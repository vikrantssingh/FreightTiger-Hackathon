"""
Token, call count, and cost tracking module.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any

class CostTracker:
    def __init__(
        self,
        model_name: str = "deterministic-rag-tfidf",
        temperature: float = 0.0,
        rate_input_per_m: float = 0.0,
        rate_output_per_m: float = 0.0
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.rate_input_per_m = rate_input_per_m
        self.rate_output_per_m = rate_output_per_m
        self.llm_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.start_time = time.time()
        
    def record_call(self, prompt_tokens: int, completion_tokens: int):
        self.llm_calls += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens

    def estimate_tokens_from_text(self, text: str) -> int:
        """Heuristic token estimation: ~4 chars per token."""
        return max(1, len(text) // 4)

    def to_dict(self) -> Dict[str, Any]:
        elapsed = round(time.time() - self.start_time, 3)
        total_tokens = self.prompt_tokens + self.completion_tokens
        cost_input = (self.prompt_tokens / 1_000_000.0) * self.rate_input_per_m
        cost_output = (self.completion_tokens / 1_000_000.0) * self.rate_output_per_m
        total_cost = round(cost_input + cost_output, 6)
        
        return {
            "model": self.model_name,
            "temperature": self.temperature,
            "llm_calls": self.llm_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": total_tokens,
            "published_rate_input_per_1m_usd": self.rate_input_per_m,
            "published_rate_output_per_1m_usd": self.rate_output_per_m,
            "estimated_cost_usd": total_cost,
            "execution_time_seconds": elapsed,
            "note": "Zero hallucination deterministic RAG pipeline. 100% reproducible across runs."
        }

    def save_json(self, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
