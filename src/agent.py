from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .guardrails import GuardrailConfig, GuardrailReport, run_guardrails
from .recommender import (
    DEFAULT_ARTIST_REPEAT_PENALTY,
    DEFAULT_GENRE_REPEAT_PENALTY,
    recommend_songs,
)


logger = logging.getLogger(__name__)


@dataclass
class AgentStrategy:
    """Runtime strategy chosen by planner and adjusted by repair."""

    scoring_mode: str
    apply_diversity: bool
    artist_repeat_penalty: float
    genre_repeat_penalty: float


@dataclass
class AgentRunResult:
    """Structured result of one agent execution."""

    recommendations: List[Tuple[Dict, float, str]]
    strategy: AgentStrategy
    guardrails: GuardrailReport
    trace: List[str]
    attempts: int


class RecommendationAgent:
    """Plan-act-check-repair agent over the deterministic recommender."""

    def __init__(
        self,
        guardrail_config: GuardrailConfig | None = None,
        max_attempts: int = 2,
    ) -> None:
        self.guardrail_config = guardrail_config or GuardrailConfig()
        self.max_attempts = max(1, max_attempts)

    def plan(self, user_prefs: Dict) -> AgentStrategy:
        mood = str(user_prefs.get("mood", "")).strip().lower()
        energy = float(user_prefs.get("energy", user_prefs.get("target_energy", 0.5)))
        has_genre = bool(user_prefs.get("genre") or user_prefs.get("favorite_genre"))

        if energy >= 0.82:
            mode = "energy_focused"
        elif mood in {"chill", "calm", "focused"}:
            mode = "mood_first"
        elif has_genre:
            mode = "genre_first"
        else:
            mode = "balanced"

        strategy = AgentStrategy(
            scoring_mode=mode,
            apply_diversity=True,
            artist_repeat_penalty=DEFAULT_ARTIST_REPEAT_PENALTY,
            genre_repeat_penalty=DEFAULT_GENRE_REPEAT_PENALTY,
        )
        logger.info("planner_selected_strategy mode=%s", mode)
        return strategy

    def act(self, user_prefs: Dict, songs: List[Dict], strategy: AgentStrategy, k: int) -> List[Tuple[Dict, float, str]]:
        return recommend_songs(
            user_prefs=user_prefs,
            songs=songs,
            k=k,
            scoring_mode=strategy.scoring_mode,
            apply_diversity=strategy.apply_diversity,
            artist_repeat_penalty=strategy.artist_repeat_penalty,
            genre_repeat_penalty=strategy.genre_repeat_penalty,
        )

    def repair(self, strategy: AgentStrategy, report: GuardrailReport) -> AgentStrategy:
        # Increase diversity pressure and move to balanced mode if a check failed.
        return AgentStrategy(
            scoring_mode="balanced",
            apply_diversity=True,
            artist_repeat_penalty=min(1.5, strategy.artist_repeat_penalty + 0.25),
            genre_repeat_penalty=min(1.2, strategy.genre_repeat_penalty + 0.25),
        )

    def run(self, user_prefs: Dict, songs: List[Dict], k: int = 5) -> AgentRunResult:
        trace: List[str] = []
        strategy = self.plan(user_prefs)
        trace.append(
            f"plan: selected mode={strategy.scoring_mode}, diversity={strategy.apply_diversity}, "
            f"artist_penalty={strategy.artist_repeat_penalty:.2f}, genre_penalty={strategy.genre_repeat_penalty:.2f}"
        )

        recommendations: List[Tuple[Dict, float, str]] = []
        report = run_guardrails(recommendations, user_prefs, self.guardrail_config)

        for attempt in range(1, self.max_attempts + 1):
            recommendations = self.act(user_prefs, songs, strategy, k)
            trace.append(f"act: attempt={attempt}, produced_top_k={len(recommendations)}")

            report = run_guardrails(recommendations, user_prefs, self.guardrail_config)
            trace.append(
                f"check: pass={report.passed}, confidence={report.confidence:.2f}, "
                f"checks={report.checks_passed}/{report.checks_total}"
            )

            if report.warnings:
                trace.append(f"check_warnings: {' | '.join(report.warnings)}")

            if report.passed or attempt == self.max_attempts:
                break

            strategy = self.repair(strategy, report)
            trace.append(
                f"repair: adjusted mode={strategy.scoring_mode}, artist_penalty={strategy.artist_repeat_penalty:.2f}, "
                f"genre_penalty={strategy.genre_repeat_penalty:.2f}"
            )

        return AgentRunResult(
            recommendations=recommendations,
            strategy=strategy,
            guardrails=report,
            trace=trace,
            attempts=attempt,
        )
