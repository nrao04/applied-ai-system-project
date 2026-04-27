# Model Card - Agentic Music Recommender

## System summary

This system recommends songs from a local CSV catalog using deterministic scoring plus an agentic orchestration layer (`plan -> act -> check -> repair`). The base scorer prioritizes genre, mood, energy alignment, and acoustic preference with optional advanced signals. The agent adds strategy selection, guardrail validation, confidence scoring, and retry behavior.

## Intended use

- Educational demonstration of applied AI system design.
- Small-scale, transparent recommendation experiments.
- Reliability testing with predefined user preference cases.

Not intended for production personalization, high-stakes ranking, or sensitive decision support.

## Base project origin (Modules 1-3)

Original project: **Music Recommender Simulation (Module 3)**.  
Original capability: rank songs by weighted preferences and print explanation strings for each recommendation.  
Extension in final project: add agentic loop, guardrails, confidence, and reliability harness.

## Reliability and testing

- Unit tests:
  - recommendation ordering and non-empty explanations,
  - agent run trace/metadata integrity,
  - guardrail warning and diversity failure checks.
- Evaluation script:
  - executes predefined profiles,
  - reports pass/fail count, average confidence, and failing cases.

## Limitations and bias

- Dataset is small and synthetic, so exposure bias is likely.
- Heavier genre weighting can create filter-bubble behavior.
- Confidence score is heuristic and may overestimate quality on narrow catalogs.
- Guardrails evaluate ranking quality, not fairness across demographic groups.

## Misuse risks and mitigations

- **Risk:** users interpret deterministic scores as objective quality.
  - **Mitigation:** provide reason strings, confidence values, and warnings.
- **Risk:** overfitting behavior to one genre cluster.
  - **Mitigation:** enforce genre diversity checks and repair strategy.
- **Risk:** deploying beyond intended educational scope.
  - **Mitigation:** explicit non-production constraints in docs and card.

## Reliability surprise

The contradictory profile (`moody` with very high energy) still produced plausible top songs, but confidence dropped and warnings became essential for interpretation. This confirmed that recommendation quality can look acceptable while preference coherence is weak.

## AI collaboration reflection

- **Helpful AI suggestion:** using a structured `plan/act/check/repair` loop improved both explainability and debugging compared with a single-pass ranker.
- **Flawed AI suggestion:** an early idea pushed confidence thresholds too aggressively, which caused false failures on valid but narrow profiles; thresholds were tuned down after test runs.

## Ethical reflection

The system is transparent but still encodes subjective assumptions through scoring weights and thresholds. Responsible use requires documenting these assumptions, measuring failure patterns, and warning users when profile constraints conflict or context is too limited.
