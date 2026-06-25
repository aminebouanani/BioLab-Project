"""Abstract AI provider interface."""

from abc import ABC, abstractmethod
from typing import Dict


class AIProvider(ABC):
    model_name = "abstract"

    @abstractmethod
    def generate_report(self, context: Dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def answer_question(self, report_text: str, context: Dict, question: str) -> str:
        raise NotImplementedError
