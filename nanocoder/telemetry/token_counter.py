"""Token counter and cost tracking module for NanoCoder."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import re


@dataclass
class TokenUsage:
    """Tracks token usage across an entire agent execution session."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    
    # Baseline comparison (what a standard naive ReAct agent would consume)
    naive_prompt_tokens: int = 0
    naive_completion_tokens: int = 0
    
    # Breakdown of tokens saved by compression mechanism
    tokens_saved_by_skeleton: int = 0
    tokens_saved_by_distillation: int = 0
    tokens_saved_by_history_compaction: int = 0
    tokens_saved_by_surgical_patch: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def naive_total_tokens(self) -> int:
        return self.naive_prompt_tokens + self.naive_completion_tokens

    @property
    def total_tokens_saved(self) -> int:
        saved = self.naive_total_tokens - self.total_tokens
        return max(0, saved)

    @property
    def percentage_saved(self) -> float:
        if self.naive_total_tokens == 0:
            return 0.0
        return round((self.total_tokens_saved / self.naive_total_tokens) * 100, 2)

    @property
    def estimated_cost_usd(self) -> float:
        # Standard rate: $0.10 / 1M input tokens, $0.40 / 1M output tokens (Gemini 3.8 Flash / Flash-Lite scale)
        return (self.prompt_tokens / 1_000_000 * 0.10) + (self.completion_tokens / 1_000_000 * 0.40)

    @property
    def naive_estimated_cost_usd(self) -> float:
        return (self.naive_prompt_tokens / 1_000_000 * 0.10) + (self.naive_completion_tokens / 1_000_000 * 0.40)

    @property
    def cost_saved_usd(self) -> float:
        return max(0.0, self.naive_estimated_cost_usd - self.estimated_cost_usd)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "naive_total_tokens": self.naive_total_tokens,
            "total_tokens_saved": self.total_tokens_saved,
            "percentage_saved": f"{self.percentage_saved}%",
            "cost_nanocoder_usd": f"${self.estimated_cost_usd:.6f}",
            "cost_naive_usd": f"${self.naive_estimated_cost_usd:.6f}",
            "savings_breakdown": {
                "skeleton_pruning": self.tokens_saved_by_skeleton,
                "output_distillation": self.tokens_saved_by_distillation,
                "history_compaction": self.tokens_saved_by_history_compaction,
                "surgical_diff_patch": self.tokens_saved_by_surgical_patch,
            }
        }


def estimate_tokens(text: str) -> int:
    """Fast, accurate token estimation (~3.7 characters per token for code & prose)."""
    if not text:
        return 0
    # Code with indentation and symbols averages ~3.5-3.8 chars per token
    return max(1, int(len(text) / 3.7))
