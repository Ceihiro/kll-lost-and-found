# KLL Smart Find AI (Lost & Found Portal)

An intelligent, NLP-driven lost-and-found management and matching system designed for **Kolehiyo ng Lungsod ng Lipa (KLL)**. Built for **CSE 103 Intelligent System**.

Students report lost items or staff log found items, and the system ranks the most probable matches using a hybrid scoring model (Rule-Based Attribute Weighting + TF-IDF Cosine Similarity with Taglish normalization). Authorized staff review, update, and verify ownership before releasing items.

---

## Key Features

- **Hybrid AI Matching Engine:** 50% Rule-Based attribute matching + 50% NLP text similarity with Tagalog/Taglish vocabulary normalization (`payong` $\rightarrow$ `umbrella`, `pitaka` $\rightarrow$ `wallet`, etc.).
- **100% Accuracy Benchmark:** Tested across 22 lost reports and 27 found reports achieving **100% Top-1 and 100% Top-3 accuracy**.
- **Complete Staff CRUD:** Full Create, Read, Update, and Delete capabilities for authorized staff to correct typos, reassign custody, or purge invalid/duplicate entries.
- **Adaptive Machine Learning Feedback Loop:** Analyzes confirmed true claims to calculate suggested attribute weights and allows staff to refine the matching engine via `learned_weights.json`.
- **Visual Analytics Dashboard:** Real-time KPI summary cards and interactive Chart.js visualizations (Category Distribution, Top Loss Hotspots, Status Breakdown).
- **Institutional BBGU-Inspired UI:** Vladivostok State University (BBGU) style solid header with downward notch arch, Dark Maroon (`#6B0020`) and Floral White (`#FFFAF0`) palette, floating toast notifications, and smooth fluid page flow with auto-locking sections.
- **Dynamic "Other" Input Support:** Category, Color, and Location dropdowns reveal custom input fields when selecting "Other", which seamlessly feed into attribute comparisons and TF-IDF text vectors.

---

## Screenshots

| Home (Campus Portal) | Report a Lost Item | Possible AI Matches |
| --- | --- | --- |
| ![Home page](docs/screenshots/home.png) | ![Report a lost item](docs/screenshots/report-lost.png) | ![Possible matches](docs/screenshots/matches.png) |

---

## Quick Start (Windows)

Prerequisites: **Python 3.10+** (tested on Python 3.13) and **Git**. See [SETUP.md](SETUP.md) for full setup instructions.

```powershell
mkdir C:\dev
cd C:\dev
git clone https://github.com/Ceihiro/kll-lost-and-found.git
cd kll-lost-and-found
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed_data.py
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Press **Ctrl + C** to terminate the server.

Every subsequent session:
```powershell
cd C:\dev\kll-lost-and-found
venv\Scripts\activate
python app.py
```

---

## How the Matching Engine Works

Each candidate item is evaluated across two complementary dimensions mixed 50/50 (configurable in `config.py`):

| Score Dimension | Method | Implementation Details |
|---|---|---|
| **Attribute Score** | Rule-Based | Compares category, color, brand, campus location, and event time window. Missing optional attributes are dynamically excluded and weights are proportionally rescaled. |
| **Text Score** | NLP (AI) | Scikit-learn TF-IDF vectorizer + Cosine Similarity. Includes built-in Tagalog/Taglish normalization and campus stop-word filtering. |

### Evaluation Benchmark Results (`evaluate.py`)

Evaluated offline on **22 lost reports** and **27 found reports**:

| Method | Top-1 Accuracy | Top-3 Accuracy |
|---|---|---|
| Attribute Only | 100% | 100% |
| Text (NLP) Only | 100% | 100% |
| **Combined (Hybrid)** | **100%** | **100%** |

Run the benchmark at any time:
```powershell
python evaluate.py
```

---

## Web Routes & Permissions

| Route | Role | Description |
|---|---|---|
| `/` | Public | Homepage — Browse active lost reports and open found catalog |
| `/lost` | Public | Submit a lost item report |
| `/found` | Public / Staff | Log a found item (includes private verification details) |
| `/matches/<lost_id>` | Public / Staff | Ranked AI matches for a specific lost item |
| `/staff/login` | Staff | Authenticate staff credentials stored securely in `.env` |
| `/staff/logout` | Staff | Invalidate staff session |
| `/staff/dashboard` | Staff Only | Complete dashboard: KPIs, overdue alerts, charts, inventory table, and AI weight tuning |
| `/staff/edit/<item_id>` | Staff Only | **CRUD Update:** Edit any field, status, or custody detail of an item |
| `/staff/delete/<item_id>` | Staff Only | **CRUD Delete:** Permanently remove an item and associated claims |
| `/staff/mark_unclaimed` | Staff Only | Transition an item to `unclaimed` archive status |
| `/staff/apply_weights` | Staff Only | Apply feedback-learned weights from verified claims to `learned_weights.json` |
| `/staff/export` | Staff Only | Export full inventory as CSV |
| `/claim` | Staff Only | Record student ownership verification outcome (`Verified`, `Not Verified`, `Pending`) |

---

## Project Structure (3-Tier Architecture)

The codebase is organized into three distinct layers so that anyone reviewing the project immediately understands what runs the app versus what supports testing and documentation:

### Tier 1: Core System (Live Application)
These files and directories form the functional web portal and Intelligent System:

| File / Directory | Layer | Purpose |
|---|---|---|
| `app.py` | Web Controller | Primary Flask application defining all public and staff routes, CSRF guards, and session authentication. |
| `matching.py` | AI / NLP Engine | Core intelligent matching engine (Taglish normalization, attribute scoring, TF-IDF cosine similarity). |
| `db.py` | Database Layer | SQLite operations: item CRUD, claim logging, status transitions, and machine learning feedback calculations. |
| `config.py` | System Settings | Centralized settings: campus room names, item categories, color palettes, and AI weight presets. |
| `templates/` | View Templates | Jinja2 HTML templates (`index.html`, `lost.html`, `found.html`, `matches.html`, `staff_dashboard.html`, `staff_edit.html`). |
| `static/` | UI Assets | Institutional stylesheet (`style.css`), campus emblems (`KLL-logo.webp`), and visual assets. |
| `kll-lost-and-found.db` | Data Persistence | SQLite database storing active lost/found records and verification audit history. |
| `.env` | Local Secrets | Environment credentials (`STAFF_USERNAME`, `STAFF_PASSWORD`, `SECRET_KEY`). |

### Tier 2: AI Evaluation & QA Harness
Standalone test tools used to validate algorithm precision and seed demo records:

| File / Directory | Layer | Purpose |
|---|---|---|
| `evaluate.py` | Benchmark Harness | Automated offline test script calculating Top-1 and Top-3 accuracy across sample pairs. |
| `data/` | Evaluation Dataset | CSV files (`lost_reports.csv`, `found_reports.csv`, `true_matches.csv`) tested by `evaluate.py`. |
| `seed_data.py` | Data Seeder | Populates initial campus items into the database for demonstration. |
| `test.py` | Smoke Test | Validates that required ML libraries (scikit-learn, Flask, pandas) are installed and working. |

### Tier 3: Repository, Collaboration & Documentation
Artifacts supporting open-source collaboration, installation, and presentation:

| File / Directory | Layer | Purpose |
|---|---|---|
| `README.md` | Portal Overview | Complete system documentation, benchmark results, and route specifications. |
| `SETUP.md` | Setup Guide | Step-by-step developer setup and troubleshooting guide for teammates. |
| `requirements.txt` | Dependencies | Pip requirements manifest for reproducible environment creation. |
| `.gitignore` | Git Rules | Excludes virtual environments, database binaries, and local `.env` files from Git. |
| `.env.example` | Config Template | Reference template for creating local `.env` configuration. |
| `docs/` | Media & Docs | Screenshots and project imagery used across documentation. |
| `KLL-Lost-and-Found-docs/` | Internal Archive | Internal project deliverables (proposal docx, team roles, daily logs). |

---

## Security & Privacy Measures

- **Environment Secrets:** Sensitive credentials (`STAFF_USERNAME`, `STAFF_PASSWORD`, `SECRET_KEY`) reside in `.env` and are strictly excluded from git.
- **CSRF Defense:** All state-changing forms (`POST`) require valid CSRF tokens verified via Flask-WTF.
- **Blind Verification Detail:** Found items store a `private_detail` (e.g. scratch, serial number, inside sticker) hidden from the public view; staff verify this before confirming ownership.
- **Role-Based Access Control:** Edit, Delete, Claim Verification, CSV export, and Analytics dashboards are strictly gated behind `@staff_required`.
