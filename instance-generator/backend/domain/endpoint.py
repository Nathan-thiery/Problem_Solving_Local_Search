class Endpoint:
    MAXLATENCYTOCACHE = 500
    MINLATENCYTOCACHE = 1
    MAXLATENCYTODATACENTER = 4000
    MINLATENCYTODATACENTER = 2

    def __init__(self, dataCenterLatency: int):
        self.dataCenterLatency = dataCenterLatency
        self.connectedCaches = {}
        self.requests = []

    @classmethod
    def createEndpoint(cls, dataCenterLatency) -> Endpoint:
        if(not(cls.MINLATENCYTODATACENTER<=dataCenterLatency<=cls.MAXLATENCYTODATACENTER)):
            return
        return Endpoint(dataCenterLatency)
