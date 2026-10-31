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
import re
from datetime import datetime, timedelta
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
        cat_other = f.get("category_other", "").strip()[:60]
        if cat_other:
            category = f"Other ({cat_other})"

    color = f.get("color", "").strip()
    if color == "Other":
        col_other = f.get("color_other", "").strip()[:60]
        if col_other:
            color = f"Other ({col_other})"

    location = f.get("location", "").strip()
    if location == "Other":
        loc_other = f.get("location_other", "").strip()[:60]
        if loc_other:
            location = f"Other ({loc_other})"

    # Handle both combined event_time and split event_date + event_time_clock
    event_time = f.get("event_time", "").strip()
    if not event_time:
        ed = f.get("event_date", "").strip()
        et = f.get("event_time_clock", "").strip()
        if ed and et:
            event_time = f"{ed}T{et}"
        elif ed:
            event_time = f"{ed}T12:00"

    return dict(
        kind=kind,
        category=category,
        color=color,
        brand=f.get("brand", "").strip()[:50],
        description=f.get("description", "").strip()[:500],
        location=location,
        event_time=event_time,
    )


def _get_date_bounds():
    """Return common date/time values and 5-year bounds for form templates."""
    now_dt = datetime.now()
    now_date = now_dt.strftime("%Y-%m-%d")
    now_time = now_dt.strftime("%H:%M")
    now = now_dt.strftime("%Y-%m-%dT%H:%M")
    try:
        min_dt = now_dt.replace(year=now_dt.year - 5)
    except ValueError:
        min_dt = now_dt.replace(year=now_dt.year - 5, day=28)
    min_date = min_dt.strftime("%Y-%m-%d")
    return dict(now=now, now_date=now_date, now_time=now_time, min_date=min_date)


def _validate_time(event_time):
    """Validate that event_time is a valid ISO datetime string,
    is not set in the future (with 5 minutes leeway for clock differences),
    and is not older than 5 years in the past.
    Returns (is_valid, error_message).
    """
    try:
        dt = datetime.fromisoformat(event_time)
    except (TypeError, ValueError):
        return False, "Invalid date/time — please use the date picker."

    now = datetime.now()
    if dt > now + timedelta(minutes=5):
        return False, "The date and time cannot be in the future."

    try:
        five_years_ago = now.replace(year=now.year - 5)
    except ValueError:
        five_years_ago = now.replace(year=now.year - 5, day=28)

    if dt < five_years_ago:
        return False, "The date cannot be older than 5 years in the past."

    return True, ""


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
    bounds = _get_date_bounds()

    if request.method == "POST":
        data = _form_item("lost")

        # Read student / reporter identity fields (defensive length bounds)
        who = request.form.get("reporter_role", "Student").strip()
        if who not in ("Student", "Faculty", "Campus Guard"):
            who = "Student"
        first_name = request.form.get("first_name", "").strip()[:50]
        last_name  = request.form.get("last_name", "").strip()[:50]
        reporter_name = request.form.get("reporter_name", "").strip()[:100]

        if first_name or last_name:
            full_name = f"{first_name} {last_name}".strip()
        else:
            full_name = reporter_name

        reporter_id      = request.form.get("reporter_id", "").strip()[:15]
        reporter_section = request.form.get("reporter_section", "").strip()[:20]

        if full_name:
            parts = [full_name]
            if who:
                parts.append(f"({who})")
            if reporter_id:
                parts.append(f"ID: {reporter_id}")
            if reporter_section:
                parts.append(reporter_section)
            contact = " | ".join(parts)
        else:
            contact = request.form.get("contact", "").strip()[:150]

        # Validation rules:
        is_valid_time, time_err = _validate_time(data["event_time"])
        name_pattern = re.compile(r"^[A-Za-z\s\.\-']+$")
        id_pattern = re.compile(r"^[0-9\-]+$")

        if not data["description"] or not data["event_time"]:
            flash("Please fill in the description and the date/time.")
        elif len(data["description"]) < 10:
            flash("Please provide a more descriptive summary (at least 10 characters).")
        elif not is_valid_time:
            flash(time_err)
        elif first_name and not name_pattern.match(first_name):
            flash("First name should contain letters only.")
        elif last_name and not name_pattern.match(last_name):
            flash("Last name should contain letters only.")
        elif reporter_id and not id_pattern.match(reporter_id):
            flash("Student ID must contain numbers and hyphens only (e.g. 2024-00123).")
        else:
            lost_id = db.add_item(
                **data,
                contact=contact
            )
            # After saving, immediately show the matching results.
            return redirect(url_for("matches", lost_id=lost_id))

    return render_template("lost.html", cfg=config, **bounds)


@app.route("/found", methods=["GET", "POST"])
def log_found():
    """GET  → show the 'Log a found item' form.
    POST → validate, save the found item, redirect home.
    """
    bounds = _get_date_bounds()

    if request.method == "POST":
        data = _form_item("found")

        who = request.form.get("reporter_role", "Student").strip()
        if who not in ("Student", "Faculty", "Campus Guard"):
            who = "Student"
        first_name = request.form.get("first_name", "").strip()[:50]
        last_name  = request.form.get("last_name", "").strip()[:50]
        storage_place = request.form.get("storage_place", "").strip()[:100]
        private_detail = request.form.get("private_detail", "").strip()[:200]

        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            contact = f"{full_name} ({who})" if who else full_name
        else:
            contact = request.form.get("contact", "").strip()[:150]

        is_valid_time, time_err = _validate_time(data["event_time"])
        name_pattern = re.compile(r"^[A-Za-z\s\.\-']+$")

        if not data["description"] or not data["event_time"]:
            flash("Please fill in the description and the date/time.")
        elif len(data["description"]) < 10:
            flash("Please provide a more descriptive summary (at least 10 characters).")
        elif not is_valid_time:
            flash(time_err)
        elif first_name and not name_pattern.match(first_name):
            flash("First name should contain letters only.")
        elif last_name and not name_pattern.match(last_name):
            flash("Last name should contain letters only.")
        else:
            db.add_item(
                **data,
                contact=contact,
                storage_place=storage_place,
                private_detail=private_detail,
            )
            flash("Found item saved successfully.")
            return redirect(url_for("index"))

    return render_template("found.html", cfg=config, **bounds)


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
        valid_pass = os.environ.get("STAFF_PASSWORD", "kll2026")

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

        is_valid_time, time_err = _validate_time(event_time)
        if not description or not event_time:
            flash("Description and Date & Time cannot be empty.")
        elif not is_valid_time:
            flash(time_err)
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

    bounds = _get_date_bounds()
    return render_template("staff_edit.html", item=item, cfg=config, **bounds)


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


@app.route("/staff/revert_claim/<int:claim_id>", methods=["POST"])
@staff_required
def revert_claim(claim_id):
    """Staff only: revert an accidental claim outcome and restore items to open."""
    if db.revert_claim(claim_id):
        flash(f"Claim audit #{claim_id} reverted successfully. Linked items are now Open again.")
    else:
        flash("Claim record not found.")
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
