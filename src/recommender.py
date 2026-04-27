import csv
from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence, Tuple

# Baseline weights (scaled per scoring mode).
WEIGHT_GENRE_MATCH = 2.0
WEIGHT_MOOD_MATCH = 1.0
WEIGHT_ENERGY_ALIGNMENT = 2.0
WEIGHT_VALENCE_ALIGNMENT = 1.0
WEIGHT_DANCEABILITY_ALIGNMENT = 0.8
WEIGHT_ACOUSTIC_PREFERENCE = 1.2

# “Advanced” catalog features (Challenge 1).
WEIGHT_POPULARITY_ALIGNMENT = 0.75  # vs user target_popularity on 0–100 scale
WEIGHT_DECADE_PROXIMITY = 1.1  # user target_decade vs song release_decade (by decade steps)
WEIGHT_MOOD_TAG_MATCH = 0.42  # per overlapping tag
MAX_MOOD_TAG_BONUS = 1.26
WEIGHT_LYRIC_THEME_MATCH = 0.9
WEIGHT_LANGUAGE_MATCH = 0.35

# Diversity (Challenge 3): subtract when artist / genre already in the running shortlist.
DEFAULT_ARTIST_REPEAT_PENALTY = 0.85
DEFAULT_GENRE_REPEAT_PENALTY = 0.4


@dataclass(frozen=True)
class ModeMultipliers:
    """Strategy-style weight profile: each mode stresses different signals."""

    genre: float = 1.0
    mood: float = 1.0
    energy: float = 1.0
    valence: float = 1.0
    dance: float = 1.0
    acoustic: float = 1.0
    advanced: float = 1.0


SCORING_MODES: Dict[str, ModeMultipliers] = {
    "balanced": ModeMultipliers(),
    "genre_first": ModeMultipliers(
        genre=1.55, mood=0.72, energy=0.88, valence=0.95, dance=0.95, acoustic=0.95, advanced=0.92
    ),
    "mood_first": ModeMultipliers(
        genre=0.78, mood=1.6, energy=0.9, valence=1.05, dance=1.0, acoustic=1.0, advanced=0.95
    ),
    "energy_focused": ModeMultipliers(
        genre=0.82, mood=0.82, energy=1.55, valence=1.0, dance=1.05, acoustic=0.95, advanced=0.9
    ),
}


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """

    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    popularity: int = 50
    release_decade: int = 2010
    mood_tags: str = ""
    lyric_theme: str = ""
    language: str = "en"


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """

    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(
        self,
        user: UserProfile,
        k: int = 5,
        scoring_mode: str = "balanced",
        apply_diversity: bool = False,
    ) -> List[Song]:
        """Rank catalog songs for a user and return the top k."""
        prefs = user_profile_to_prefs(user)
        ranked: List[Tuple[float, Song, str]] = []
        for song in self.songs:
            row = song_to_dict(song)
            score, rs = score_song(prefs, row, mode=scoring_mode)
            ranked.append((score, song, "; ".join(rs)))
        ranked.sort(key=lambda x: x[0], reverse=True)
        if apply_diversity:
            ranked = _diversify_song_tuples(
                ranked,
                k,
                DEFAULT_ARTIST_REPEAT_PENALTY,
                DEFAULT_GENRE_REPEAT_PENALTY,
            )
        else:
            ranked = ranked[:k]
        return [song for _, song, _ in ranked]

    def explain_recommendation(
        self, user: UserProfile, song: Song, scoring_mode: str = "balanced"
    ) -> str:
        """Human-readable explanation for one song and user."""
        prefs = user_profile_to_prefs(user)
        _, reasons = score_song(prefs, song_to_dict(song), mode=scoring_mode)
        return "; ".join(reasons) if reasons else "No strong matches to the stated preferences."


def user_profile_to_prefs(user: UserProfile) -> Dict:
    """Map a UserProfile into the dictionary shape used by score_song."""
    return {
        "genre": user.favorite_genre,
        "mood": user.favorite_mood,
        "energy": float(user.target_energy),
        "likes_acoustic": user.likes_acoustic,
    }


def song_to_dict(song: Song) -> Dict:
    """Convert a Song dataclass to a plain dict for CSV-style scoring."""
    return asdict(song)


def _normalize_str(value: str) -> str:
    return (value or "").strip().lower()


def _genre_matches(user_genre: str, song_genre: str) -> bool:
    u = _normalize_str(user_genre)
    s = _normalize_str(song_genre)
    if not u or not s:
        return False
    return u == s or u in s or s in u


def _mood_matches(user_mood: str, song_mood: str) -> bool:
    return _normalize_str(user_mood) == _normalize_str(song_mood)


def _alignment_bonus(weight: float, song_value: float, target: float) -> Tuple[float, float]:
    """Return (points, distance) where points are weight * (1 - distance), capped."""
    distance = abs(float(song_value) - float(target))
    distance = min(distance, 1.0)
    return weight * (1.0 - distance), distance


def _parse_tags(blob: str) -> List[str]:
    if not blob:
        return []
    parts = []
    for token in blob.replace(",", "|").split("|"):
        t = _normalize_str(token)
        if t:
            parts.append(t)
    return parts


def _decade_steps(song_decade: int, user_decade: int) -> int:
    """Rough decade distance in steps of ten years."""
    return abs(int(song_decade) - int(user_decade)) // 10


def _mode_or_default(mode: str) -> ModeMultipliers:
    return SCORING_MODES.get(mode, SCORING_MODES["balanced"])


def _diversify_song_tuples(
    ranked: Sequence[Tuple[float, Song, str]],
    k: int,
    artist_penalty: float,
    genre_penalty: float,
) -> List[Tuple[float, Song, str]]:
    """
    Greedy top-k with penalties for repeating artists or genres already selected.
    Returns tuples keeping the original score and explanation (penalty affects selection only).
    Final order is sorted by model score (desc) so the printed rank matches score magnitude.
    """
    if k <= 0:
        return []
    remaining = sorted(ranked, key=lambda x: x[0], reverse=True)
    picked: List[Tuple[float, Song, str]] = []
    picked_artists: set = set()
    picked_genres: set = set()

    while len(picked) < k and remaining:
        best_i = -1
        best_adj = float("-inf")
        for i, (sc, song, expl) in enumerate(remaining):
            adj = float(sc)
            art = song.artist or ""
            gen = _normalize_str(song.genre or "")
            if art in picked_artists:
                adj -= artist_penalty
            if gen in picked_genres:
                adj -= genre_penalty
            if adj > best_adj:
                best_adj = adj
                best_i = i
        choice = remaining.pop(best_i)
        sc, song, expl = choice
        picked.append((sc, song, expl))
        picked_artists.add(song.artist or "")
        picked_genres.add(_normalize_str(song.genre or ""))
    picked.sort(key=lambda x: x[0], reverse=True)
    return picked


def load_songs(csv_path: str) -> List[Dict]:
    """Load song rows from CSV; coerce numeric fields for math."""
    print(f"Loading songs from {csv_path}...")
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append(
                {
                    "id": int(row["id"]),
                    "title": row["title"],
                    "artist": row["artist"],
                    "genre": row["genre"],
                    "mood": row["mood"],
                    "energy": float(row["energy"]),
                    "tempo_bpm": float(row["tempo_bpm"]),
                    "valence": float(row["valence"]),
                    "danceability": float(row["danceability"]),
                    "acousticness": float(row["acousticness"]),
                    "popularity": int(row["popularity"]),
                    "release_decade": int(row["release_decade"]),
                    "mood_tags": row.get("mood_tags", "") or "",
                    "lyric_theme": row.get("lyric_theme", "") or "",
                    "language": row.get("language", "") or "en",
                }
            )
    return songs


def score_song(user_prefs: Dict, song: Dict, mode: str = "balanced") -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Returns total score and a list of short reason strings for transparency.
    """
    reasons: List[str] = []
    score = 0.0
    mult = _mode_or_default(mode)

    genre_key = user_prefs.get("genre") or user_prefs.get("favorite_genre")
    mood_key = user_prefs.get("mood") or user_prefs.get("favorite_mood")
    raw_energy = user_prefs.get("energy")
    if raw_energy is None:
        raw_energy = user_prefs.get("target_energy", 0.5)
    target_energy = float(raw_energy)

    if genre_key and _genre_matches(str(genre_key), str(song.get("genre", ""))):
        pts = WEIGHT_GENRE_MATCH * mult.genre
        score += pts
        reasons.append(f"genre match (+{pts:.2f})")

    if mood_key and _mood_matches(str(mood_key), str(song.get("mood", ""))):
        pts = WEIGHT_MOOD_MATCH * mult.mood
        score += pts
        reasons.append(f"mood match (+{pts:.2f})")

    energy_pts, energy_gap = _alignment_bonus(
        WEIGHT_ENERGY_ALIGNMENT * mult.energy, float(song["energy"]), target_energy
    )
    score += energy_pts
    reasons.append(
        f"energy alignment (+{energy_pts:.2f}; gap {energy_gap:.2f} from target {target_energy:.2f})"
    )

    if "target_valence" in user_prefs and user_prefs["target_valence"] is not None:
        tv = float(user_prefs["target_valence"])
        v_pts, v_gap = _alignment_bonus(
            WEIGHT_VALENCE_ALIGNMENT * mult.valence, float(song["valence"]), tv
        )
        score += v_pts
        reasons.append(f"valence alignment (+{v_pts:.2f}; gap {v_gap:.2f} from {tv:.2f})")

    if "target_danceability" in user_prefs and user_prefs["target_danceability"] is not None:
        td = float(user_prefs["target_danceability"])
        d_pts, d_gap = _alignment_bonus(
            WEIGHT_DANCEABILITY_ALIGNMENT * mult.dance, float(song["danceability"]), td
        )
        score += d_pts
        reasons.append(
            f"danceability alignment (+{d_pts:.2f}; gap {d_gap:.2f} from {td:.2f})"
        )

    likes_acoustic = user_prefs.get("likes_acoustic")
    if likes_acoustic is not None:
        ac = float(song["acousticness"])
        w = WEIGHT_ACOUSTIC_PREFERENCE * mult.acoustic
        if likes_acoustic:
            a_pts = w * ac
            reasons.append(f"prefers acoustic (+{a_pts:.2f})")
        else:
            a_pts = w * (1.0 - ac)
            reasons.append(f"prefers produced/electric (+{a_pts:.2f})")
        score += a_pts

    adv = mult.advanced
    if adv != 0.0:
        # Popularity alignment when user gives a 0–100 target.
        if user_prefs.get("target_popularity") is not None:
            tp = float(user_prefs["target_popularity"])
            sp = float(song["popularity"])
            p_pts, p_gap = _alignment_bonus(
                WEIGHT_POPULARITY_ALIGNMENT * adv, sp / 100.0, tp / 100.0
            )
            score += p_pts
            reasons.append(
                f"popularity fit (+{p_pts:.2f}; song {int(sp)} vs target {int(tp)})"
            )

        # Era fit: closer release decade clusters score higher.
        if user_prefs.get("target_decade") is not None:
            steps = _decade_steps(int(song["release_decade"]), int(user_prefs["target_decade"]))
            decade_frac = min(steps / 4.0, 1.0)  # 4+ decade gaps bottom out
            dec_pts = WEIGHT_DECADE_PROXIMITY * adv * (1.0 - decade_frac)
            score += dec_pts
            reasons.append(
                f"era fit (+{dec_pts:.2f}; decade {song['release_decade']} vs target {user_prefs['target_decade']})"
            )

        user_tag_blob = user_prefs.get("favorite_mood_tags") or user_prefs.get("mood_tags")
        if user_tag_blob:
            user_tags = set(_parse_tags(str(user_tag_blob)))
            song_tags = set(_parse_tags(str(song.get("mood_tags", ""))))
            overlap = user_tags & song_tags
            if overlap:
                tag_pts = min(
                    MAX_MOOD_TAG_BONUS * adv,
                    len(overlap) * WEIGHT_MOOD_TAG_MATCH * adv,
                )
                score += tag_pts
                reasons.append(
                    f"mood tags overlap {sorted(overlap)!r} (+{tag_pts:.2f})"
                )

        lt = user_prefs.get("lyric_theme")
        if lt and _normalize_str(str(lt)) == _normalize_str(str(song.get("lyric_theme", ""))):
            ly_pts = WEIGHT_LYRIC_THEME_MATCH * adv
            score += ly_pts
            reasons.append(f"lyric theme match (+{ly_pts:.2f})")

        ulang = user_prefs.get("language")
        if ulang and _normalize_str(str(ulang)) == _normalize_str(str(song.get("language", ""))):
            lang_pts = WEIGHT_LANGUAGE_MATCH * adv
            score += lang_pts
            reasons.append(f"language match (+{lang_pts:.2f})")

    return score, reasons


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    scoring_mode: str = "balanced",
    apply_diversity: bool = True,
    artist_repeat_penalty: float = DEFAULT_ARTIST_REPEAT_PENALTY,
    genre_repeat_penalty: float = DEFAULT_GENRE_REPEAT_PENALTY,
) -> List[Tuple[Dict, float, str]]:
    """
    Score every song, sort high to low, optionally diversify, return top k.
    Each item is (song, score, joined reasons); score is the pre-diversity model score.
    """
    ranked: List[Tuple[float, Dict, str]] = []
    for s in songs:
        sc, rs = score_song(user_prefs, s, mode=scoring_mode)
        ranked.append((sc, s, "; ".join(rs)))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if apply_diversity:
        ranked = _diversify_dict_tuples(ranked, k, artist_repeat_penalty, genre_repeat_penalty)
    else:
        ranked = ranked[:k]
    return [(song, float(sc), expl) for sc, song, expl in ranked]


def _diversify_dict_tuples(
    ranked: Sequence[Tuple[float, Dict, str]],
    k: int,
    artist_penalty: float,
    genre_penalty: float,
) -> List[Tuple[float, Dict, str]]:
    if k <= 0:
        return []
    remaining = sorted(ranked, key=lambda x: x[0], reverse=True)
    picked: List[Tuple[float, Dict, str]] = []
    picked_artists: set = set()
    picked_genres: set = set()

    while len(picked) < k and remaining:
        best_i = -1
        best_adj = float("-inf")
        for i, (sc, song, expl) in enumerate(remaining):
            adj = float(sc)
            art = str(song.get("artist", ""))
            gen = _normalize_str(str(song.get("genre", "")))
            if art in picked_artists:
                adj -= artist_penalty
            if gen in picked_genres:
                adj -= genre_penalty
            if adj > best_adj:
                best_adj = adj
                best_i = i
        choice = remaining.pop(best_i)
        sc, song, expl = choice
        picked.append((sc, song, expl))
        picked_artists.add(str(song.get("artist", "")))
        picked_genres.add(_normalize_str(str(song.get("genre", ""))))
    picked.sort(key=lambda x: x[0], reverse=True)
    return picked
