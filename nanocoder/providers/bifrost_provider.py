"""Bifrost by Maxim AI Gateway Provider for NanoCoder.

Routes inference requests through Bifrost (Maxim AI's high-performance AI Gateway)
for enterprise virtual key governance, automatic provider fallback, low latency,
and unified token observability.
"""

import os
from typing import Optional
from nanocoder.providers.base import BaseProvider
from nanocoder.telemetry.token_counter import TokenUsage, estimate_tokens


class BifrostProvider(BaseProvider):
    """Integrates with Bifrost by Maxim AI (AI/LLM Gateway)."""

    def __init__(
        self,
        token_usage: TokenUsage,
        model_name: str = "gemini-3.8-flash",
        bifrost_gateway_url: Optional[str] = None,
        virtual_key: Optional[str] = None
    ):
        super().__init__(token_usage)
        self.model_name = model_name
        self.bifrost_gateway_url = bifrost_gateway_url or os.environ.get("BIFROST_GATEWAY_URL", "http://localhost:8080/v1")
        self.virtual_key = virtual_key or os.environ.get("BIFROST_VIRTUAL_KEY", os.environ.get("OPENAI_API_KEY", "bifrost-key"))

        try:
            from openai import OpenAI
            # Bifrost exposes an ultra-fast OpenAI-compatible gateway
            self.client = OpenAI(
                base_url=self.bifrost_gateway_url,
                api_key=self.virtual_key
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Bifrost Gateway client: {e}")

    def generate(self, prompt: str) -> str:
        """Sends inference through the Bifrost Gateway."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            choice = response.choices[0]
            output_text = choice.message.content or ""
            
            completion_tokens = response.usage.completion_tokens if response.usage else estimate_tokens(output_text)
            self.token_usage.completion_tokens += completion_tokens
            self.token_usage.naive_completion_tokens += completion_tokens * 3
            
            return output_text
        except Exception as e:
            # If Bifrost daemon is not locally running, provide helpful notice
            raise RuntimeError(f"Bifrost Gateway connection error at {self.bifrost_gateway_url}: {e}")
