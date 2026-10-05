import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from generator import Generator
from instance_validator import validate_instance

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class instanceParams(BaseModel):
    videosNb: int
    cacheServersNb: int
    endpointsNb: int
    requestNb: int
    videoDistribution: int
    density: int
    cacheSaturation: int
    latencyDistribution: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/instances")
def createInstance(params: instanceParams):
    logger.info(
        "Generation request: videos=%s caches=%s endpoints=%s requests=%s density=%s cacheSaturation=%s latencyDistribution=%s",
        params.videosNb,
        params.cacheServersNb,
        params.endpointsNb,
        params.requestNb,
        params.density,
        params.cacheSaturation,
        params.latencyDistribution,
    )
    if not (1 <= params.videosNb <= 10000 and 1 <= params.endpointsNb <= 1000 and 1 <= params.cacheServersNb <= 1000 and 1 <= params.requestNb <= 1000000):
        logger.warning("Generation request rejected: invalid global parameters")
        raise HTTPException(status_code=422, detail="Paramètres invalides")
    if params.requestNb > params.endpointsNb * 10000:
        logger.warning("Generation request rejected: too many request descriptions per endpoint")
        raise HTTPException(status_code=422, detail="Trop de descriptions de requêtes pour le nombre d'endpoints")
    if not (params.videoDistribution in [0, 1] and 0 <= params.density <= 100 and 1 <= params.cacheSaturation <= 100 and 0 <= params.latencyDistribution <= 100):
        logger.warning("Generation request rejected: invalid distribution parameters")
        raise HTTPException(status_code=422, detail="Paramètres invalides")

    generator = Generator(params.videosNb, params.endpointsNb, params.requestNb, params.cacheServersNb, params.cacheSaturation, params.videoDistribution, params.density, params.latencyDistribution)
    instanceFile = generator.exportNetworkIntoIn()
    is_valid, validation_error = validate_instance(instanceFile)
    if not is_valid:
        logger.error("Generated instance is INVALID: %s", validation_error)
        raise HTTPException(status_code=500, detail=f"Instance générée invalide: {validation_error}")

    logger.info("Generated instance is VALID")
    filename = f"{params.videosNb}_{params.endpointsNb}_{params.requestNb}_{params.cacheServersNb}.in"
    return Response(instanceFile, media_type="text/plain", headers={"Content-Disposition": f"attachment; filename={filename}"})
