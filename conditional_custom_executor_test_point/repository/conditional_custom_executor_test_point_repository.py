from abc import ABC, abstractmethod


class ConditionalCustomExecutorTestPointRepository(ABC):
    @abstractmethod
    def operate(self, *args, ipcExecutorConditionalCustomExecutorChannel=None, **kwargs):
        pass
