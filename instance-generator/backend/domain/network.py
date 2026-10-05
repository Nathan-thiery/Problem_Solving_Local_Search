from .video import Video
from .cache_server import CacheServer
from .endpoint import Endpoint
import random


class Network:
    def __init__(self, videos, cacheServers, endpoints, requestNb):
        self.videos = videos
        self.cacheServers = cacheServers
        self.endpoints = endpoints
        self.requestNb = requestNb

    def createVideos(numberOfVideo: int) -> list[Video]:
        if (numberOfVideo < 1 and numberOfVideo > 10000):
            return []
        videos = []
        for i in range(numberOfVideo):
            videos.append(Video.createVideo(random.randint(Video.MINSIZE, Video.MAXSIZE)))
        return videos

    def createCaches(numberOfCaches: int, capacity: int) -> list[CacheServer]:
            if(numberOfCaches < 1 and numberOfCaches > 1000):
                return []
            caches = []
            for i in range(numberOfCaches):
                caches.append(CacheServer.createCacheServer(capacity))
            return caches

    def createEndpoints(numberOfEndpoints: int) -> list[Endpoint]:
            if(numberOfEndpoints < 1 and numberOfEndpoints > 1000):
                return []
            endpoints = []
            for i in range(numberOfEndpoints):
                endpoints.append(Endpoint.createEndpoint(random.randint(2, 4000)))
            return endpoints

    def connectEndpointToCache(self, endpoint, cacheServer, latency):
        endpoint.connectedCaches[cacheServer] = latency
        if endpoint not in cacheServer.connectedEndpoints:
            cacheServer.connectedEndpoints.append(endpoint)
