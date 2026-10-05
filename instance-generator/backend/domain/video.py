class Video:
    MAXSIZE = 1000
    MINSIZE = 1

    def __init__(self, sizeMB):
        self.sizeMB = sizeMB

    @classmethod
    def createVideo(cls, sizeMB) -> Video | None:
        if(not(cls.MINSIZE<=sizeMB<=cls.MAXSIZE)):
            return
        return Video(sizeMB)