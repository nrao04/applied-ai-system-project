from src.agent import RecommendationAgent
from src.guardrails import GuardrailConfig, detect_profile_warnings, run_guardrails
from src.recommender import Song, song_to_dict


def _songs():
    return [
        song_to_dict(
            Song(
                id=1,
                title="Upbeat Pop",
                artist="A1",
                genre="pop",
                mood="happy",
                energy=0.86,
                tempo_bpm=122,
                valence=0.86,
                danceability=0.84,
                acousticness=0.2,
            )
        ),
        song_to_dict(
            Song(
                id=2,
                title="Focused Lofi",
                artist="A2",
                genre="lofi",
                mood="chill",
                energy=0.35,
                tempo_bpm=88,
                valence=0.58,
                danceability=0.52,
                acousticness=0.9,
            )
        ),
        song_to_dict(
            Song(
                id=3,
                title="Rock Burst",
                artist="A3",
                genre="rock",
                mood="intense",
                energy=0.92,
                tempo_bpm=140,
                valence=0.5,
                danceability=0.62,
                acousticness=0.12,
            )
        ),
    ]


def test_agent_run_returns_trace_and_recommendations():
    agent = RecommendationAgent()
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.85, "likes_acoustic": False}
    result = agent.run(prefs, _songs(), k=2)

    assert len(result.recommendations) == 2
    assert result.trace
    assert result.guardrails.checks_total == 3
    assert 0.0 <= result.guardrails.confidence <= 1.0


def test_guardrails_warn_on_contradictory_profile():
    warnings = detect_profile_warnings({"mood": "moody", "energy": 0.96})
    assert any("very high energy" in warning for warning in warnings)


def test_guardrails_fail_on_low_diversity():
    recs = [
        ({"genre": "pop", "artist": "A1"}, 7.0, "x"),
        ({"genre": "pop", "artist": "A2"}, 6.8, "y"),
    ]
    report = run_guardrails(recs, {"genre": "pop"}, GuardrailConfig(min_unique_genres=2))
    assert report.passed is False
    assert any("Genre diversity too low" in failure for failure in report.failures)
