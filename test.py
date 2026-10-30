"""
FILE: test.py
PURPOSE: Quick sanity check — verifies that the libraries are installed
         correctly and that the basic TF-IDF matching idea works.
         Run with:  python test.py

         Expected output (approximately):
           [[1.        0.63  0.0]]
           Flask 3.1.3 | pandas 3.0.6 | scikit-learn 1.9.1

         The first row shows cosine similarity scores:
           1.0  – the query matches itself perfectly
           0.63 – partial match (same color and room, similar words)
           0.0  – no shared words with the query at all

CSE 103 – Intelligent System | Kolehiyo ng Lungsod ng Lipa
"""

import flask, pandas, sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Three sample documents: one query and two candidates.
docs = [
    "black casio calculator lab 2",      # query (lost item)
    "black scientific calculator lab 2", # candidate 1 (close match)
    "blue water bottle",                 # candidate 2 (no match)
]

# Build TF-IDF matrix: rows = documents, columns = vocabulary words.
tfidf = TfidfVectorizer().fit_transform(docs)

# Compare the first document (query) against all three, including itself.
# Result should be close to [1.0, 0.63, 0.0].
print(cosine_similarity(tfidf[0], tfidf))

# Print library versions to confirm the environment is correct.
import importlib.metadata
flask_ver = importlib.metadata.version("flask")
print(f"Flask {flask_ver} | pandas {pandas.__version__} | scikit-learn {sklearn.__version__}")
