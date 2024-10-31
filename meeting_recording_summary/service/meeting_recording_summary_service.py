from abc import abstractmethod, ABC


class MeetingRecordingSummaryService(ABC):
    @abstractmethod
    def getSummary(self, *args, **kwargs):
        pass