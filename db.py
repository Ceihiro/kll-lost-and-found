"""
FILE: db.py
PURPOSE: All database operations for KLL Lost and Found.
         Creates the SQLite database file (kll-lost-and-found.db) the first
         time the app runs, and provides functions to add, read, and update
         items and claims. No other file should write SQL directly.

Tables:
  items  – every lost and found report
  claims – staff verification records linking a lost report to a found item

CSE 103 – Intelligent System | Kolehiyo ng Lungsod ng Lipa
"""

import sqlite3
from pathlib import Path

# Database file sits in the same folder as this script.
DB_PATH = Path(__file__).parent / "kll-lost-and-found.db"

# ── Table definitions ──────────────────────────────────────────────────────
# CREATE TABLE IF NOT EXISTS means this is safe to run every time the app
# starts — it only creates the table when it does not exist yet.
SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kind          TEXT    NOT NULL CHECK (kind IN ('lost', 'found')),
    category      TEXT    NOT NULL,
    color         TEXT,
    brand         TEXT,
    description   TEXT    NOT NULL,
    location      TEXT    NOT NULL,
    event_time    TEXT    NOT NULL,   -- ISO datetime: when it was lost or found
    contact       TEXT,               -- lost reports only: how to reach the owner
    storage_place TEXT,               -- found items only: where the item is kept
    private_detail TEXT,              -- found items only: detail staff use to verify
    status        TEXT    NOT NULL DEFAULT 'open'
                          CHECK (status IN ('open', 'returned', 'unclaimed')),
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claims (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lost_id    INTEGER NOT NULL REFERENCES items(id),
    found_id   INTEGER NOT NULL REFERENCES items(id),
    outcome    TEXT    NOT NULL CHECK (outcome IN ('Verified', 'Not Verified', 'Pending')),
    notes      TEXT,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_conn():
    """Open and return a connection to the SQLite database.
    row_factory = sqlite3.Row lets us access columns by name (row['category'])
    instead of by index (row[2]).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Run the schema SQL to create tables if they do not exist yet.
    Called once when app.py starts.
    """
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def add_item(kind, category, color, brand, description, location, event_time,
             contact=None, storage_place=None, private_detail=None):
    """Insert a new lost or found report and return its new id.

    Parameters
    ----------
    kind          : 'lost' or 'found'
    category      : item type from config.CATEGORIES
    color         : item color from config.COLORS
    brand         : optional brand name (may be empty string)
    description   : free-text description used by the NLP matching
    location      : room or area from config.LOCATIONS
    event_time    : ISO datetime string (from the HTML datetime-local input)
    contact       : lost items only – owner's email or phone
    storage_place : found items only – where the item is being kept
    private_detail: found items only – secret detail for owner verification
    """
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO items
               (kind, category, color, brand, description, location,
                event_time, contact, storage_place, private_detail)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (kind, category, color, brand, description, location,
             event_time, contact, storage_place, private_detail),
        )
        return cur.lastrowid   # return the auto-generated id


def get_item(item_id):
    """Return one item row by its id, or None if not found."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM items WHERE id = ?", (item_id,)
        ).fetchone()


def list_items(kind, status="open"):
    """Return all items of the given kind with the given status.
    Default status is 'open' — we only show items that have not been resolved.
    Results are sorted newest-first by event_time.
    """
    with get_conn() as conn:
        return conn.execute(
            """SELECT * FROM items
               WHERE kind = ? AND status = ?
               ORDER BY event_time DESC""",
            (kind, status),
        ).fetchall()


def list_all_items():
    """Return every item in the database regardless of kind or status.
    Used by the staff dashboard to show the full picture.
    Results are sorted newest-first by created_at timestamp.
    """
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM items ORDER BY created_at DESC"
        ).fetchall()


def list_claims(limit=30):
    """Return the most recent claim records with the linked item details.

    Joins the claims table with the items table twice (once for lost,
    once for found) so the dashboard can show readable item info
    without a second query per row.

    limit: maximum number of rows to return (default 30).
    """
    with get_conn() as conn:
        return conn.execute(
            """SELECT
                   c.id,
                   c.outcome,
                   c.notes,
                   c.created_at,
                   l.category  AS lost_category,
                   l.color     AS lost_color,
                   l.description AS lost_desc,
                   f.category  AS found_category,
                   f.color     AS found_color,
                   f.description AS found_desc,
                   c.lost_id,
                   c.found_id
               FROM claims c
               JOIN items l ON l.id = c.lost_id
               JOIN items f ON f.id = c.found_id
               ORDER BY c.created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()


def count_items():
    """Return a summary dict of item counts by status.
    Used to display the quick-stats bar at the top of the dashboard.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT kind, status, COUNT(*) AS n
               FROM items
               GROUP BY kind, status"""
        ).fetchall()

    # Build a nested dict: counts[kind][status] = n
    counts = {
        "lost":  {"open": 0, "returned": 0, "unclaimed": 0},
        "found": {"open": 0, "returned": 0, "unclaimed": 0},
    }
    for row in rows:
        counts[row["kind"]][row["status"]] = row["n"]
    return counts


def get_chart_data():
    """Return aggregated counts for Chart.js visualizations on the dashboard.

    Returns a dict with:
      categories : list of [category_name, count] — items by category type
      locations  : list of [location_name, count] — most common loss locations
      statuses   : dict {status: count}            — open / returned / unclaimed split
    """
    with get_conn() as conn:
        categories = conn.execute(
            """SELECT category, COUNT(*) AS n
               FROM items GROUP BY category ORDER BY n DESC"""
        ).fetchall()
        locations = conn.execute(
            """SELECT location, COUNT(*) AS n
               FROM items WHERE kind = 'lost'
               GROUP BY location ORDER BY n DESC LIMIT 8"""
        ).fetchall()
        statuses = conn.execute(
            """SELECT status, COUNT(*) AS n FROM items GROUP BY status"""
        ).fetchall()
    return {
        "categories": [[r["category"], r["n"]] for r in categories],
        "locations":  [[r["location"],  r["n"]] for r in locations],
        "statuses":   {r["status"]: r["n"] for r in statuses},
    }


def compute_feedback_weights():
    """Analyze all 'Verified' claims and suggest refined attribute weights.

    How it works (Section 6.8 of the proposal):
    - For each verified claim, compare the lost and found item attribute-by-attribute.
    - Count how many times each attribute actually matched in confirmed true pairs.
    - Convert match rates into normalized weights (summing to 1.0).
    - Attributes that match more often in verified claims get higher suggested weights.

    Returns
    -------
    dict  – suggested weights {category, color, brand, location, time} summing to 1.0
    None  – if fewer than 3 verified claims exist (not enough data to learn from)
    """
    with get_conn() as conn:
        verified = conn.execute(
            """SELECT l.category AS l_cat, l.color AS l_col, l.brand AS l_brand,
                      l.location AS l_loc, l.event_time AS l_time,
                      f.category AS f_cat, f.color AS f_col, f.brand AS f_brand,
                      f.location AS f_loc, f.event_time AS f_time
               FROM claims c
               JOIN items l ON l.id = c.lost_id
               JOIN items f ON f.id = c.found_id
               WHERE c.outcome = 'Verified'"""
        ).fetchall()

    if len(verified) < 3:
        return None   # need at least 3 verified claims to compute meaningful rates

    hits   = {"category": 0, "color": 0, "brand": 0, "location": 0, "time": 0}
    totals = {"category": 0, "color": 0, "brand": 0, "location": 0, "time": 0}

    def _norm(v):
        return (v or "").strip().lower()

    for r in verified:
        # Category
        if _norm(r["l_cat"]) and _norm(r["f_cat"]):
            totals["category"] += 1
            if _norm(r["l_cat"]) == _norm(r["f_cat"]):
                hits["category"] += 1
        # Color
        if _norm(r["l_col"]) and _norm(r["f_col"]):
            totals["color"] += 1
            if _norm(r["l_col"]) == _norm(r["f_col"]):
                hits["color"] += 1
        # Brand
        if _norm(r["l_brand"]) and _norm(r["f_brand"]):
            totals["brand"] += 1
            if _norm(r["l_brand"]) == _norm(r["f_brand"]):
                hits["brand"] += 1
        # Location
        if _norm(r["l_loc"]) and _norm(r["f_loc"]):
            totals["location"] += 1
            if _norm(r["l_loc"]) == _norm(r["f_loc"]):
                hits["location"] += 1
        # Time window
        try:
            from datetime import datetime
            import config as _cfg
            a = datetime.fromisoformat(r["l_time"])
            b = datetime.fromisoformat(r["f_time"])
            hours = abs((a - b).total_seconds()) / 3600
            totals["time"] += 1
            if hours <= _cfg.TIME_WINDOW_HOURS:
                hits["time"] += 1
        except (TypeError, ValueError):
            pass

    # Compute match rate per attribute (0.0 – 1.0).
    rates = {k: (hits[k] / totals[k]) if totals[k] > 0 else 0.5 for k in hits}

    # Normalize so all suggested weights sum to 1.0.
    total = sum(rates.values())
    if total == 0:
        return None
    return {k: round(v / total, 3) for k, v in rates.items()}


def list_overdue_items(days=30):
    """Return open found items that have been sitting for more than `days` days.
    These are candidates for 'unclaimed' status — the staff dashboard highlights
    them as a reminder to follow up or dispose of the item.

    Uses SQLite's julianday() to calculate the difference between now and
    the event_time (when the item was found).
    """
    with get_conn() as conn:
        return conn.execute(
            """SELECT *
               FROM items
               WHERE kind = 'found'
                 AND status = 'open'
                 AND (julianday('now') - julianday(event_time)) >= ?
               ORDER BY event_time ASC""",
            (days,),
        ).fetchall()


def update_item_status(item_id, status):
    """Change the status of one item.
    Valid values: 'open', 'returned', 'unclaimed'.
    Used by staff to manually mark a found item as unclaimed after
    a long period, or to re-open a mistakenly closed item.
    """
    with get_conn() as conn:
        conn.execute(
            "UPDATE items SET status = ? WHERE id = ?",
            (status, item_id),
        )


def record_claim(lost_id, found_id, outcome, notes=""):
    """Save a staff verification result in the claims table.

    If the outcome is 'Verified', both the lost and found item are marked
    as 'returned' so they no longer appear in the open lists.
    """
    with get_conn() as conn:
        # Always insert a claim record, regardless of outcome.
        conn.execute(
            """INSERT INTO claims (lost_id, found_id, outcome, notes)
               VALUES (?, ?, ?, ?)""",
            (lost_id, found_id, outcome, notes),
        )
        # Only close both items when ownership is confirmed.
        if outcome == "Verified":
            conn.execute(
                "UPDATE items SET status = 'returned' WHERE id IN (?, ?)",
                (lost_id, found_id),
            )
