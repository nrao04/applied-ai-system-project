"""Command line runner for the agentic music recommender."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, List, Tuple

from tabulate import tabulate

from .agent import RecommendationAgent
from .recommender import load_songs


def recommendations_table(recs: List[Tuple[Dict, float, str]], tablefmt: str = "github") -> str:
    """Compact table with scores and full reason strings."""
    rows = []
    for i, (song, score, expl) in enumerate(recs, start=1):
        rows.append([i, song["title"], song["artist"], f"{score:.2f}", expl])
    return tabulate(
        rows,
        headers=["#", "Title", "Artist", "Score", "Reasons"],
        tablefmt=tablefmt,
        maxcolwidths=[None, 22, 16, 8, 56],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agentic Music Recommender")
    parser.add_argument("--mode", choices=["agentic", "baseline"], default="agentic")
    parser.add_argument("--verbose-trace", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose_trace else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
    )
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    # Richer prefs exercise Challenge 1 signals (optional keys are ignored if absent).
    profiles: Dict[str, Dict] = {
        "High-energy pop (default)": {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "likes_acoustic": False,
            "target_popularity": 70,
            "target_decade": 2020,
            "favorite_mood_tags": "euphoric,nostalgic",
            "lyric_theme": "nightlife",
            "language": "en",
        },
        "Chill lofi room": {
            "genre": "lofi",
            "mood": "chill",
            "energy": 0.35,
            "likes_acoustic": True,
            "target_popularity": 45,
            "target_decade": 2020,
            "favorite_mood_tags": "calm,focused",
            "lyric_theme": "introspection",
            "language": "en",
        },
        "Deep intense rock": {
            "genre": "rock",
            "mood": "intense",
            "energy": 0.9,
            "likes_acoustic": False,
            "target_popularity": 65,
            "target_decade": 2020,
            "favorite_mood_tags": "aggressive,euphoric",
            "lyric_theme": "rebellion",
            "language": "en",
        },
        "Adversarial — moody + max energy": {
            "genre": "pop",
            "mood": "moody",
            "energy": 0.95,
            "likes_acoustic": False,
            "target_popularity": 80,
            "target_decade": 2021,
            "favorite_mood_tags": "moody",
            "lyric_theme": "nightlife",
            "language": "en",
        },
    }

    agent = RecommendationAgent()
    for label, user_prefs in profiles.items():
        print(f"## {label}")
        if args.mode == "baseline":
            from .recommender import recommend_songs

            recs = recommend_songs(user_prefs, songs, k=5, scoring_mode="balanced", apply_diversity=True)
            print("\n** Baseline mode: balanced + diversity **\n")
            print(recommendations_table(recs))
            print()
            continue

        result = agent.run(user_prefs=user_prefs, songs=songs, k=5)
        print(
            f"\n** Agent mode: {result.strategy.scoring_mode} ** "
            f"(confidence={result.guardrails.confidence:.2f}, checks={result.guardrails.checks_passed}/{result.guardrails.checks_total})\n"
        )
        print(recommendations_table(result.recommendations))
        if args.verbose_trace:
            print("\nTrace:")
            for step in result.trace:
                print(f"- {step}")
        if result.guardrails.failures:
            print("\nGuardrail failures:")
            for failure in result.guardrails.failures:
                print(f"- {failure}")
        if result.guardrails.warnings:
            print("\nGuardrail warnings:")
            for warning in result.guardrails.warnings:
                print(f"- {warning}")
        print("\n")


if __name__ == "__main__":
    main()
