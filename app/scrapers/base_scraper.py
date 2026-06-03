from abc import ABC, abstractmethod

class BaseScraper(ABC):
    @staticmethod
    @abstractmethod
    def coletar():
        pass