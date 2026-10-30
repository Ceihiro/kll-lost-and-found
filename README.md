# KLL Lost and Found

lost-and-found matching system for Kolehiyo ng Lungsod ng Lipa (KLL). Made for **CSE 103 Intelligent System**.

Someone reports a lost item, staff log a found item, and the system suggests the most likely matches with a score and the reasons. Staff always verify the owner before an item is released.

## Screenshots

| Home                                    | Report a lost item                                      | Possible matches                                  |
| --------------------------------------- | ------------------------------------------------------- | ------------------------------------------------- |
| ![Home page](docs/screenshots/home.png) | ![Report a lost item](docs/screenshots/report-lost.png) | ![Possible matches](docs/screenshots/matches.png) |

## Quick start (Windows)

You need **Python 3.13** (tick "Add python.exe to PATH" when installing) and **Git**. Don't have them? See [SETUP.md](SETUP.md).

Open Command Prompt and run these one at a time:

```
mkdir C:\dev
cd C:\dev
git clone https://github.com/Ceihiro/kll-lost-and-found.git
cd findit-ai
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python seed_data.py
python app.py
```

Then open **http://127.0.0.1:5000** in your browser. Press **Ctrl + C** in the terminal to stop.

Every time you come back: `cd C:\dev\findit-ai`, `venv\Scripts\activate`, `git pull`, `python app.py`.

## How it works

Each found item gets two scores, mixed 50/50:

- **Attribute score (rules):** category, color, brand, location, and time.
- **Text score (AI):** TF-IDF and cosine similarity on the descriptions, using scikit-learn.

The top 3 matches are shown with the reasons. The weights are in `config.py`.

## Files

| File                    | What it does                          | Owner                  |
| ----------------------- | ------------------------------------- | ---------------------- |
| `app.py`, `db.py`       | Pages, forms, and the SQLite database | Backend coder          |
| `matching.py`           | The scoring and ranking               | Matching coder         |
| `templates/`, `static/` | Page layouts and look                 | Interface coder        |
| `evaluate.py`, `data/`  | Accuracy tests                        | Testing coder          |
| `config.py`             | Categories, rooms, and weights        | Everyone (small edits) |

## Still to build

- Staff login
- Dashboard and CSV export
- Reminders for unclaimed items
- Feedback buttons that adjust the weights
