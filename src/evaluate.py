"""Reliability harness for the agentic recommender."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .agent import RecommendationAgent
from .recommender import load_songs


@dataclass(frozen=True)
class EvalCase:
    name: str
    user_prefs: Dict
    min_confidence: float = 0.55


def run_evaluation() -> None:
    songs = load_songs("data/songs.csv")
    agent = RecommendationAgent()

    cases: List[EvalCase] = [
        EvalCase(
            name="high_energy_pop",
            user_prefs={
                "genre": "pop",
                "mood": "happy",
                "energy": 0.8,
                "likes_acoustic": False,
                "target_popularity": 70,
                "target_decade": 2020,
            },
        ),
        EvalCase(
            name="chill_lofi",
            user_prefs={
                "genre": "lofi",
                "mood": "chill",
                "energy": 0.35,
                "likes_acoustic": True,
                "target_popularity": 45,
                "target_decade": 2020,
            },
        ),
        EvalCase(
            name="adversarial_moody_high_energy",
            user_prefs={
                "genre": "pop",
                "mood": "moody",
                "energy": 0.95,
                "likes_acoustic": False,
                "target_popularity": 80,
                "target_decade": 2021,
            },
        ),
    ]

    passed = 0
    confidences: List[float] = []
    failure_names: List[str] = []

    for case in cases:
        result = agent.run(case.user_prefs, songs, k=5)
        confidence = result.guardrails.confidence
        confidences.append(confidence)
        case_passed = result.guardrails.passed and confidence >= case.min_confidence
        if case_passed:
            passed += 1
        else:
            failure_names.append(case.name)
        print(
            f"[{case.name}] pass={case_passed} confidence={confidence:.2f} "
            f"checks={result.guardrails.checks_passed}/{result.guardrails.checks_total} attempts={result.attempts}"
        )

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    print("\n=== Evaluation Summary ===")
    print(f"Passed: {passed}/{len(cases)}")
    print(f"Average confidence: {avg_conf:.2f}")
    print(f"Failed cases: {', '.join(failure_names) if failure_names else 'none'}")


if __name__ == "__main__":
    run_evaluation()
