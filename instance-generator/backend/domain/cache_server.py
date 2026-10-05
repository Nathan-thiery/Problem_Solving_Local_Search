class CacheServer:
    MAXSIZE = 500000
    MINSIZE = 1

    def __init__(self, capacityMB: int):
        self.capacityMB = capacityMB
        self.connectedEndpoints = []

    @classmethod
    def createCacheServer(cls, capacityMB: int) -> CacheServer:
        if(not(cls.MINSIZE<=capacityMB<=cls.MAXSIZE)):
            return;
        createdCacheServer = CacheServer(capacityMB)
        return createdCacheServer;
