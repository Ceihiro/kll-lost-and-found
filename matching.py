"""
FILE: matching.py
PURPOSE: The AI matching engine for KLL Lost and Found.
         Scores how likely a found item matches a lost report using two methods:

         1. Attribute score  (rule-based, weighted)
            Compares category, color, brand, location, and time.
            Each attribute that matches adds to the score.
            Missing attributes are skipped and the remaining weights rescaled,
            so a blank brand does not unfairly lower the result.

         2. Text score  (NLP – TF-IDF + cosine similarity)
            Converts each item's text fields into a TF-IDF vector and
            measures how similar the lost description is to each found item.
            Uses scikit-learn (the "AI" / NLP part of the system).

         Final score = 50 % attribute score + 50 % text score (configurable).

         Feedback learning (Section 6.8 of the proposal):
            If staff have verified enough claims, the system saves learned weights
            to learned_weights.json. attribute_score() will automatically use those
            instead of the defaults in config.py, refining scoring over time.

CSE 103 – Intelligent System | Kolehiyo ng Lungsod ng Lipa
"""

import json
from datetime import datetime
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config

# Path to the optional learned weights file (created by /staff/apply_weights).
_LEARNED_WEIGHTS_FILE = Path(__file__).parent / "learned_weights.json"


def _load_weights():
    """Return the attribute weights to use for scoring.

    If staff have applied feedback weights (via the dashboard), loads them from
    learned_weights.json.  Otherwise falls back to the defaults in config.py.
    This implements the feedback-based weight refinement from proposal Section 6.8.
    """
    if _LEARNED_WEIGHTS_FILE.exists():
        try:
            with open(_LEARNED_WEIGHTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass   # if the file is broken, fall back silently
    return dict(config.ATTRIBUTE_WEIGHTS)


# ── Tagalog / Taglish synonym map ─────────────────────────────────────────
# Maps Filipino words to their English equivalents so TF-IDF can match them.
# Example: a lost report says "payong", found report says "umbrella" →
#   without this map: cosine similarity = 0 (no shared words)
#   with this map:    both become "umbrella" → similarity = high
#
# Add more entries here whenever you notice recurring Tagalog terms
# in real student reports.
_TAGALOG_SYNONYMS = {
    # ── Items (Tagalog → English) ────────────────────────────────────────
    "payong":        "umbrella",
    "payung":        "umbrella",
    "umbrelya":      "umbrella",       # Filipino pronunciation
    "awtomatik":     "automatic",
    "susi":          "keys",
    "bote":          "bottle water bottle",
    "kwaderno":      "notebook",
    "kuwaderno":     "notebook",
    "libro":         "book notebook",
    "kalkulator":    "calculator",
    "kalkuleytor":   "calculator",
    "kalkuletor":    "calculator",
    "scical":        "scientific calculator",  # common student shorthand
    "calcu":         "calculator",             # very common shorthand
    "mochila":       "bag backpack",
    "pitaka":        "wallet",
    "relo":          "watch",
    "sinturon":      "belt",
    # ── Common Taglish item nicknames ────────────────────────────────────
    "tumbler":       "water bottle",   # very common Taglish / brand-as-noun
    "aquaflask":     "water bottle",   # popular local brand used as category
    "hydroflask":    "water bottle",
    "hydro flask":   "water bottle",
    "charjer":       "charger",        # common typo/mispronunciation
    "charger":       "charger",
    "flasdraib":     "flash drive",
    "flas draib":    "flash drive",
    "sandisk":       "flash drive",    # brand often used instead of category
    "usb":           "flash drive",
    "computor":      "computer",
    # ── Local / Filipino brands used as item names ────────────────────────
    "bavin":         "charger",        # popular local phone charger brand
    "romoss":        "charger powerbank",
    "baseus":        "charger powerbank",
    "fibrella":      "umbrella",       # popular local umbrella brand
    "giraffe":       "umbrella",
    "jansport":      "bag backpack",
    "hawk":          "bag backpack",
    "cattleya":      "notebook binder",
    "kingston":      "flash drive",
    # ── Colors (Filipino → English) ──────────────────────────────────────
    "pula":          "red",
    "berde":         "green",
    "itim":          "black",
    "puti":          "white",
    "asul":          "blue",
    "dilaw":         "yellow",
    "abo":           "gray",
    "kulay abo":     "gray",
    "kulay puti":    "white",
    "kulay itim":    "black",
    "kulay asul":    "blue",
    "kulay pula":    "red",
    "rosas":         "pink",
    "lila":          "purple",
    "kahel":         "orange",
    "kayumanggi":    "brown",
    # ── Descriptors: condition and appearance ────────────────────────────
    "may sticker":   "sticker",        # "may" = "has/with"
    "may sulat":     "label written",
    "may pangalan":  "name label",
    "may nakalagay": "label",
    "may tahi":      "sewn stitched",
    "may tape":      "tape wrapped",
    "may dent":      "dent dented",
    "may keychain":  "keychain",
    "may cover":     "cover case",
    "may remote":    "remote",
    "nabasag":       "broken cracked",
    "sira":          "broken damaged",
    "luma":          "old",
    "bago":          "new",
    "maliit":        "small",
    "malaki":        "large big",
    "bilog":         "round",
    "mahabang":      "long",
    "mahaba":        "long",
    "malalim":       "deep",
    "transparent":   "clear transparent",
    "awtomatik":     "automatic",
    # ── Location filler words (normalize room names) ─────────────────────
    "sa lab":        "lab",
    "sa room":       "room",
    "sa hallway":    "hallway",
    "sa mesa":       "table desk",
    "sa upuan":      "chair seat",
    "sa floor":      "floor",
    "sa loob":       "inside",
    "sa gilid":      "side",
    "sa taas":       "top upper",
    "sa dulo":       "end tip",
    "sa likod":      "back behind",
    "sa sulok":      "corner",
}

# ── Filipino + English stop words ─────────────────────────────────────────
# These common words carry no useful meaning for matching and should be
# removed before TF-IDF vectorization.
# Filipino stop words: ko, sa, yung, ang, etc.
# English stop words: the, a, in, found, lost, etc.
_STOP_WORDS = {
    # Filipino filler / connective words
    "ko", "sa", "yung", "ang", "mga", "na", "ng", "at", "ay", "si",
    "ni", "ka", "mo", "niya", "namin", "nila", "kami", "kayo", "sila",
    "ito", "iyan", "iyon", "doon", "dito", "diyan", "para", "kung",
    "nang", "lang", "lamang", "po", "opo", "ho", "nga", "eh", "ba",
    "raw", "daw", "kasi", "pero", "o", "naman", "muna", "pala",
    "talaga", "din", "rin", "yata", "siguro", "halos", "lahat",
    "wala", "walang", "mayroon", "may", "noon", "ngayon", "kanina",
    "akala", "sana", "kaya", "pati", "habang", "hanggang",
    # Action words used in reports (normalize these away)
    "nakita", "napulot", "nawala", "naiwan", "nalaglag", "nahulog",
    "naiwanan", "nakalimutan", "nakalipad", "nawawala",
    "pagkatapos", "malapit", "ilalim", "labas", "loob", "taas",
    "kaninang", "kaninang", "umaga", "hapon", "gabi",
    # English filler in lost/found descriptions
    "the", "a", "an", "in", "on", "at", "to", "of", "it", "is",
    "was", "my", "i", "and", "or", "with", "found", "lost", "left",
    "inside", "room", "near", "beside", "under", "around", "one",
    "item", "thing", "stuff", "something", "just", "got", "have",
    "area", "corner", "floor", "table", "chair", "desk",
}


def _normalize(text):
    """Clean and normalize a text string before TF-IDF vectorization.

    Steps:
    1. Lowercase everything.
    2. Replace Tagalog / Taglish synonyms with English equivalents.
       e.g. "payong" → "umbrella", "tumbler" → "water bottle", "calcu" → "calculator"
       Uses word-boundary matching so "calculator" does not re-match inside itself.
    3. Remove Filipino and English stop words (common words with no matching value).
       e.g. "nakita ko sa lab 2" → "lab 2"
    4. Strip extra whitespace.

    This is what allows TF-IDF to match descriptions written in different
    languages or with slightly different wording, including messy real-world
    Taglish student reports.
    """
    import re
    text = (text or "").lower()

    # Apply synonym replacements using word-boundary regex to avoid partial matches.
    # Multi-word keys (e.g. "may sticker") are applied first by sorting longest first.
    for tagalog, english in sorted(_TAGALOG_SYNONYMS.items(), key=lambda x: -len(x[0])):
        # Use \b word boundary for single-word keys; plain replace for multi-word keys.
        if " " in tagalog:
            text = text.replace(tagalog, english)
        else:
            text = re.sub(r'\b' + re.escape(tagalog) + r'\b', english, text)

    # Remove stop words token-by-token.
    tokens = [w for w in text.split() if w not in _STOP_WORDS and len(w) > 1]
    return " ".join(tokens)


# ── Small helpers ──────────────────────────────────────────────────────────

def _norm(value):
    """Lowercase and strip whitespace so comparisons are case-insensitive."""
    return (value or "").strip().lower()


def _hours_apart(time_a, time_b):
    """Return the absolute difference in hours between two ISO datetime strings.
    Returns None if either string is missing or invalid.
    """
    try:
        a = datetime.fromisoformat(time_a)
        b = datetime.fromisoformat(time_b)
    except (TypeError, ValueError):
        return None
    return abs((a - b).total_seconds()) / 3600


# ── Rule-based attribute score ─────────────────────────────────────────────

def attribute_score(lost, found):
    """Compare a lost item to a found item using simple rules.

    Returns
    -------
    score   : float 0.0 – 1.0
    reasons : list of human-readable strings explaining what matched

    How it works
    ------------
    For each attribute (category, color, brand, location, time):
      - If both sides have a value, compare them and give 1.0 (match) or 0.0 (no match).
      - If either side is blank, skip that attribute entirely.
    After collecting the scores, we divide by the sum of the weights of only
    the attributes we actually compared (weight rescaling).
    This means a blank brand never hurts the score.
    """
    # Use learned weights if available, otherwise use config defaults.
    weights = _load_weights()
    parts   = {}     # attribute name → score (0.0 or 1.0)
    reasons = []     # human-readable match reasons

    # ── Category ──────────────────────────────────────────────────────────
    if _norm(lost["category"]) and _norm(found["category"]):
        same = _norm(lost["category"]) == _norm(found["category"])
        parts["category"] = 1.0 if same else 0.0
        if same:
            reasons.append(f"Same category: {found['category']}")

    # ── Color ─────────────────────────────────────────────────────────────
    if _norm(lost["color"]) and _norm(found["color"]):
        same = _norm(lost["color"]) == _norm(found["color"])
        parts["color"] = 1.0 if same else 0.0
        if same:
            reasons.append(f"Same color: {found['color']}")

    # ── Brand ─────────────────────────────────────────────────────────────
    if _norm(lost["brand"]) and _norm(found["brand"]):
        same = _norm(lost["brand"]) == _norm(found["brand"])
        parts["brand"] = 1.0 if same else 0.0
        if same:
            reasons.append(f"Same brand: {found['brand']}")

    # ── Location ──────────────────────────────────────────────────────────
    if _norm(lost["location"]) and _norm(found["location"]):
        same = _norm(lost["location"]) == _norm(found["location"])
        parts["location"] = 1.0 if same else 0.0
        if same:
            reasons.append(f"Same location: {found['location']}")

    # ── Time ──────────────────────────────────────────────────────────────
    # Score decays linearly from 1.0 (same time) to 0.0 (at TIME_WINDOW_HOURS).
    hours = _hours_apart(lost["event_time"], found["event_time"])
    if hours is not None:
        parts["time"] = max(0.0, 1.0 - hours / config.TIME_WINDOW_HOURS)
        if hours <= config.TIME_WINDOW_HOURS:
            reasons.append(f"Found within {hours:.0f} hour(s) of the lost time")

    # ── Rescale and combine ────────────────────────────────────────────────
    # Only count the weight of attributes we actually compared.
    used_weight = sum(weights[k] for k in parts)
    if used_weight == 0:
        return 0.0, reasons   # no attributes could be compared
    score = sum(weights[k] * v for k, v in parts.items()) / used_weight
    return score, reasons


# ── NLP text score ─────────────────────────────────────────────────────────

def _doc(item):
    """Combine an item's text fields into one string for TF-IDF vectorization,
    with Tagalog/Taglish normalization applied.

    We include category, color, brand, and description so the NLP part
    can pick up keywords from all fields.

    Calling _normalize() here is the key step that enables Taglish matching:
      - Tagalog words are translated to English equivalents
      - Common Filipino/English filler words (stop words) are removed
      - This means "payong" and "umbrella" both become "umbrella" →
        TF-IDF will now see them as the same word → high similarity score

    Without _normalize(), a report saying "payong" and one saying "umbrella"
    would have 0 shared vocabulary → cosine similarity = 0.0 (no match).
    With _normalize(), both map to "umbrella" → similarity = high.
    """
    raw = " ".join([
        item["category"]    or "",
        item["color"]       or "",
        item["brand"]       or "",
        item["description"] or "",
    ])
    # _normalize() does: lowercase → synonym replacement → stop word removal
    return _normalize(raw)


def text_scores(lost, found_items):
    """Compute TF-IDF cosine similarity between the lost item and every found item.

    How it works
    ------------
    1. Build a list of documents: first the lost item, then all found items.
    2. TfidfVectorizer converts each document into a numeric vector where each
       word's weight reflects how important it is (common words like 'the' get
       low weight; specific words like 'Casio' get high weight).
    3. Cosine similarity measures the angle between two vectors.
       1.0 = identical direction (same words), 0.0 = no shared words.

    Returns a list of floats the same length as found_items.
    """
    if not found_items:
        return []

    # First document is the lost item; the rest are found items.
    docs = [_doc(lost)] + [_doc(f) for f in found_items]

    try:
        matrix = TfidfVectorizer().fit_transform(docs)
    except ValueError:
        # ValueError happens when all descriptions are blank (empty vocabulary).
        return [0.0] * len(found_items)

    # Compare the first row (lost item) against all other rows (found items).
    return list(cosine_similarity(matrix[0], matrix[1:])[0])


# ── Main ranking function ──────────────────────────────────────────────────

def rank_matches(lost, found_items, top_n=None,
                 attribute_share=None, text_share=None):
    """Score and rank all found items for one lost report.

    Parameters
    ----------
    lost            : dict-like row from the items table
    found_items     : list of dict-like rows from the items table
    top_n           : how many results to return (default: config.TOP_N)
    attribute_share : override the attribute weight (used by evaluate.py)
    text_share      : override the text weight    (used by evaluate.py)

    Returns
    -------
    List of dicts, sorted best-first, each containing:
      'found'           – the found item row
      'attribute_score' – rule-based score 0–1
      'text_score'      – NLP score 0–1
      'final_score'     – weighted combination 0–1
      'reasons'         – list of strings explaining why it matched
    """
    top_n   = top_n   or config.TOP_N
    a_share = config.ATTRIBUTE_SHARE if attribute_share is None else attribute_share
    t_share = config.TEXT_SHARE      if text_share      is None else text_share

    # Compute NLP scores for all found items in one batch (more efficient).
    texts   = text_scores(lost, found_items)
    results = []

    for found, t_score in zip(found_items, texts):
        a_score, reasons = attribute_score(lost, found)

        # Mix the two scores using the configured shares.
        final = a_share * a_score + t_share * t_score

        # Add a reason line for the text score if it contributed anything.
        if t_score > 0:
            reasons.append(f"Description similarity: {t_score:.0%}")

        results.append({
            "found":           found,
            "attribute_score": a_score,
            "text_score":      t_score,
            "final_score":     final,
            "reasons":         reasons,
        })

    # Sort best match first and return only the top N.
    results.sort(key=lambda r: r["final_score"], reverse=True)
    return results[:top_n]
