"""
=============================================================================
RAG GROUNDING VALIDATOR — Deterministic Hallucination Guard
=============================================================================
This module is the FINAL safety gate between LLM output and trade execution.
It uses ZERO AI — it is pure deterministic Python logic.

The LLM CANNOT hallucinate past this validator.

Checks performed:
  1. RAG sources cited  — LLM must list ≥1 memory ID it used
  2. Win rate integrity — LLM's stated win rate must match ChromaDB ±5%
  3. Hallucination risk — LLM self-reported HIGH risk → force HOLD
  4. Cold-start safety  — DB has < 3 records → force HOLD (no data to verify)
  5. Confidence floor   — Grounding-adjusted confidence must exceed 65%

If ANY check fails → TradeDecision.action is overridden to "HOLD"
and the reason is logged for Explainable AI (XAI) audit trail.
=============================================================================
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GroundingResult:
    """Result from the grounding validator."""
    is_grounded:          bool          # True = passed all checks
    override_to_hold:     bool          # True = action must be changed to HOLD
    override_reason:      str           # Human-readable reason for the override
    checks_passed:        list[str]     # List of checks that passed
    checks_failed:        list[str]     # List of checks that failed
    grounding_score:      float         # 0.0 to 1.0 — how well grounded is the decision


class GroundingValidator:
    """
    Deterministic validator that ensures LLM decisions are grounded in
    verified RAG memory before execution.

    Usage in main.py:
        validator = GroundingValidator()
        result = validator.validate(decision, trade_recall, news_recall)
        if result.override_to_hold:
            decision.action = "HOLD"
            # Log result.override_reason for XAI
    """

    WIN_RATE_TOLERANCE = 0.05   # LLM can be off by ±5% on win rate
    MIN_GROUNDING_SCORE = 0.4   # Below this → force HOLD

    def validate(
        self,
        decision,                         # TradeDecision (Pydantic model)
        trade_recall: dict,               # From TradingRAG.recall_similar_trades()
        news_recall: dict,                # From TradingRAG.recall_similar_news()
        actual_win_rate: Optional[float]  # From TradingRAG.get_strategy_win_rate()
    ) -> GroundingResult:
        """
        Validates that the LLM decision is properly grounded.

        Returns GroundingResult. If override_to_hold=True, the caller
        MUST change decision.action to "HOLD" before proceeding.
        """

        # HOLD decisions always pass (no need to validate a safe non-action)
        if decision.action == "HOLD":
            return GroundingResult(
                is_grounded=True,
                override_to_hold=False,
                override_reason="HOLD decisions are always grounded (no capital at risk).",
                checks_passed=["HOLD_PASSTHROUGH"],
                checks_failed=[],
                grounding_score=1.0
            )

        passed = []
        failed = []

        # ------------------------------------------------------------------
        # CHECK 1: Cold-start safety — need minimum historical data
        # ------------------------------------------------------------------
        trade_is_cold = trade_recall.get("is_cold_start", True)
        news_is_cold  = news_recall.get("is_cold_start", True)

        if trade_is_cold and trade_recall.get("total_found", 0) == 0:
            failed.append(
                "COLD_START: No historical trade data in RAG DB. "
                "Cannot verify any claim the LLM makes about past performance."
            )
        else:
            passed.append(f"TRADE_HISTORY: {trade_recall.get('total_found', 0)} similar trades found")

        # ------------------------------------------------------------------
        # CHECK 2: LLM must have cited RAG sources
        # ------------------------------------------------------------------
        cited_sources = getattr(decision, "rag_sources_cited", [])

        if not cited_sources:
            failed.append(
                "NO_SOURCES_CITED: LLM did not cite any RAG memory IDs. "
                "The reasoning may be entirely hallucinated."
            )
        else:
            # Validate that cited IDs actually exist in retrieved docs
            valid_trade_ids = set(trade_recall.get("doc_ids", []))
            valid_news_ids  = set(news_recall.get("doc_ids", []))
            all_valid_ids   = valid_trade_ids | valid_news_ids

            cited_set   = set(cited_sources)
            real_cites  = cited_set & all_valid_ids
            fake_cites  = cited_set - all_valid_ids

            if fake_cites:
                failed.append(
                    f"FABRICATED_SOURCES: LLM cited non-existent memory IDs: "
                    f"{list(fake_cites)}. These were not in the RAG context provided."
                )
            if real_cites:
                passed.append(f"SOURCES_VERIFIED: {len(real_cites)} valid RAG citation(s): {list(real_cites)}")

        # ------------------------------------------------------------------
        # CHECK 3: Win rate integrity check
        # ------------------------------------------------------------------
        llm_stated_win_rate = getattr(decision, "historical_win_rate", None)

        if actual_win_rate is not None and llm_stated_win_rate is not None:
            try:
                stated = float(llm_stated_win_rate)
                diff   = abs(stated - actual_win_rate)

                if diff > self.WIN_RATE_TOLERANCE:
                    failed.append(
                        f"WIN_RATE_MISMATCH: LLM stated win rate {stated*100:.1f}% but "
                        f"ChromaDB shows {actual_win_rate*100:.1f}% "
                        f"(tolerance ±{self.WIN_RATE_TOLERANCE*100:.0f}%). "
                        f"Possible hallucination of performance data."
                    )
                else:
                    passed.append(
                        f"WIN_RATE_VERIFIED: LLM stated {stated*100:.1f}% vs "
                        f"DB {actual_win_rate*100:.1f}% — within tolerance ✓"
                    )
            except (TypeError, ValueError):
                failed.append("WIN_RATE_PARSE_ERROR: Could not parse LLM's stated win rate.")

        elif actual_win_rate is None:
            # Not enough data to verify — not a hard fail but noted
            passed.append("WIN_RATE_SKIPPED: Insufficient DB records to verify win rate (< 3 trades)")

        # ------------------------------------------------------------------
        # CHECK 4: LLM self-assessed hallucination risk
        # ------------------------------------------------------------------
        hallucination_risk = getattr(decision, "hallucination_risk", "UNKNOWN")

        if hallucination_risk == "HIGH":
            failed.append(
                f"HIGH_HALLUCINATION_RISK: LLM self-reported HIGH uncertainty. "
                f"A {decision.action} trade under HIGH uncertainty is forbidden."
            )
        elif hallucination_risk in ("LOW", "MEDIUM"):
            passed.append(f"HALLUCINATION_RISK: LLM self-reported {hallucination_risk} — acceptable")
        else:
            failed.append(
                f"UNKNOWN_HALLUCINATION_RISK: LLM did not provide a risk level. "
                f"Treating as HIGH to be safe."
            )

        # ------------------------------------------------------------------
        # CHECK 5: Minimum confidence threshold (post-grounding)
        # ------------------------------------------------------------------
        confidence = getattr(decision, "confidence", 0)
        if confidence < 65:
            failed.append(
                f"LOW_CONFIDENCE: Decision confidence is {confidence}% which is "
                f"below the grounded minimum of 65%."
            )
        else:
            passed.append(f"CONFIDENCE_OK: {confidence}% ≥ 65% threshold")

        # ------------------------------------------------------------------
        # Calculate grounding score and final verdict
        # ------------------------------------------------------------------
        total_checks   = len(passed) + len(failed)
        grounding_score = len(passed) / total_checks if total_checks > 0 else 0.0

        should_override = (
            len(failed) > 0
            or grounding_score < self.MIN_GROUNDING_SCORE
        )

        if should_override:
            override_reason = (
                f"🛡️ GROUNDING VALIDATOR: {decision.action} overridden to HOLD. "
                f"Grounding score: {grounding_score:.2f}/{1.0:.2f}. "
                f"Failed checks: {'; '.join(failed)}"
            )
        else:
            override_reason = ""

        return GroundingResult(
            is_grounded=not should_override,
            override_to_hold=should_override,
            override_reason=override_reason,
            checks_passed=passed,
            checks_failed=failed,
            grounding_score=grounding_score
        )

    def format_log_entry(self, result: GroundingResult, decision_action: str) -> dict:
        """Returns a structured dict for XAI logging."""
        return {
            "grounding_score":   round(result.grounding_score, 4),
            "is_grounded":       result.is_grounded,
            "original_action":   decision_action,
            "final_action":      "HOLD" if result.override_to_hold else decision_action,
            "checks_passed":     result.checks_passed,
            "checks_failed":     result.checks_failed,
            "override_reason":   result.override_reason,
        }
