# Trading Concepts — Knowledge Base

## Purpose

This folder is the **core reasoning engine** for the AI Trading Agent. It is NOT a glossary. It teaches the agent how trading concepts actually appear on a chart, how they form, how to identify them, how to validate them, how they interact with each other, and most critically: **what should happen NEXT after a concept is identified.**

## Primary Framework

**ICT (Inner Circle Trader) / Smart Money Concepts (SMC)** is the primary methodology. All definitions, detection rules, and sequences use ICT/SMC terminology by default. Alternative interpretations are mentioned only when materially different, and are clearly labelled.

## How the Agent Should Use This Folder

1. The `master_knowledge_base.md` is the complete reference. When loaded into RAG, each section becomes a retrievable chunk.
2. The `cheat_sheet.md` is a condensed quick-reference of the same information — use it when the agent needs a fast lookup without consuming full context.
3. The `concept_relationships.md` maps how every concept connects to every other concept.
4. The `next_action_rules.md` provides explicit decision trees: "If the agent detects X on the chart, what should it investigate next?"

## Relationship to `strategy_library/`

The `strategy_library/` contains **code** that executes strategies (SMC, ICT Silver Bullet, Wyckoff, etc.). This `trading_concepts/` folder contains the **knowledge** that those strategies are built from. The strategies *use* these concepts; this folder *teaches* them.

Think of it this way:
- `trading_concepts/` = **what the agent knows** (education)
- `strategy_library/` = **what the agent does** (execution)

## File Index

| File | Purpose |
|------|---------|
| `master_knowledge_base.md` | Complete knowledge base — all concepts A through R with full depth |
| `cheat_sheet.md` | Condensed quick-reference of the same information |
| `concept_relationships.md` | How every concept interacts with every other concept |
| `next_action_rules.md` | Decision trees: "If X detected → check Y → then Z" |
