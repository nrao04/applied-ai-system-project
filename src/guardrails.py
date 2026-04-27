from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class GuardrailConfig:
    """Configuration for recommendation quality checks."""

    min_unique_genres: int = 2
    min_top_score: float = 5.0
    min_confidence: float = 0.55


@dataclass(frozen=True)
class GuardrailReport:
    """Result of guardrail validation."""

    passed: bool
    confidence: float
    checks_passed: int
    checks_total: int
    failures: List[str]
    warnings: List[str]
    metrics: Dict[str, float]


def detect_profile_warnings(user_prefs: Dict) -> List[str]:
    """Return non-fatal warnings for contradictory or underspecified preferences."""
    warnings: List[str] = []

    mood = str(user_prefs.get("mood", "")).strip().lower()
    energy = float(user_prefs.get("energy", user_prefs.get("target_energy", 0.5)))

    if mood in {"moody", "sad", "melancholic"} and energy >= 0.9:
        warnings.append(
            "Profile mixes low-valence mood with very high energy; recommendations may trade off heavily."
        )
    if not user_prefs.get("genre") and not user_prefs.get("favorite_genre"):
        warnings.append("No genre preference provided; mode selection may rely on mood/energy only.")
    return warnings


def compute_confidence(
    recommendations: Sequence[Tuple[Dict, float, str]],
    min_unique_genres: int,
) -> Tuple[float, Dict[str, float]]:
    """Compute confidence and supporting metrics from recommendation set quality."""
    if not recommendations:
        return 0.0, {"top_score": 0.0, "score_gap": 0.0, "genre_diversity_ratio": 0.0}

    scores = [float(score) for _, score, _ in recommendations]
    top_score = scores[0]
    score_gap = top_score - scores[1] if len(scores) > 1 else top_score
    unique_genres = {
        str(song.get("genre", "")).strip().lower() for song, _, _ in recommendations if song.get("genre")
    }

    score_component = min(1.0, max(0.0, top_score / 10.0))
    gap_component = min(1.0, max(0.0, score_gap / 2.0))
    diversity_component = min(1.0, max(0.0, len(unique_genres) / float(max(1, min_unique_genres))))
    confidence = 0.5 * score_component + 0.3 * diversity_component + 0.2 * gap_component

    return confidence, {
        "top_score": top_score,
        "score_gap": score_gap,
        "genre_diversity_ratio": diversity_component,
    }


def run_guardrails(
    recommendations: Sequence[Tuple[Dict, float, str]],
    user_prefs: Dict,
    config: GuardrailConfig | None = None,
) -> GuardrailReport:
    """Validate recommendation results and produce confidence + failure reasons."""
    cfg = config or GuardrailConfig()
    warnings = detect_profile_warnings(user_prefs)
    failures: List[str] = []

    confidence, metrics = compute_confidence(recommendations, cfg.min_unique_genres)
    unique_genres = {
        str(song.get("genre", "")).strip().lower() for song, _, _ in recommendations if song.get("genre")
    }
    top_score = float(recommendations[0][1]) if recommendations else 0.0

    checks_total = 3
    checks_passed = 0

    if len(unique_genres) >= cfg.min_unique_genres:
        checks_passed += 1
    else:
        failures.append(f"Genre diversity too low: {len(unique_genres)} < {cfg.min_unique_genres}.")

    if top_score >= cfg.min_top_score:
        checks_passed += 1
    else:
        failures.append(f"Top recommendation score too low: {top_score:.2f} < {cfg.min_top_score:.2f}.")

    if confidence >= cfg.min_confidence:
        checks_passed += 1
    else:
        failures.append(f"Confidence below threshold: {confidence:.2f} < {cfg.min_confidence:.2f}.")

    return GuardrailReport(
        passed=checks_passed == checks_total,
        confidence=confidence,
        checks_passed=checks_passed,
        checks_total=checks_total,
        failures=failures,
        warnings=warnings,
        metrics=metrics,
    )
