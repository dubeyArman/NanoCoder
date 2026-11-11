"""Base LLM Provider interface for NanoCoder."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from nanocoder.telemetry.token_counter import TokenUsage


class BaseProvider(ABC):
    """Abstract interface for LLM inference backends."""

    def __init__(self, token_usage: TokenUsage):
        self.token_usage = token_usage

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Sends prompt to LLM and returns the completion string."""
        pass
