"""
=============================================================================
LLM PROVIDER — Multi-Provider Smart Router
=============================================================================
Connects to multiple LLM APIs (free & paid) and auto-switches between them.

Provider Priority (free → paid fallback):
  1. Groq          (FREE: ~1000 req/day, blazing fast, Llama 3.3)
  2. Google Gemini  (FREE: ~1500 req/day, Gemini 2.5 Flash)
  3. OpenRouter     (FREE: ~50-1000 req/day, many models)
  4. OpenAI         (PAID: fallback, GPT-4o)

If Provider #1 hits rate limit → automatically falls to #2 → #3 → #4.
This lets us check EVERY candle without worrying about token costs.
=============================================================================
"""

import os
import time
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Optional


class TradeDecision(BaseModel):
    action: str = Field(description="BUY, SELL, or HOLD")
    pair: str = Field(description="The trading pair, e.g., EURUSD")
    confidence: int = Field(description="Confidence score 0-100")
    reasoning: str = Field(description="Detailed explanation referencing strategies, news, and data")
    suggested_sl: float = Field(description="Suggested Stop Loss price")
    suggested_tp: float = Field(description="Suggested Take Profit price")
    strategy_used: str = Field(description="Which strategy or combination the decision is based on")


class LLMProvider:
    """
    Smart LLM Router with auto-failover across free providers.

    Usage:
        provider = LLMProvider()
        response = provider.invoke("Analyze this market data...")
        decision = provider.invoke_structured("...", TradeDecision)
    """

    # Provider configs: (name, base_url, env_key, model, is_free)
    PROVIDERS = [
        {
            "name": "Groq",
            "base_url": "https://api.groq.com/openai/v1",
            "env_key": "GROQ_API_KEY",
            "model": "llama-3.3-70b-versatile",
            "is_free": True,
        },
        {
            "name": "Google Gemini",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "env_key": "GOOGLE_API_KEY",
            "model": "gemini-2.5-flash",
            "is_free": True,
        },
        {
            "name": "OpenRouter (Nemotron Ultra 550B)",
            "base_url": "https://openrouter.ai/api/v1",
            "env_key": "OPENROUTER_API_KEY",
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",  # 1M context, frontier-level reasoning, FREE
            "is_free": True,
        },
        {
            "name": "OpenRouter (Qwen3 Coder)",
            "base_url": "https://openrouter.ai/api/v1",
            "env_key": "OPENROUTER_API_KEY",
            "model": "qwen/qwen3-coder:free",  # 1M context, great for structured JSON output, FREE
            "is_free": True,
        },
        {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "env_key": "OPENAI_API_KEY",
            "model": "gpt-4o",
            "is_free": False,
        },
    ]

    def __init__(self):
        self.available_providers = []
        self._init_providers()
        self.current_provider_idx = 0
        self.request_count = {}  # Track requests per provider per day

    def _init_providers(self):
        """Initialize only providers that have API keys set."""
        from langchain_openai import ChatOpenAI

        for cfg in self.PROVIDERS:
            api_key = os.getenv(cfg["env_key"])
            if api_key and api_key not in ("", "sk-...", "AIza...", "gsk_...", "tvly-..."):
                try:
                    llm = ChatOpenAI(
                        api_key=api_key,
                        base_url=cfg["base_url"],
                        model=cfg["model"],
                        temperature=0.1,
                        max_retries=1,
                        request_timeout=30,
                    )
                    self.available_providers.append({
                        "name": cfg["name"],
                        "llm": llm,
                        "is_free": cfg["is_free"],
                        "model": cfg["model"],
                        "failures": 0,
                    })
                    print(f"  ✅ {cfg['name']} ({cfg['model']}) — ready")
                except Exception as e:
                    print(f"  ❌ {cfg['name']} — failed to init: {e}")
            else:
                print(f"  ⏭️  {cfg['name']} — skipped (no API key)")

        if not self.available_providers:
            raise RuntimeError(
                "🛑 No LLM providers configured! "
                "Set at least one API key in .env (GROQ_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY, or OPENAI_API_KEY)"
            )

        print(f"\n  📡 {len(self.available_providers)} LLM provider(s) active. "
              f"Primary: {self.available_providers[0]['name']}")

    def _get_next_provider(self) -> Optional[dict]:
        """Get the next available provider, cycling through the list."""
        for _ in range(len(self.available_providers)):
            provider = self.available_providers[self.current_provider_idx]
            if provider["failures"] < 3:  # Skip providers with 3+ consecutive failures
                return provider
            self.current_provider_idx = (self.current_provider_idx + 1) % len(self.available_providers)
        return None

    def _failover(self, failed_name: str, error: str):
        """Switch to next provider after a failure."""
        print(f"  ⚠️  {failed_name} failed: {error}. Switching to next provider...")
        for p in self.available_providers:
            if p["name"] == failed_name:
                p["failures"] += 1
        self.current_provider_idx = (self.current_provider_idx + 1) % len(self.available_providers)

    def invoke(self, prompt: str) -> str:
        """
        Send a text prompt to the LLM and get a string response.
        Auto-failovers across providers if one fails.
        """
        attempts = 0
        max_attempts = len(self.available_providers)

        while attempts < max_attempts:
            provider = self._get_next_provider()
            if provider is None:
                raise RuntimeError("All LLM providers are down.")

            try:
                response = provider["llm"].invoke(prompt)
                provider["failures"] = 0  # Reset on success
                return response.content
            except Exception as e:
                self._failover(provider["name"], str(e))
                attempts += 1
                time.sleep(1)  # Brief pause before retry

        raise RuntimeError("All LLM providers exhausted after failover attempts.")

    def invoke_structured(self, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        """
        Send a prompt and get a structured (Pydantic) response.
        Auto-failovers across providers.
        """
        attempts = 0
        max_attempts = len(self.available_providers)

        while attempts < max_attempts:
            provider = self._get_next_provider()
            if provider is None:
                raise RuntimeError("All LLM providers are down.")

            try:
                structured_llm = provider["llm"].with_structured_output(output_schema)
                response = structured_llm.invoke(prompt)
                provider["failures"] = 0
                return response
            except Exception as e:
                # Structured output may not work on all models, try raw JSON parse
                try:
                    raw = provider["llm"].invoke(
                        prompt + "\n\nRespond ONLY with valid JSON matching this schema: "
                        + output_schema.model_json_schema().__str__()
                    )
                    import json
                    data = json.loads(raw.content)
                    provider["failures"] = 0
                    return output_schema(**data)
                except Exception:
                    self._failover(provider["name"], str(e))
                    attempts += 1
                    time.sleep(1)

        raise RuntimeError("All LLM providers exhausted.")

    def get_active_provider_name(self) -> str:
        provider = self._get_next_provider()
        return provider["name"] if provider else "NONE"

    def get_status(self) -> list[dict]:
        return [
            {"name": p["name"], "model": p["model"], "free": p["is_free"], "failures": p["failures"]}
            for p in self.available_providers
        ]
