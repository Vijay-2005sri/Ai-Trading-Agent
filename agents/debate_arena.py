"""
=============================================================================
DEBATE ARENA — Multi-LLM Consensus Engine for Gold (XAUUSD)
=============================================================================
Orchestrates a 3-round debate protocol where ALL available LLM providers
independently analyze market data, critique each other's reasoning, and
vote on a consensus trading decision.

Protocol:
  Round 1 — Independent Analysis (Parallel)
    Each model receives identical data and produces its own TradeDecision.
  Round 2 — Debate & Roast
    Each model sees ALL Round 1 decisions and writes a critique.
    Models can change their position if convinced by another's argument.
  Round 3 — Consensus Vote
    Each model votes on the best action considering all arguments.
    Majority vote wins. Ties → HOLD (safety first).

Rate Limit Safety:
  - Minimum 2 models required for a valid debate
  - If rate limits hit mid-debate, continues with remaining models
  - Falls back to single-model mode if < 2 models available
=============================================================================
"""

import json
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# DEBATE SCHEMAS
# =============================================================================

class DebateCritique(BaseModel):
    """Round 2: A model's critique of all other models' decisions."""
    model_name: str = Field(description="Name of the model writing this critique")
    agreements: list[str] = Field(
        default_factory=list,
        description="List of models this model agrees with and why (e.g., 'I agree with Groq because...')"
    )
    disagreements: list[str] = Field(
        default_factory=list,
        description="List of models this model disagrees with and why (e.g., 'Gemini's SELL is wrong because...')"
    )
    revised_action: str = Field(
        description="After seeing all arguments: BUY, SELL, or HOLD. May differ from Round 1."
    )
    revised_confidence: int = Field(
        description="Revised confidence 0-100 after considering all arguments."
    )
    key_argument: str = Field(
        description="The single strongest argument supporting the revised position."
    )


class ConsensusVote(BaseModel):
    """Round 3: A model's final vote on the best action."""
    voter_name: str = Field(description="Name of the model casting this vote")
    chosen_action: str = Field(description="Final vote: BUY, SELL, or HOLD")
    chosen_model: str = Field(
        description="Which model's reasoning was most convincing (can be self)"
    )
    final_confidence: int = Field(description="Final confidence 0-100")
    vote_reasoning: str = Field(
        description="Brief explanation for why this action was chosen as the consensus"
    )


# =============================================================================
# DEBATE RESULT — Full output of a completed debate
# =============================================================================

@dataclass
class DebateResult:
    """Complete record of a 3-round debate."""
    pair: str                                          # Always "XAUUSD" for now
    timestamp: str = ""                                # ISO timestamp
    models_participated: list[str] = field(default_factory=list)
    round1_decisions: dict = field(default_factory=dict)   # {model_name: TradeDecision}
    round2_critiques: list[dict] = field(default_factory=list)
    round3_votes: list[dict] = field(default_factory=list)
    consensus_action: str = "HOLD"                     # Final voted action
    consensus_confidence: int = 0                      # Average confidence of winners
    consensus_reasoning: str = ""                      # Combined reasoning
    winning_decision: object = None                    # The TradeDecision to execute
    debate_successful: bool = False                    # True if ≥2 models debated
    vote_tally: dict = field(default_factory=dict)     # {"BUY": 3, "SELL": 1, "HOLD": 1}
    transcript: list[str] = field(default_factory=list)  # Human-readable log

    def to_log_dict(self) -> dict:
        """Convert to a JSON-serializable dict for trade_log.json."""
        return {
            "pair": self.pair,
            "timestamp": self.timestamp,
            "models_participated": self.models_participated,
            "round1_decisions": {
                name: {
                    "action": d.action,
                    "confidence": d.confidence,
                    "reasoning": d.reasoning[:200],
                    "strategy_used": d.strategy_used,
                }
                for name, d in self.round1_decisions.items()
            },
            "round2_critiques": self.round2_critiques,
            "round3_votes": self.round3_votes,
            "consensus_action": self.consensus_action,
            "consensus_confidence": self.consensus_confidence,
            "consensus_reasoning": self.consensus_reasoning[:300],
            "vote_tally": self.vote_tally,
            "debate_successful": self.debate_successful,
        }


# =============================================================================
# DEBATE ARENA ENGINE
# =============================================================================

class DebateArena:
    """
    Orchestrates the 3-round multi-LLM debate for Gold (XAUUSD).

    Usage:
        arena = DebateArena(llm_provider)
        result = arena.run_debate(
            base_prompt=..., rag_context=..., pair="XAUUSD"
        )
        # result.winning_decision is a TradeDecision ready for execution
    """

    MIN_MODELS_FOR_DEBATE = 2      # Minimum models to proceed
    ROUND1_TIMEOUT = 45            # Seconds per model in Round 1
    ROUND2_TIMEOUT = 30            # Seconds per model in Round 2
    ROUND3_TIMEOUT = 30            # Seconds per model in Round 3

    def __init__(self, llm_provider):
        """
        Args:
            llm_provider: An instance of LLMProvider with debate methods
        """
        self.llm = llm_provider

    # =====================================================================
    # MAIN ENTRY POINT
    # =====================================================================

    def run_debate(
        self,
        base_prompt: str,
        rag_context: str,
        pair: str = "XAUUSD"
    ) -> DebateResult:
        """
        Execute the full 3-round debate protocol.

        Args:
            base_prompt:  The complete analysis prompt (quant + fundamentals + concepts)
            rag_context:  RAG memory context block
            pair:         Trading pair (default: XAUUSD)

        Returns:
            DebateResult with the consensus decision and full transcript.
        """
        result = DebateResult(
            pair=pair,
            timestamp=datetime.now().isoformat()
        )

        available_models = self.llm.get_all_available_names()
        result.transcript.append(
            f"=== DEBATE ARENA INITIATED for {pair} ===\n"
            f"Available models: {', '.join(available_models)} ({len(available_models)} total)"
        )

        if len(available_models) < self.MIN_MODELS_FOR_DEBATE:
            result.transcript.append(
                f"⚠️ Only {len(available_models)} model(s) available. "
                f"Need {self.MIN_MODELS_FOR_DEBATE}. Falling back to single-model mode."
            )
            result.debate_successful = False
            return result

        # ── ROUND 1: Independent Analysis (Parallel) ─────────────────
        print(f"\n    🏟️  DEBATE ROUND 1: Independent Analysis ({len(available_models)} models)...")
        result.transcript.append("\n--- ROUND 1: INDEPENDENT ANALYSIS ---")

        round1_decisions = self._run_round1(available_models, base_prompt, rag_context, pair)
        result.round1_decisions = round1_decisions
        result.models_participated = list(round1_decisions.keys())

        if len(round1_decisions) < self.MIN_MODELS_FOR_DEBATE:
            result.transcript.append(
                f"⚠️ Only {len(round1_decisions)} model(s) responded in Round 1. "
                f"Cannot proceed with debate."
            )
            # If exactly 1 model responded, use its decision as-is
            if len(round1_decisions) == 1:
                sole_model = list(round1_decisions.keys())[0]
                result.winning_decision = round1_decisions[sole_model]
                result.consensus_action = result.winning_decision.action
                result.consensus_confidence = result.winning_decision.confidence
                result.consensus_reasoning = f"Single model ({sole_model}) decision — no debate possible."
            result.debate_successful = False
            return result

        for name, decision in round1_decisions.items():
            result.transcript.append(
                f"  {name}: {decision.action} (Conf: {decision.confidence}%) "
                f"| Strategy: {decision.strategy_used}"
            )
            print(
                f"      {name}: {decision.action} "
                f"(Conf: {decision.confidence}% | {decision.strategy_used})"
            )

        # ── ROUND 2: Debate & Roast ──────────────────────────────────
        print(f"\n    🏟️  DEBATE ROUND 2: Debate & Roast ({len(round1_decisions)} models)...")
        result.transcript.append("\n--- ROUND 2: DEBATE & ROAST ---")

        debate_brief = self._build_debate_brief(round1_decisions, pair)
        round2_critiques = self._run_round2(round1_decisions, debate_brief)
        result.round2_critiques = round2_critiques

        for critique in round2_critiques:
            model = critique.get("model_name", "Unknown")
            revised = critique.get("revised_action", "?")
            conf = critique.get("revised_confidence", 0)
            key_arg = critique.get("key_argument", "")[:100]
            result.transcript.append(
                f"  {model}: Revised to {revised} ({conf}%) | Key: {key_arg}"
            )
            print(f"      {model}: {revised} ({conf}%) — \"{key_arg[:60]}...\"")

        # ── ROUND 3: Consensus Vote ──────────────────────────────────
        print(f"\n    🏟️  DEBATE ROUND 3: Consensus Vote...")
        result.transcript.append("\n--- ROUND 3: CONSENSUS VOTE ---")

        full_transcript = self._build_vote_context(round1_decisions, round2_critiques, pair)
        round3_votes = self._run_round3(round1_decisions, full_transcript)
        result.round3_votes = round3_votes

        # ── Tally votes and determine consensus ──────────────────────
        consensus = self._tally_votes(round3_votes, round1_decisions)
        result.consensus_action = consensus["action"]
        result.consensus_confidence = consensus["confidence"]
        result.consensus_reasoning = consensus["reasoning"]
        result.winning_decision = consensus["winning_decision"]
        result.vote_tally = consensus["tally"]
        result.debate_successful = True

        tally_str = " | ".join(f"{a}: {c}" for a, c in result.vote_tally.items())
        result.transcript.append(
            f"\n🏆 CONSENSUS: {result.consensus_action} "
            f"(Confidence: {result.consensus_confidence}%) "
            f"| Votes: {tally_str}"
        )
        print(
            f"\n    🏆 CONSENSUS: {result.consensus_action} "
            f"(Conf: {result.consensus_confidence}% | Tally: {tally_str})"
        )

        return result

    # =====================================================================
    # ROUND 1 — Independent Analysis (Parallel)
    # =====================================================================

    def _run_round1(
        self,
        model_names: list[str],
        base_prompt: str,
        rag_context: str,
        pair: str
    ) -> dict:
        """
        Each model independently analyzes the data and produces a TradeDecision.
        Runs in parallel using threads for speed.

        Returns: {model_name: TradeDecision, ...} for models that responded.
        """
        decisions = {}
        lock = threading.Lock()

        def _query_model(name):
            try:
                decision = self.llm.invoke_structured_on_provider(
                    provider_name=name,
                    base_prompt=base_prompt,
                    rag_context=rag_context,
                )
                if decision is not None:
                    decision.pair = pair
                    with lock:
                        decisions[name] = decision
            except Exception as e:
                print(f"      ⚠️ {name} Round 1 error: {str(e)[:80]}")

        with ThreadPoolExecutor(max_workers=len(model_names)) as executor:
            futures = {executor.submit(_query_model, name): name for name in model_names}
            for future in as_completed(futures, timeout=self.ROUND1_TIMEOUT):
                try:
                    future.result()
                except Exception:
                    pass  # Timeouts and errors are handled in _query_model

        return decisions

    # =====================================================================
    # ROUND 2 — Debate & Roast
    # =====================================================================

    def _build_debate_brief(self, decisions: dict, pair: str) -> str:
        """
        Compile all Round 1 decisions into a brief for debate.
        Each model will see what every other model decided and why.
        """
        lines = [
            f"=== DEBATE BRIEF: {pair} ===",
            f"The following {len(decisions)} AI models have independently analyzed {pair}.",
            "Review each model's decision, then critique their reasoning.\n"
        ]

        for name, d in decisions.items():
            lines.append(
                f"--- {name} ---\n"
                f"  Action:     {d.action}\n"
                f"  Confidence: {d.confidence}%\n"
                f"  Strategy:   {d.strategy_used}\n"
                f"  Reasoning:  {d.reasoning[:300]}\n"
                f"  SL: {d.suggested_sl} | TP: {d.suggested_tp}\n"
                f"  RAG Sources: {', '.join(d.rag_sources_cited) if d.rag_sources_cited else 'None'}\n"
                f"  Hallucination Risk: {d.hallucination_risk}\n"
            )

        return "\n".join(lines)

    def _run_round2(self, decisions: dict, debate_brief: str) -> list[dict]:
        """
        Each model reads the debate brief and writes a critique.
        Can revise its own position if convinced by another model's argument.
        """
        critiques = []
        schema_json = json.dumps(DebateCritique.model_json_schema(), indent=2)

        for name in decisions:
            prompt = (
                f"You are {name} in a trading debate.\n\n"
                f"{debate_brief}\n\n"
                f"Now write your critique:\n"
                f"1. Which models do you AGREE with and why?\n"
                f"2. Which models do you DISAGREE with and why? Be specific.\n"
                f"3. After considering all arguments, what is your REVISED position?\n"
                f"4. State your single strongest argument.\n\n"
                f"Respond ONLY with valid JSON matching this schema:\n{schema_json}"
            )

            try:
                response = self.llm.invoke_on_provider(name, prompt)
                if response:
                    # Parse the JSON response
                    cleaned = response.strip()
                    if cleaned.startswith("```"):
                        lines = cleaned.split("\n")
                        lines = [l for l in lines if not l.strip().startswith("```")]
                        cleaned = "\n".join(lines)

                    data = json.loads(cleaned)
                    data["model_name"] = name  # Ensure model name is set
                    critiques.append(data)
                else:
                    print(f"      ⚠️ {name} did not respond in Round 2.")
            except Exception as e:
                print(f"      ⚠️ {name} Round 2 parse error: {str(e)[:80]}")
                # Still include a minimal critique so the model isn't lost
                critiques.append({
                    "model_name": name,
                    "agreements": [],
                    "disagreements": [],
                    "revised_action": decisions[name].action,
                    "revised_confidence": decisions[name].confidence,
                    "key_argument": f"[Round 2 failed for {name} — keeping Round 1 position]"
                })

        return critiques

    # =====================================================================
    # ROUND 3 — Consensus Vote
    # =====================================================================

    def _build_vote_context(
        self, decisions: dict, critiques: list[dict], pair: str
    ) -> str:
        """Build the full debate transcript for Round 3 voting."""
        lines = [f"=== FULL DEBATE TRANSCRIPT: {pair} ===\n"]

        lines.append("--- ROUND 1: INDEPENDENT DECISIONS ---")
        for name, d in decisions.items():
            lines.append(
                f"  {name}: {d.action} ({d.confidence}%) — {d.reasoning[:150]}"
            )

        lines.append("\n--- ROUND 2: CRITIQUES & REVISIONS ---")
        for c in critiques:
            name = c.get("model_name", "?")
            lines.append(f"  {name}:")
            for a in c.get("agreements", []):
                lines.append(f"    ✅ {a[:100]}")
            for d in c.get("disagreements", []):
                lines.append(f"    ❌ {d[:100]}")
            lines.append(
                f"    → Revised: {c.get('revised_action', '?')} "
                f"({c.get('revised_confidence', 0)}%)"
            )
            lines.append(f"    Key argument: {c.get('key_argument', '')[:150]}")

        return "\n".join(lines)

    def _run_round3(self, decisions: dict, full_transcript: str) -> list[dict]:
        """
        Each model casts a final vote on the best action.
        They consider ALL Round 1 decisions + Round 2 critiques.
        """
        votes = []
        schema_json = json.dumps(ConsensusVote.model_json_schema(), indent=2)

        for name in decisions:
            prompt = (
                f"You are {name}. You have participated in a trading debate.\n\n"
                f"{full_transcript}\n\n"
                f"NOW CAST YOUR FINAL VOTE:\n"
                f"- Which action (BUY, SELL, or HOLD) should the team take?\n"
                f"- Whose reasoning was most convincing (can be your own)?\n"
                f"- What is your final confidence level?\n\n"
                f"Respond ONLY with valid JSON matching this schema:\n{schema_json}"
            )

            try:
                response = self.llm.invoke_on_provider(name, prompt)
                if response:
                    cleaned = response.strip()
                    if cleaned.startswith("```"):
                        lines = cleaned.split("\n")
                        lines = [l for l in lines if not l.strip().startswith("```")]
                        cleaned = "\n".join(lines)

                    data = json.loads(cleaned)
                    data["voter_name"] = name  # Ensure voter name is set
                    votes.append(data)
                else:
                    print(f"      ⚠️ {name} did not vote in Round 3.")
            except Exception as e:
                print(f"      ⚠️ {name} Round 3 parse error: {str(e)[:80]}")
                # Use their Round 2 revised position as their vote
                for c in []:  # We don't have critiques in scope, use Round 1
                    pass
                votes.append({
                    "voter_name": name,
                    "chosen_action": decisions[name].action,
                    "chosen_model": name,
                    "final_confidence": decisions[name].confidence,
                    "vote_reasoning": f"[Vote failed for {name} — using Round 1 position]"
                })

        return votes

    # =====================================================================
    # VOTE TALLYING
    # =====================================================================

    def _tally_votes(self, votes: list[dict], decisions: dict) -> dict:
        """
        Count votes and determine the consensus.

        Rules:
          1. Majority action wins (BUY vs SELL vs HOLD)
          2. Ties → highest average confidence wins
          3. Perfect tie → HOLD (capital preservation)
          4. The winning decision inherits the best SL/TP from the
             most-cited model in the winning camp

        Returns:
          {
            "action": "BUY",
            "confidence": 82,
            "reasoning": "...",
            "winning_decision": TradeDecision,
            "tally": {"BUY": 3, "SELL": 1, "HOLD": 1}
          }
        """
        from agents.llm_provider import TradeDecision

        # Count votes
        tally = {"BUY": 0, "SELL": 0, "HOLD": 0}
        confidence_by_action = {"BUY": [], "SELL": [], "HOLD": []}
        reasoning_by_action = {"BUY": [], "SELL": [], "HOLD": []}
        chosen_models_by_action = {"BUY": [], "SELL": [], "HOLD": []}

        for vote in votes:
            action = vote.get("chosen_action", "HOLD").upper()
            if action not in tally:
                action = "HOLD"
            tally[action] += 1
            confidence_by_action[action].append(vote.get("final_confidence", 50))
            reasoning_by_action[action].append(vote.get("vote_reasoning", ""))
            chosen_models_by_action[action].append(vote.get("chosen_model", ""))

        # Find the winner
        max_votes = max(tally.values())
        winners = [a for a, c in tally.items() if c == max_votes]

        if len(winners) == 1:
            winning_action = winners[0]
        else:
            # Tie-breaker: highest average confidence
            avg_conf = {
                a: (sum(confidence_by_action[a]) / len(confidence_by_action[a]))
                if confidence_by_action[a] else 0
                for a in winners
            }
            best_action = max(avg_conf, key=avg_conf.get)
            if avg_conf[best_action] > 0:
                winning_action = best_action
            else:
                winning_action = "HOLD"  # Perfect tie → safety

        # Calculate consensus confidence
        avg_confidence = int(
            sum(confidence_by_action[winning_action]) /
            len(confidence_by_action[winning_action])
        ) if confidence_by_action[winning_action] else 0

        # Find the most-cited model for the winning action
        best_model_name = None
        if chosen_models_by_action[winning_action]:
            # Most frequently cited model in the winning camp
            from collections import Counter
            model_counts = Counter(chosen_models_by_action[winning_action])
            best_model_name = model_counts.most_common(1)[0][0]

        # Build the winning TradeDecision
        # Start from the most-cited model's decision, or fall back to first available
        if best_model_name and best_model_name in decisions:
            base_decision = decisions[best_model_name]
        else:
            # Use the first model that voted for the winning action
            base_decision = None
            for name, d in decisions.items():
                if d.action == winning_action:
                    base_decision = d
                    break
            if base_decision is None:
                # No model originally voted for this action — create from scratch
                first_decision = list(decisions.values())[0]
                base_decision = first_decision

        # Create the consensus decision
        combined_reasoning = (
            f"DEBATE CONSENSUS ({tally}): "
            + " | ".join(r[:100] for r in reasoning_by_action[winning_action] if r)
        )

        winning_decision = TradeDecision(
            action=winning_action,
            pair=base_decision.pair,
            confidence=avg_confidence,
            reasoning=combined_reasoning[:500],
            suggested_sl=base_decision.suggested_sl,
            suggested_tp=base_decision.suggested_tp,
            strategy_used=base_decision.strategy_used,
            rag_sources_cited=base_decision.rag_sources_cited,
            historical_win_rate=base_decision.historical_win_rate,
            hallucination_risk=base_decision.hallucination_risk,
        )

        return {
            "action": winning_action,
            "confidence": avg_confidence,
            "reasoning": combined_reasoning,
            "winning_decision": winning_decision,
            "tally": tally,
        }
