"""
Command line runner for the Music Recommender Simulation.

Run from the project root:

    python -m src.main
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from tabulate import tabulate

from .recommender import (
    DEFAULT_ARTIST_REPEAT_PENALTY,
    DEFAULT_GENRE_REPEAT_PENALTY,
    load_songs,
    recommend_songs,
    SCORING_MODES,
)


def recommendations_table(
    recs: List[Tuple[Dict, float, str]], tablefmt: str = "github"
) -> str:
    """Challenge 4: compact table with scores and full reason strings."""
    rows = []
    for i, (song, score, expl) in enumerate(recs, start=1):
        rows.append([i, song["title"], song["artist"], f"{score:.2f}", expl])
    return tabulate(
        rows,
        headers=["#", "Title", "Artist", "Score", "Reasons"],
        tablefmt=tablefmt,
        maxcolwidths=[None, 22, 16, 8, 56],
    )


def main() -> None:
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

    all_modes = ["balanced", "genre_first", "mood_first", "energy_focused"]
    print("Available scoring modes:", ", ".join(sorted(SCORING_MODES.keys())))
    print()

    first = True
    for label, user_prefs in profiles.items():
        print(f"## {label}")
        modes = all_modes if first else ["balanced"]
        for mode in modes:
            recs = recommend_songs(
                user_prefs, songs, k=5, scoring_mode=mode, apply_diversity=True
            )
            print(
                f"\n** Mode: {mode} ** (diversity: −{DEFAULT_ARTIST_REPEAT_PENALTY:.2f} repeat artist, "
                f"−{DEFAULT_GENRE_REPEAT_PENALTY:.2f} repeat genre)\n"
            )
            print(recommendations_table(recs))
        first = False
        print("\n")

    # Compact sanity demo: one profile, one mode — easy to screenshot.
    slim = recommend_songs(
        profiles["High-energy pop (default)"],
        songs,
        k=5,
        scoring_mode="balanced",
        apply_diversity=True,
    )
    print("--- Quick copy: pop profile, balanced + diversity ---\n")
    print(recommendations_table(slim))


if __name__ == "__main__":
    main()
