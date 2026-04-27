# Model card: Mixtape Scorer (classroom sim)

## 1. Model name

**Mixtape Scorer** — a deterministic, content-based song ranker for a toy catalog.

## 2. Intended use

- **What it does:** Given a tiny CSV of songs and a short list of preferences (genre, mood, target energy, acoustic vs produced), it scores every song with fixed rules and prints the top K with explanations.  
- **Who it is for:** Students and anyone learning how “recommendations” can mean little more than weighted arithmetic on metadata.  
- **What it is not:** A production recommender. It does not personalize from listening history, does not model fairness across groups, and should not be used to make real business or editorial decisions.

## 3. How the model works

Each song is described by genre, mood, several 0–1 audio-ish features (energy, valence, danceability, acousticness), tempo, plus extra columns used in the stretch build: popularity (0–100), release decade, pipe-separated mood tags, a coarse lyric theme, and language. The user passes the usual genre/mood/energy/acoustic prefs and can add optional targets (e.g. target popularity, decade, favorite mood tags, lyric theme, language) so those fields contribute. The scorer adds points when genre or mood lines up, when energy is close to the target, and for acoustic vs produced taste. Optional valence/danceability in the prefs dict use the same “closer is better” idea.

There are also **scoring modes** (`balanced`, `genre_first`, `mood_first`, `energy_focused`) that scale how much each signal weighs—same rules, different emphasis. After scoring, an optional **diversity** step fills the top K greedily while penalizing repeat artists and repeat genres so one label does not dominate the shortlist.

There is no training step; changing behavior means changing weights, mode, or the CSV.

## 4. Data

- **Size:** 18 fictional rows in `data/songs.csv` (10 starter tracks + 8 added for variety).  
- **Columns:** Original audio-ish fields plus popularity, release decade, mood tags, lyric theme, and language for the extended scorer.  
- **Limit:** Everything is synthetic; it still skips real-world mess (real charts, rights, listening logs, lyrics NLP, demographics). Explicit lyrics and “true” regional charts are not modeled.

## 5. Strengths

- **Glass box:** Every point has a printed reason, which is rare in large production systems but great for a classroom.  
- **Sensible defaults for the cliché “happy pop gym” profile:** High energy + happy tends to bubble up danceable, produced pop before ambient classical—matches everyday intuition.  
- **Cheap to run:** No API keys, no GPU jobs—helpful when the learning goal is the *idea* of scoring, not scaling.

## 6. Limitations and bias

The scorer can build a **filter bubble** because genre carries the largest discrete bonus and the dataset is small. A user who only states “pop” may never see the Latin or hip-hop row even if mood and energy fit, simply because those two points for genre are doing a lot of work. Energy closeness helps, but it cannot invent diversity that is not already in the spreadsheet. During testing, the “high-energy pop” profile kept **Gym Hero** and **Sunrise City** near the top—not because the code is “wrong,” but because both sit in the pop/indie-pop cluster with upbeat valence and production that matches someone who dislikes acoustic mixes. If 40% of the CSV were pop, a naive deployment would *look* smart while mostly recycling the same bucket.

## 7. Evaluation

I ran four preference sketches in `src/main.py`: upbeat pop, chill lofi, intense rock, and a deliberately contradictory “moody + nearly max energy” profile. For each, I read the top five lines and checked whether the winners matched the stated knobs. The adversarial profile behaved as a gut-check: mood still fired on **Night Drive Loop**, but pure energy + genre matches from **Gym Hero** took first, which shows how conflicting preferences turn into trade-offs instead of magic.  

I also ran a **weight experiment** (see README): halving genre weight and doubling the energy cap moved who won second place even when the winner stayed pop, which matched my expectation that the list is sensitive to constants.

Automated checks: `pytest` covers that the OOP `Recommender` ranks the seeded pop/happy track above the lofi row and that explanations are non-empty strings.

## 8. Future work

- Stronger **fairness / exposure** metrics (not just artist/genre diversity in top K).  
- **Soft genre blends** or multi-label genres instead of one string plus substring hacks.  
- A tiny **collaborative** stub (two fake user histories) to contrast with the pure content score.  
- Richer **evaluation** (held-out prefs, human ratings) beyond eyeballing tables.

## 9. Personal reflection

The part that stuck with me is how quickly a simple score can *feel* like taste, even when it is only four or five numbers. I did not need neural nets to see “personalization”; I needed clear features and weights. The catch is that those weights are hidden product decisions in real apps—here they are just Python constants, which is both empowering and a little alarming.

Using autocomplete-style tools sped up boilerplate (CSV typing, sorting snippets) but I still had to decide what counted as a “genre match” and whether substring matching was fair. The tools could not tell me whether +2 for genre was ethical, only convenient. If I extended this, I would graph catalog balance before touching the algorithm again, because fixing skewed data beats tweaking softmax every time.
