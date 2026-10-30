"""
FILE: config.py
PURPOSE: Central settings file for KLL Lost and Found.
         Teammates edit this file to change categories, locations, colors,
         and the weights used by the matching engine. Do not hard-code
         these values inside other files.

CSE 103 – Intelligent System | Kolehiyo ng Lungsod ng Lipa
"""

# ── Item categories shown in the dropdown forms ───────────────────────────
# Add or remove entries here to match what is commonly lost on campus.
CATEGORIES = [
    "Umbrella", "Water bottle", "Flash drive", "Charger", "Calculator",
    "ID / Card", "Bag", "Notebook / Book", "Keys", "Other",
]

# ── Colors shown in the dropdown forms ────────────────────────────────────
COLORS = [
    "Black", "White", "Gray", "Blue", "Red", "Green",
    "Yellow", "Brown", "Pink", "Purple", "Orange", "Other",
]

# ── Campus locations (rooms / areas) ──────────────────────────────────────
# Edit this list to match the actual rooms in KLL.
LOCATIONS = [
    "Lab 1", "Lab 2", "Lab 3", "Room 101", "Room 102", "Room 201",
    "Room 202", "Hallway", "Faculty room", "Other",
]

# ── Attribute score weights ────────────────────────────────────────────────
# Each key matches an attribute compared between a lost and a found item.
# All values must add up to 1.0.
# Higher weight = that attribute matters more in the final score.
#
# DESIGN DECISION (Oct 31): Location and time carry the most combined weight
# (0.20 + 0.25 = 0.45) because for generic items like "white calculator",
# the description text alone cannot distinguish two identical items.
# Location and date of report are the ONLY reliable differentiators in that case.
# Example: two "white calculator" reports → the one whose location and
# reported time matches the found item most closely wins.
ATTRIBUTE_WEIGHTS = {
    "category": 0.30,   # most important — a bag is very different from a calculator
    "color":    0.20,   # second most important visual clue
    "brand":    0.05,   # useful but often left blank by students
    "location": 0.20,   # WHERE it was lost vs. found — key tiebreaker for generic items
    "time":     0.25,   # WHEN it was lost — strongest tiebreaker for identical descriptions
}

# ── Score mixing ───────────────────────────────────────────────────────────
# Final score = ATTRIBUTE_SHARE × attribute_score + TEXT_SHARE × text_score
# Setting one to 1.0 and the other to 0.0 lets evaluate.py compare methods.
ATTRIBUTE_SHARE = 0.5   # 50 % rule-based
TEXT_SHARE      = 0.5   # 50 % NLP (TF-IDF cosine similarity)

# ── Time window ────────────────────────────────────────────────────────────
# A found item reported more than this many hours after the lost time
# receives a time score of 0. Items within the window are scored 0–1.
TIME_WINDOW_HOURS = 72  # 3 days

# ── Display limit ─────────────────────────────────────────────────────────
# How many top matches to show per lost report.
TOP_N = 3
