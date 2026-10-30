"""Quick debug to show remaining text-only failures."""
import csv
from pathlib import Path
import matching

DATA = Path(__file__).parent / "data"

def read_csv(name):
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

lost_rows  = read_csv("lost_reports.csv")
found_rows = read_csv("found_reports.csv")
truth      = {r["lost_id"]: r["found_id"] for r in read_csv("true_matches.csv")}

print("=== TEXT ONLY FAILURES ===\n")
fails = 0
for lost in lost_rows:
    ranked = matching.rank_matches(lost, found_rows, top_n=3, attribute_share=0.0, text_share=1.0)
    ids = [r["found"]["id"] for r in ranked]
    correct = truth.get(lost["id"])
    if not (bool(ids) and ids[0] == correct):
        fails += 1
        print(f"Lost #{lost['id']}: {lost['description']}")
        for f in found_rows:
            if f["id"] == correct:
                print(f"  Correct #{correct}: {f['description']}")
        for f in found_rows:
            if f["id"] == ids[0]:
                print(f"  Got     #{ids[0]}: {f['description']}")
        for r in ranked:
            if r["found"]["id"] == correct:
                print(f"  Correct score: {r['text_score']:.3f}")
        for r in ranked:
            if r["found"]["id"] == ids[0]:
                print(f"  Wrong score:   {r['text_score']:.3f}")
        print()

print(f"Total failures: {fails}/20")
