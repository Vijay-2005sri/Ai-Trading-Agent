"""
=============================================================================
LLM PROVIDER — Multi-Provider Smart Router with RAG Grounding
=============================================================================
Connects to multiple LLM APIs and auto-switches between them on failure.
Uses the pure `openai` Python package (no LangChain dependency).

Provider Priority (free → paid fallback):
  1. Groq          (FREE: ~1000 req/day, blazing fast, Llama 3.3-70B)
  2. Google Gemini  (FREE: ~1500 req/day, Gemini 2.5 Flash)
  3. OpenRouter     (FREE: Nemotron 550B Ultra — frontier-level reasoning)
  4. OpenRouter     (FREE: Qwen3 Coder — excellent JSON structured output)
  5. DeepSeek       (PAID: 1M context, fast & cheap)

RAG Grounding Contract:
  Every LLM invocation now injects a "GROUNDING CONTRACT" system prompt
  that forces the model to:
    - ONLY cite win rates that appear verbatim in the RAG context block
    - List all RAG memory IDs it used in rag_sources_cited
    - Self-assess hallucination risk honestly
    - Never invent market data not present in the provided context
=============================================================================
"""

import os
import time
import json
from typing import Optional
from pydantic import BaseModel, Field
from openai import OpenAI


# =============================================================================
# GROUNDED TradeDecision Schema
# =============================================================================

class TradeDecision(BaseModel):
    """
    Structured trading decision with mandatory RAG grounding fields.

    The LLM MUST fill rag_sources_cited from the RAG context block provided
    to it. The GroundingValidator will cross-check these IDs against ChromaDB.
    Fabricated IDs or empty lists will trigger an automatic HOLD override.
    """
    action: str = Field(
        description="BUY, SELL, or HOLD. Must be consistent with the RAG historical evidence."
    )
    pair: str = Field(
        description="The trading pair, e.g., EURUSD"
    )
    confidence: int = Field(
        description="Confidence score 0-100. Must be LOWER if RAG win rate is below 55% or cold-start."
    )
    reasoning: str = Field(
        description=(
            "Detailed explanation that MUST reference: "
            "(1) specific RAG memory IDs from the context block, "
            "(2) the historical win rate stated in RAG context, "
            "(3) specific news events from the RAG news block, "
            "(4) which strategy generated the signal and why. "
            "Do NOT invent data not present in the provided context."
        )
    )
    suggested_sl: float = Field(
        description="Suggested Stop Loss price. Must be non-zero for BUY/SELL."
    )
    suggested_tp: float = Field(
        description="Suggested Take Profit price. Must be non-zero for BUY/SELL."
    )
    strategy_used: str = Field(
        description="Exact strategy name from the LOADED STRATEGIES block (e.g., 'SMC_Liquidity_Sweep')"
    )
    rag_sources_cited: list[str] = Field(
        default_factory=list,
        description=(
            "MANDATORY: List every RAG memory ID you referenced from the RAG context block. "
            "Format: ['MEM-1', 'NEWS-2', ...]. "
            "Empty list = GroundingValidator will override this decision to HOLD."
        )
    )
    historical_win_rate: float = Field(
        default=0.0,
        description=(
            "Copy the win rate EXACTLY as stated in the RAG VERIFIED TRADE MEMORY block. "
            "Do NOT invent or estimate. If no RAG history, use 0.0."
        )
    )
    hallucination_risk: str = Field(
        default="UNKNOWN",
        description=(
            "Self-assess your certainty. "
            "'LOW' = strong RAG evidence + clear signals align. "
            "'MEDIUM' = some evidence but signals are mixed. "
            "'HIGH' = little/no RAG evidence, acting on patterns alone. "
            "Be HONEST — HIGH risk will safely override to HOLD."
        )
    )


# =============================================================================
# GROUNDING CONTRACT — Injected into EVERY LLM system prompt
# =============================================================================

GROUNDING_CONTRACT = """
=== GROUNDING CONTRACT (MANDATORY — NON-NEGOTIABLE) ===
You are connected to a verified ChromaDB vector database (RAG system).
The context blocks below contain REAL historical data retrieved from this database.

YOUR OBLIGATIONS:
1. CITE SOURCES: Every claim about past performance MUST cite a RAG memory ID 
   (e.g., MEM-1, NEWS-2) from the context provided below.
2. DO NOT INVENT: If the RAG block says "No verified history available", 
   you MUST set hallucination_risk="HIGH" and action="HOLD".
3. WIN RATE HONESTY: Copy the win rate EXACTLY from the RAG context. 
   Do NOT estimate or improve it.
4. SELF-ASSESS: Be brutally honest about hallucination_risk. 
   The system has a deterministic validator that WILL catch mismatches.
5. EMPTY DB = HOLD: If RAG is cold-start (no history), the safest action is HOLD.

Violation of this contract → your decision is automatically overridden to HOLD.
This protects the trading account from hallucination-driven losses.
=== END OF GROUNDING CONTRACT ===
"""


# =============================================================================
# LLM PROVIDER — Pure OpenAI SDK (No LangChain)
# =============================================================================

class LLMProvider:
    """
    Smart LLM Router with auto-failover across free providers.
    Injects GROUNDING_CONTRACT into every prompt.
    Uses the pure `openai` Python package — zero LangChain dependency.

    Usage:
        provider = LLMProvider()
        decision = provider.invoke_structured(prompt, rag_context, TradeDecision)
    """

    # Provider configs — ordered by priority (free first, paid last)
    PROVIDERS = [
        {
            "name":     "Groq",
            "base_url": "https://api.groq.com/openai/v1",
            "env_key":  "GROQ_API_KEY",
            "model":    "llama-3.3-70b-versatile",
            "is_free":  True,
        },
        {
            "name":     "Google Gemini",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "env_key":  "GOOGLE_API_KEY",
            "model":    "gemini-2.5-flash",
            "is_free":  True,
        },
        {
            "name":     "OpenRouter (Nemotron Ultra 550B)",
            "base_url": "https://openrouter.ai/api/v1",
            "env_key":  "OPENROUTER_API_KEY",
            "model":    "nvidia/nemotron-3-ultra-550b-a55b:free",
            "is_free":  True,
        },
        {
            "name":     "OpenRouter (Qwen3 Coder)",
            "base_url": "https://openrouter.ai/api/v1",
            "env_key":  "OPENROUTER_API_KEY",
            "model":    "qwen/qwen3-coder:free",
            "is_free":  True,
        },
        {
            "name":     "SambaNova (Llama 3.1 70B)",
            "base_url": "https://api.sambanova.ai/v1",
            "env_key":  "SAMBANOVA_API_KEY",
            "model":    "Meta-Llama-3.1-70B-Instruct",
            "is_free":  True,
        },
        {
            "name":     "HuggingFace (Qwen Coder 32B)",
            "base_url": "https://api-inference.huggingface.co/v1/",
            "env_key":  "HF_TOKEN",
            "model":    "Qwen/Qwen2.5-Coder-32B-Instruct",
            "is_free":  True,
        },
        {
            "name":     "HuggingFace (Llama 3.1 8B)",
            "base_url": "https://api-inference.huggingface.co/v1/",
            "env_key":  "HF_TOKEN",
            "model":    "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "is_free":  True,
        },
        {
            "name":     "DeepSeek",
            "base_url": "https://api.deepseek.com",
            "env_key":  "DEEPSEEK_API_KEY",
            "model":    "deepseek-chat",
            "is_free":  False,
        },
    ]

    def __init__(self):
        self.available_providers = []
        self._init_providers()
        self.current_provider_idx = 0

    def _init_providers(self):
        """Initialize only providers that have API keys set."""
        for cfg in self.PROVIDERS:
            api_key = os.getenv(cfg["env_key"])
            if api_key and api_key not in ("", "sk-...", "AIza...", "gsk_...", "tvly-..."):
                try:
                    client = OpenAI(
                        api_key=api_key,
                        base_url=cfg["base_url"],
                        timeout=30.0,
                        max_retries=1,
                    )
                    self.available_providers.append({
                        "name":     cfg["name"],
                        "client":   client,
                        "model":    cfg["model"],
                        "is_free":  cfg["is_free"],
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
                "Set at least one API key in .env "
                "(GROQ_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY, or DEEPSEEK_API_KEY)"
            )

        print(
            f"\n  📡 {len(self.available_providers)} LLM provider(s) active. "
            f"Primary: {self.available_providers[0]['name']}"
        )

    def _get_current_provider(self) -> Optional[dict]:
        """Get current provider, skip those with 3+ consecutive failures."""
        for _ in range(len(self.available_providers)):
            provider = self.available_providers[self.current_provider_idx]
            if provider["failures"] < 3:
                return provider
            self.current_provider_idx = (
                (self.current_provider_idx + 1) % len(self.available_providers)
            )
        return None

    def _failover(self, failed_name: str, error: str):
        """Mark provider as failed and rotate to next."""
        print(f"  ⚠️  {failed_name} failed: {error}. Switching to next provider...")
        for p in self.available_providers:
            if p["name"] == failed_name:
                p["failures"] += 1
        self.current_provider_idx = (
            (self.current_provider_idx + 1) % len(self.available_providers)
        )

    def invoke(self, prompt: str) -> str:
        """
        Send a text prompt to the LLM. Returns plain string response.
        Auto-failovers across providers.
        """
        attempts    = 0
        max_attempts = len(self.available_providers)

        while attempts < max_attempts:
            provider = self._get_current_provider()
            if provider is None:
                raise RuntimeError("All LLM providers are down.")
            try:
                response = provider["client"].chat.completions.create(
                    model=provider["model"],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                )
                provider["failures"] = 0
                return response.choices[0].message.content
            except Exception as e:
                self._failover(provider["name"], str(e))
                attempts += 1
                time.sleep(1)

        raise RuntimeError("All LLM providers exhausted after failover attempts.")

    def invoke_structured(
        self,
        base_prompt: str,
        rag_context: str,
        output_schema: type[BaseModel] = TradeDecision
    ) -> BaseModel:
        """
        Send a grounded prompt and get a structured (Pydantic) response.

        Args:
            base_prompt:   The analytical prompt (quant report, fundamental report, etc.)
            rag_context:   Pre-built RAG context block from TradingRAG (verified memory)
            output_schema: Pydantic schema — defaults to grounded TradeDecision

        The GROUNDING_CONTRACT is automatically prepended to every call.
        The LLM receives: CONTRACT + RAG_CONTEXT + BASE_PROMPT
        """
        # Build the fully grounded prompt
        user_prompt = (
            f"=== CURRENT MARKET ANALYSIS ===\n"
            f"{base_prompt}\n\n"
            f"Now produce your grounded decision. Remember: cite RAG IDs, "
            f"copy win rates exactly, and assess hallucination_risk honestly.\n\n"
            f"Respond ONLY with valid JSON matching this schema:\n"
            f"{json.dumps(output_schema.model_json_schema(), indent=2)}"
        )

        system_prompt = (
            f"{GROUNDING_CONTRACT}\n\n"
            f"=== VERIFIED RAG CONTEXT (Source of Truth) ===\n"
            f"{rag_context}"
        )

        attempts     = 0
        max_attempts = len(self.available_providers)

        while attempts < max_attempts:
            provider = self._get_current_provider()
            if provider is None:
                raise RuntimeError("All LLM providers are down.")

            try:
                response = provider["client"].chat.completions.create(
                    model=provider["model"],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                raw_content = response.choices[0].message.content
                
                # Parse JSON from response
                data = json.loads(raw_content)
                provider["failures"] = 0
                return output_schema(**data)

            except Exception as e:
                # Try without response_format (some providers don't support it)
                try:
                    response = provider["client"].chat.completions.create(
                        model=provider["model"],
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.1,
                    )
                    raw_content = response.choices[0].message.content
                    
                    # Extract JSON from potential markdown code blocks
                    cleaned = raw_content.strip()
                    if cleaned.startswith("```"):
                        # Remove markdown code fences
                        lines = cleaned.split("\n")
                        lines = [l for l in lines if not l.strip().startswith("```")]
                        cleaned = "\n".join(lines)
                    
                    data = json.loads(cleaned)
                    provider["failures"] = 0
                    return output_schema(**data)
                except Exception:
                    self._failover(provider["name"], str(e))
                    attempts += 1
                    time.sleep(1)

        # Hard fallback — safe HOLD with honest reasoning
        print("  🛡️  All LLM providers exhausted. Returning safe HOLD.")
        return TradeDecision(
            action="HOLD",
            pair="UNKNOWN",
            confidence=0,
            reasoning="All LLM providers exhausted. Defaulting to HOLD for capital safety.",
            suggested_sl=0.0,
            suggested_tp=0.0,
            strategy_used="ERROR_FALLBACK",
            rag_sources_cited=[],
            historical_win_rate=0.0,
            hallucination_risk="HIGH"
        )

    def get_active_provider_name(self) -> str:
        provider = self._get_current_provider()
        return provider["name"] if provider else "NONE"

    def get_status(self) -> list[dict]:
        return [
            {
                "name":     p["name"],
                "model":    p["model"],
                "free":     p["is_free"],
                "failures": p["failures"]
            }
            for p in self.available_providers
        ]

    # =================================================================
    # DEBATE ARENA METHODS — Per-Provider Targeting
    # =================================================================
    # These methods let the DebateArena send prompts to SPECIFIC models
    # instead of using the auto-failover router.

    def get_all_available_names(self) -> list[str]:
        """Return names of all available (configured) providers."""
        return [p["name"] for p in self.available_providers]

    def get_provider_by_name(self, name: str) -> Optional[dict]:
        """Get a specific provider by its name. Returns None if not found."""
        for p in self.available_providers:
            if p["name"] == name:
                return p
        return None

    def invoke_on_provider(
        self,
        provider_name: str,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.1
    ) -> Optional[str]:
        """
        Send a text prompt to a SPECIFIC provider (not the auto-router).
        Used by the Debate Arena to get each model's independent opinion.

        Returns the response string, or None if the provider fails.
        Does NOT trigger failover — the caller (DebateArena) handles that.
        """
        provider = self.get_provider_by_name(provider_name)
        if provider is None:
            print(f"  ⚠️  Provider '{provider_name}' not found.")
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = provider["client"].chat.completions.create(
                model=provider["model"],
                messages=messages,
                temperature=temperature,
            )
            provider["failures"] = 0
            return response.choices[0].message.content
        except Exception as e:
            provider["failures"] += 1
            print(f"  ⚠️  {provider_name} failed: {str(e)[:120]}")
            return None

    def invoke_structured_on_provider(
        self,
        provider_name: str,
        base_prompt: str,
        rag_context: str,
        output_schema: type[BaseModel] = TradeDecision
    ) -> Optional[BaseModel]:
        """
        Send a grounded, structured prompt to a SPECIFIC provider.
        Used by the Debate Arena for Round 1 (each model's independent analysis).

        Returns a Pydantic model instance, or None if the provider fails.
        Does NOT trigger failover — the caller (DebateArena) handles that.
        """
        provider = self.get_provider_by_name(provider_name)
        if provider is None:
            print(f"  ⚠️  Provider '{provider_name}' not found.")
            return None

        user_prompt = (
            f"=== CURRENT MARKET ANALYSIS ===\n"
            f"{base_prompt}\n\n"
            f"Now produce your grounded decision. Remember: cite RAG IDs, "
            f"copy win rates exactly, and assess hallucination_risk honestly.\n\n"
            f"Respond ONLY with valid JSON matching this schema:\n"
            f"{json.dumps(output_schema.model_json_schema(), indent=2)}"
        )

        system_prompt = (
            f"{GROUNDING_CONTRACT}\n\n"
            f"=== VERIFIED RAG CONTEXT (Source of Truth) ===\n"
            f"{rag_context}"
        )

        # Attempt 1: with response_format
        try:
            response = provider["client"].chat.completions.create(
                model=provider["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content
            data = json.loads(raw_content)
            provider["failures"] = 0
            return output_schema(**data)
        except Exception:
            pass

        # Attempt 2: without response_format (some providers don't support it)
        try:
            response = provider["client"].chat.completions.create(
                model=provider["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
            )
            raw_content = response.choices[0].message.content

            # Extract JSON from potential markdown code blocks
            cleaned = raw_content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines)

            data = json.loads(cleaned)
            provider["failures"] = 0
            return output_schema(**data)
        except Exception as e:
            provider["failures"] += 1
            print(f"  ⚠️  {provider_name} structured call failed: {str(e)[:120]}")
            return None
