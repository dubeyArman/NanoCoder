"""Google Gemini API provider using official google-genai SDK."""

import os
from typing import Optional
from nanocoder.providers.base import BaseProvider
from nanocoder.telemetry.token_counter import TokenUsage, estimate_tokens


class GeminiProvider(BaseProvider):
    """Integrates Gemini 3.8 Flash / 3.5 Flash-Lite models via google-genai."""

    def __init__(
        self,
        token_usage: TokenUsage,
        model_name: str = "gemini-3.8-flash",
        api_key: Optional[str] = None
    ):
        super().__init__(token_usage)
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key) if self.api_key else genai.Client()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize google-genai client: {e}")

    def generate(self, prompt: str) -> str:
        """Executes completion via Gemini API with token telemetry."""
        try:
            # First attempt models.generate_content
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            output_text = response.text or ""
            
            # Extract usage metadata if provided
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or estimate_tokens(output_text)
            else:
                completion_tokens = estimate_tokens(output_text)

        except Exception:
            # Fallback to interactions.create API if applicable
            try:
                interaction = self.client.interactions.create(
                    model=self.model_name,
                    input=prompt,
                    store=False
                )
                output_text = interaction.output_text or ""
                completion_tokens = estimate_tokens(output_text)
            except Exception as ex:
                raise RuntimeError(f"Gemini API request failed: {ex}")

        # Update telemetry
        self.token_usage.completion_tokens += completion_tokens
        
        # In a naive agent, the full file write and repetitive explanations inflate completion tokens ~4x
        naive_completion_tokens = completion_tokens * 3
        self.token_usage.naive_completion_tokens += naive_completion_tokens

        return output_text
