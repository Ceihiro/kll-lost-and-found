"""
FILE: seed_data.py
PURPOSE: Loads sample found and lost items into the database so you can test the
         matching engine right away without manually typing in data.
         Run this once after setting up the project:  python seed_data.py

         Source files:
           - data/found_reports.csv (25 sample found items)
           - data/lost_reports.csv  (sample lost items)

CSE 103 – Intelligent System | Kolehiyo ng Lungsod ng Lipa
"""

import csv
from pathlib import Path

import db   # our database helper

# Make sure the tables exist before inserting anything.
db.init_db()

DATA_DIR = Path(__file__).parent / "data"

# 1. Load sample found reports
found_file = DATA_DIR / "found_reports.csv"
found_count = 0
if found_file.exists():
    with open(found_file, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            db.add_item(
                kind="found",
                category=row["category"],
                color=row.get("color", ""),
                brand=row.get("brand", ""),
                description=row["description"],
                location=row["location"],
                event_time=row["event_time"],
                storage_place="Faculty room cabinet",
                private_detail="(sample verification detail)",
            )
            found_count += 1

# 2. Load a few sample lost reports (first 5) so the home page shows both sides
lost_file = DATA_DIR / "lost_reports.csv"
lost_count = 0
sample_contacts = [
    "Maria Santos | (Student) | ID: 2023-01452 | BSCS 2B",
    "John Carlo Reyes | (Student) | ID: 2022-00891 | BSCS 3A",
    "Prof. Aris Dela Cruz | (Faculty) | ID: 2018-00045 | DCS",
    "Bea Nicole Mendoza | (Student) | ID: 2024-03120 | BSED 1A",
    "Mark Anthony Ramos | (Student) | ID: 2021-00673 | BSCpE 4A",
]
if lost_file.exists():
    with open(lost_file, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= 5:  # load 5 sample lost reports
                break
            db.add_item(
                kind="lost",
                category=row["category"],
                color=row.get("color", ""),
                brand=row.get("brand", ""),
                description=row["description"],
                location=row["location"],
                event_time=row["event_time"],
                contact=sample_contacts[i % len(sample_contacts)],
            )
            lost_count += 1

print(f"Database seeded successfully!")
print(f" - {found_count} sample found items added")
print(f" - {lost_count} sample lost reports added")
print("\nRefresh http://127.0.0.1:5000 in your browser to see them!")
