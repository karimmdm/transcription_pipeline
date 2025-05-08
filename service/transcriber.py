from abc import ABC, abstractmethod
import logging


class ITranscriberService(ABC):
    def __init__(self):
        """
        Initializes the TranscriberService.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
