import logging
from abc import ABC


class ITranscriberService(ABC):
    def __init__(self):
        """Initializes the TranscriberService."""
        self.logger = logging.getLogger(self.__class__.__name__)


class WhiserXTranscriberService(ITranscriberService):
    def __init__(self):
        super().__init__()
