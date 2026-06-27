"""Abstract AI provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict


class AIProvider(ABC):
    model_name = "abstract"
    provider_name = "abstract"
    is_real_llm = False

    @abstractmethod
    def generate_report(self, context: Dict):
        raise NotImplementedError

    @abstractmethod
    def answer_question(self, report_text: str, context: Dict, question: str):
        raise NotImplementedError

    def health(self) -> Dict:
        return {
            "provider": self.provider_name,
            "model_name": self.model_name,
            "is_real_llm": self.is_real_llm,
            "ready": True,
        }


@dataclass
class AIProviderResult:
    text: str
    model_name: str
    provider_used: str
    is_real_llm: bool

    @property
    def storage_model_name(self):
        if self.provider_used == "remote_medgemma":
            return "{}:{}".format(self.provider_used, self.model_name)
        return self.model_name


class AIProviderError(Exception):
    """Raised when an AI provider cannot produce a valid response."""


class AIProviderConfigurationError(AIProviderError):
    """Raised when provider startup/configuration is invalid."""
