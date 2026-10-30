"""
FILE: evaluate.py
PURPOSE: Offline accuracy test for the matching engine.
         Loads fake lost and found reports from the data/ folder,
         runs the matching engine on each lost report, then checks
         whether the correct found item appears in the top-1 or top-3 results.

         Prints a comparison table for three methods:
           Attribute only  – rule-based score only
           Text only       – TF-IDF cosine similarity only
           Combined        – 50/50 mix (the default in config.py)

         This is the experiment described in the proposal.
         Run it with:  python evaluate.py

Input files in data/:
  lost_reports.csv   – fake lost reports  (id, category, color, brand, description, location, event_time)
  found_reports.csv  – fake found reports (same columns)
  true_matches.csv   – correct answers    (lost_id, found_id)

CSE 103 – Intelligent System | Kolehiyo ng Lungsod ng Lipa
"""

import csv
from pathlib import Path

import matching   # our matching engine

# Where the test CSV files live.
DATA = Path(__file__).parent / "data"


def read_csv(name):
    """Read a CSV file from the data/ folder and return a list of dicts."""
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def accuracy(lost_rows, found_rows, truth, attribute_share, text_share):
    """Compute top-1 and top-3 accuracy for one scoring method.

    Parameters
    ----------
    lost_rows       : list of lost item dicts from CSV
    found_rows      : list of found item dicts from CSV
    truth           : dict mapping lost_id → correct found_id
    attribute_share : weight for the rule-based score (0.0–1.0)
    text_share      : weight for the NLP score (0.0–1.0)

    Returns
    -------
    (top1_rate, top3_rate) as floats between 0.0 and 1.0
    """
    top1 = top3 = 0

    for lost in lost_rows:
        # Rank the top 3 found items for this lost report.
        ranked = matching.rank_matches(
            lost, found_rows, top_n=3,
            attribute_share=attribute_share,
            text_share=text_share,
        )
        # Get the found ids in ranked order.
        ids = [r["found"]["id"] for r in ranked]

        # The correct answer for this lost item.
        correct = truth.get(lost["id"])

        # Count how many times the correct answer appears in position 1 or top 3.
        top1 += bool(ids) and ids[0] == correct
        top3 += correct in ids

    n = len(lost_rows)
    return top1 / n, top3 / n   # convert counts to rates (0.0–1.0)


def main():
    # Load all three CSV files.
    lost_rows  = read_csv("lost_reports.csv")
    found_rows = read_csv("found_reports.csv")
    truth      = {r["lost_id"]: r["found_id"] for r in read_csv("true_matches.csv")}

    # The three methods to compare.
    # (None, None) means "use whatever is in config.py".
    methods = [
        ("Attribute only", 1.0,  0.0 ),
        ("Text only",      0.0,  1.0 ),
        ("Combined",       None, None),
    ]

    print(f"{len(lost_rows)} lost reports, {len(found_rows)} found reports\n")
    print(f"{'Method':<16}{'Top-1':>8}{'Top-3':>8}")
    print("-" * 32)

    for name, a, t in methods:
        top1, top3 = accuracy(lost_rows, found_rows, truth, a, t)
        print(f"{name:<16}{top1:>8.0%}{top3:>8.0%}")


if __name__ == "__main__":
    main()
