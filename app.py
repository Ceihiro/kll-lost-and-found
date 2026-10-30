"""
FILE: app.py
PURPOSE: Main Flask web application for KLL Lost and Found.
         Defines all the URL routes (pages) the browser can visit,
         reads form data, calls db.py to save/load records,
         and calls matching.py to rank found items.

Routes:
  /                   – Home: shows all open lost and found items
  /lost               – Form: report a lost item
  /found              – Form: log a found item (any student/staff can use this)
  /matches/<lost_id>  – Results: ranked found items for one lost report
  /staff/login        – Staff login page
  /staff/logout       – Clears the staff session
  /claim              – Staff only: record a verification outcome

Security:
  - SECRET_KEY and staff credentials are loaded from the .env file (never committed).
  - Every POST form is protected by a CSRF token (Flask-WTF).
  - The /claim route requires staff login (enforced by @staff_required).

CSE 103 – Intelligent System | Kolehiyo ng Lungsod ng Lipa
"""

import csv
import io
import json
import os
from datetime import datetime
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv    # reads .env file into os.environ
from flask import (Flask, flash, redirect, render_template,
                   request, session, url_for, Response)
from flask_wtf.csrf import CSRFProtect   # automatically blocks forged form submissions

import config
import db
import matching

# ── Load secrets from .env before anything else ────────────────────────────
load_dotenv()

# ── Create the Flask app ───────────────────────────────────────────────────
app = Flask(__name__)

# SECRET_KEY is required by Flask for session cookies and CSRF tokens.
# It must be kept secret and must not be the same across different deployments.
app.secret_key = os.environ.get("SECRET_KEY", "fallback-dev-key-change-me")

# Attach CSRF protection to the app.
# After this, every POST request must include a valid csrf_token field.
csrf = CSRFProtect(app)

# Create the database tables if they do not exist yet.
db.init_db()


# ── Staff auth decorator ───────────────────────────────────────────────────

def staff_required(f):
    """Route decorator that redirects to the login page if the user is not
    logged in as staff. Usage: add @staff_required before a route function.
    """
    @wraps(f)   # keeps the original function name for Flask's routing
    def decorated(*args, **kwargs):
        if not session.get("staff"):
            flash("Staff login required.")
            return redirect(url_for("staff_login"))
        return f(*args, **kwargs)
    return decorated


# ── Shared helper functions ────────────────────────────────────────────────

def _form_item(kind):
    """Read the common item fields from a submitted HTML form and return
    them as a dict that can be passed directly to db.add_item().
    'kind' is either 'lost' or 'found'.
    """
    f = request.form
    category = f.get("category", "").strip()
    if category == "Other":
        cat_other = f.get("category_other", "").strip()
        if cat_other:
            category = f"Other ({cat_other})"

    color = f.get("color", "").strip()
    if color == "Other":
        col_other = f.get("color_other", "").strip()
        if col_other:
            color = f"Other ({col_other})"

    location = f.get("location", "").strip()
    if location == "Other":
        loc_other = f.get("location_other", "").strip()
        if loc_other:
            location = f"Other ({loc_other})"

    return dict(
        kind=kind,
        category=category,
        color=color,
        brand=   f.get("brand",       "").strip(),
        description=f.get("description", "").strip()[:500],
        location=location,
        event_time=f.get("event_time","").strip(),
    )


def _validate_time(event_time):
    """Return True if event_time is a valid ISO datetime string (e.g. 2026-10-30T14:30),
    or False if it is blank or in a wrong format.
    """
    try:
        datetime.fromisoformat(event_time)
        return True
    except (TypeError, ValueError):
        return False


# ── Public routes ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Home page – shows all open lost reports and all open found items."""
    return render_template(
        "index.html",
        lost_items=db.list_items("lost"),
        found_items=db.list_items("found"),
    )


@app.route("/lost", methods=["GET", "POST"])
def report_lost():
    """GET  → show the 'Report a lost item' form.
    POST → validate the form, save the lost item, redirect to the matches page.
    """
    now = datetime.now().strftime("%Y-%m-%dT%H:%M")   # pre-fill the date/time field

    if request.method == "POST":
        data = _form_item("lost")

        # Read student identity fields
        reporter_name    = request.form.get("reporter_name", "").strip()
        reporter_id      = request.form.get("reporter_id", "").strip()
        reporter_section = request.form.get("reporter_section", "").strip()

        if reporter_name:
            contact = f"{reporter_name} | ID: {reporter_id} | {reporter_section}"
        else:
            contact = request.form.get("contact", "").strip()

        # Basic validation before saving to the database.
        if not data["description"] or not data["event_time"]:
            flash("Please fill in the description and the date/time.")
        elif not _validate_time(data["event_time"]):
            flash("Invalid date/time — please use the date picker.")
        else:
            lost_id = db.add_item(
                **data,
                contact=contact
            )
            # After saving, immediately show the matching results.
            return redirect(url_for("matches", lost_id=lost_id))

    return render_template("lost.html", cfg=config, now=now)


@app.route("/found", methods=["GET", "POST"])
def log_found():
    """GET  → show the 'Log a found item' form.
    POST → validate, save the found item, redirect home.
    """
    now = datetime.now().strftime("%Y-%m-%dT%H:%M")

    if request.method == "POST":
        data = _form_item("found")

        if not data["description"] or not data["event_time"]:
            flash("Please fill in the description and the date/time.")
        elif not _validate_time(data["event_time"]):
            flash("Invalid date/time — please use the date picker.")
        else:
            db.add_item(
                **data,
                storage_place= request.form.get("storage_place",  "").strip(),
                private_detail=request.form.get("private_detail", "").strip(),
            )
            flash("Found item saved.")
            return redirect(url_for("index"))

    return render_template("found.html", cfg=config, now=now)


@app.route("/matches/<int:lost_id>")
def matches(lost_id):
    """Show the top matching found items for a given lost report.
    The matching engine in matching.py scores and ranks the results.
    """
    lost = db.get_item(lost_id)

    # Guard: make sure the id exists and is actually a lost item.
    if lost is None or lost["kind"] != "lost":
        flash("Lost report not found.")
        return redirect(url_for("index"))

    # Get all open found items and rank them against the lost report.
    ranked = matching.rank_matches(lost, db.list_items("found"))
    return render_template("matches.html", lost=lost, ranked=ranked)


# ── Staff routes ───────────────────────────────────────────────────────────

@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    """Staff login page.
    Credentials are stored in .env (STAFF_USERNAME, STAFF_PASSWORD).
    On success, sets session['staff'] = True and redirects home.
    """
    # Already logged in? Skip the login page.
    if session.get("staff"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Read the expected credentials from the environment (.env file).
        valid_user = os.environ.get("STAFF_USERNAME", "staff")
        valid_pass = os.environ.get("STAFF_PASSWORD", "")

        if username == valid_user and password == valid_pass:
            session["staff"] = True          # mark this browser session as staff
            flash("Logged in as staff.")
            return redirect(url_for("index"))

        flash("Incorrect username or password.")

    return render_template("staff_login.html")


@app.route("/staff/logout")
def staff_logout():
    """Clear the staff session and redirect to the home page."""
    session.pop("staff", None)
    flash("Logged out.")
    return redirect(url_for("index"))


@app.route("/staff/dashboard")
@staff_required
def staff_dashboard():
    """Staff dashboard — full overview of all items and recent claims.

    Shows:
      - Overdue reminders: open found items older than 30 days
      - Quick stats: counts by kind and status
      - All items table (lost + found, all statuses)
      - Recent claims / verification history
    """
    return render_template(
        "staff_dashboard.html",
        counts=db.count_items(),                 # summary numbers for the stats bar
        items=db.list_all_items(),               # every item in the database
        claims=db.list_claims(limit=30),         # 30 most recent claim records
        overdue=db.list_overdue_items(days=30),  # open found items older than 30 days
        chart_data=json.dumps(db.get_chart_data()),          # JSON for Chart.js
        feedback_weights=db.compute_feedback_weights(),      # suggested learned weights
        current_weights=matching._load_weights(),            # weights currently in use
    )


@app.route("/staff/mark_unclaimed", methods=["POST"])
@staff_required
def mark_unclaimed():
    """Staff only: mark a found item as 'unclaimed' (e.g. after 30 days).
    This removes it from the open found list without deleting the record.
    """
    item_id = int(request.form["item_id"])
    db.update_item_status(item_id, "unclaimed")
    flash("Item marked as unclaimed.")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/edit/<int:item_id>", methods=["GET", "POST"])
@staff_required
def staff_edit(item_id):
    """Staff only: edit any field of an existing lost or found item."""
    item = db.get_item(item_id)
    if not item:
        flash("Item not found.")
        return redirect(url_for("staff_dashboard"))

    if request.method == "POST":
        f = request.form
        category = f.get("category", "").strip()
        if category == "Other":
            cat_other = f.get("category_other", "").strip()
            if cat_other:
                category = f"Other ({cat_other})"

        color = f.get("color", "").strip()
        if color == "Other":
            col_other = f.get("color_other", "").strip()
            if col_other:
                color = f"Other ({col_other})"

        location = f.get("location", "").strip()
        if location == "Other":
            loc_other = f.get("location_other", "").strip()
            if loc_other:
                location = f"Other ({loc_other})"

        brand = f.get("brand", "").strip()
        description = f.get("description", "").strip()[:500]
        event_time = f.get("event_time", "").strip()
        status = f.get("status", item["status"]).strip()
        contact = f.get("contact", "").strip()
        storage_place = f.get("storage_place", "").strip()
        private_detail = f.get("private_detail", "").strip()

        if not description or not event_time:
            flash("Description and Date & Time cannot be empty.")
        elif not _validate_time(event_time):
            flash("Invalid date/time format.")
        else:
            db.update_item(
                item_id=item_id,
                category=category,
                color=color,
                brand=brand,
                description=description,
                location=location,
                event_time=event_time,
                status=status,
                contact=contact,
                storage_place=storage_place,
                private_detail=private_detail,
            )
            flash(f"Item #{item_id} updated successfully.")
            return redirect(url_for("staff_dashboard"))

    return render_template("staff_edit.html", item=item, cfg=config)


@app.route("/staff/delete/<int:item_id>", methods=["POST"])
@staff_required
def staff_delete(item_id):
    """Staff only: permanently delete an item and its linked claim records."""
    item = db.get_item(item_id)
    if not item:
        flash("Item not found.")
    else:
        db.delete_item(item_id)
        flash(f"Item #{item_id} permanently deleted.")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/apply_weights", methods=["POST"])
@staff_required
def apply_weights():
    """Staff only: save the feedback-learned weights to learned_weights.json.

    The matching engine (matching.py) automatically loads this file the next
    time it scores a match, replacing the config.py defaults with weights
    computed from verified claim history (proposal Section 6.8).

    Requires at least 3 verified claims to compute meaningful weights.
    To reset to defaults, delete learned_weights.json and restart the app.
    """
    weights = db.compute_feedback_weights()
    if weights:
        weights_file = Path(__file__).parent / "learned_weights.json"
        with open(weights_file, "w", encoding="utf-8") as f:
            json.dump(weights, f, indent=2)
        flash("Learned weights applied! The matching engine will now use feedback-adjusted scores.")
    else:
        flash("Not enough verified claims yet — need at least 3 to learn from.")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/export")
@staff_required
def export_csv():
    """Staff only: download all items as a CSV file.
    The file can be opened in Excel or Google Sheets.
    Private details (storage_place, private_detail, contact) are included
    because this is a staff-only route.
    """
    items = db.list_all_items()

    # Build the CSV in memory using Python's csv module.
    # StringIO acts like a file but stores the text in memory instead of on disk.
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row — column names.
    writer.writerow([
        "id", "kind", "category", "color", "brand",
        "description", "location", "event_time", "status",
        "contact", "storage_place", "private_detail", "created_at",
    ])

    # One row per item.
    for item in items:
        writer.writerow([
            item["id"],
            item["kind"],
            item["category"],
            item["color"]        or "",
            item["brand"]        or "",
            item["description"],
            item["location"],
            item["event_time"],
            item["status"],
            item["contact"]       or "",
            item["storage_place"] or "",
            item["private_detail"] or "",
            item["created_at"],
        ])

    # Build a filename with today's date so downloads are easy to identify.
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"kll-lost-and-found-{today}.csv"

    # Return the CSV as a downloadable file attachment.
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/claim", methods=["POST"])
@staff_required   # ← blocks non-staff from submitting this form
def claim():
    """Staff only: record whether a lost item was verified as a match.
    Outcome can be 'Verified', 'Not Verified', or 'Pending'.
    'Verified' closes both items (marks them 'returned' in the database).
    """
    lost_id  = int(request.form["lost_id"])
    found_id = int(request.form["found_id"])
    outcome  = request.form["outcome"]

    # Only accept the three known outcome values — ignore anything else.
    if outcome not in ("Verified", "Not Verified", "Pending"):
        flash("Invalid outcome.")
    else:
        db.record_claim(
            lost_id, found_id, outcome,
            request.form.get("notes", "").strip()
        )
        flash(f"Claim saved: {outcome}")

    # Return to the same matches page after saving.
    return redirect(url_for("matches", lost_id=lost_id))


# ── Run the app ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # debug=True reloads the server when you save a file and shows error details.
    # Turn off debug mode before a public demo.
    app.run(debug=True)
