import random

from domain.video import Video
from domain.network import Network
from domain.endpoint import Endpoint
from domain.cache_server import CacheServer


class Generator:

    def __init__(self, numberOfVideo: int, numberOfEndpoint: int, numberOfRequest: int, numberOfCaches: int, cacheSaturation: int, videoDistribution: int, density: int, latencyDistribution: int):
        self.numberOfVideo = numberOfVideo
        self.numberOfEndpoint = numberOfEndpoint
        self.numberOfRequest = numberOfRequest
        self.numberOfCache = numberOfCaches
        self.cacheSaturation = cacheSaturation
        self.videoDistribution = videoDistribution
        self.density = density
        self.latencyDistribution = latencyDistribution

    def createNetwork(self) -> Network:
        if self.numberOfRequest > self.numberOfEndpoint * 10000:
            raise ValueError("Le nombre de descriptions de requêtes dépasse la limite par endpoint")

        videos = Network.createVideos(self.numberOfVideo)
        endpoints = Network.createEndpoints(self.numberOfEndpoint)
        self.cacheServerSize = min(
            CacheServer.MAXSIZE,
            max(1, round(CacheServer.MAXSIZE * self.cacheSaturation / 100)),
        )
        cacheServers = Network.createCaches(self.numberOfCache, self.cacheServerSize)
        network = Network(videos, cacheServers, endpoints, self.numberOfRequest)
        cacheNb = round(self.numberOfCache * self.density / 100)

        for endpoint in endpoints:
            for cacheServer in random.sample(cacheServers, cacheNb):
                maxLatency = min(
                    Endpoint.MAXLATENCYTOCACHE,
                    endpoint.dataCenterLatency - 1,
                )
                minLatency = 1
                targetLatency = minLatency + round(
                    (maxLatency - minLatency) * self.latencyDistribution / 100
                )
                latency = random.randint(minLatency, max(minLatency, targetLatency))
                network.connectEndpointToCache(endpoint, cacheServer, latency)

        if(self.numberOfRequest < 1 and self.numberOfRequest > 1000000):
            return
        for requestId in range(self.numberOfRequest):
            endpoint = endpoints[requestId % self.numberOfEndpoint]
            if self.videoDistribution == 0:
                videoId = random.randrange(self.numberOfVideo)
            else:
                videoId = min(self.numberOfVideo - 1, int(random.random() ** 2 * self.numberOfVideo))
            endpoint.requests.append((videoId, 1))

        return network

    def exportNetworkIntoIn(self):
        network = self.createNetwork()
        lines = [f"{self.numberOfVideo} {self.numberOfEndpoint} {self.numberOfRequest} {self.numberOfCache} {self.cacheServerSize}"]
        lines.append(" ".join(str(video.sizeMB) for video in network.videos))

        for endpoint in network.endpoints:
            lines.append(f"{endpoint.dataCenterLatency} {len(endpoint.connectedCaches)}")
            for cacheServer, latency in endpoint.connectedCaches.items():
                cacheServerId = network.cacheServers.index(cacheServer)
                lines.append(f"{cacheServerId} {latency}")

        for endpointId, endpoint in enumerate(network.endpoints):
            for videoId, requestNb in endpoint.requests:
                lines.append(f"{videoId} {endpointId} {requestNb}")

        return "\n".join(lines) + "\n"
