"""OpenAI API Provider for NanoCoder."""

import os
from typing import Optional
from nanocoder.providers.base import BaseProvider
from nanocoder.telemetry.token_counter import TokenUsage, estimate_tokens


class OpenAIProvider(BaseProvider):
    """Integrates OpenAI or compatible API endpoints."""

    def __init__(
        self,
        token_usage: TokenUsage,
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        super().__init__(token_usage)
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}")

    def generate(self, prompt: str) -> str:
        """Executes completion via OpenAI API."""
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
            raise RuntimeError(f"OpenAI API request failed: {e}")
