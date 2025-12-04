"""
Loader: loads data/cleaned.json and inserts into SQLite database.

Usage:
    python src/loader.py
"""
import json
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

CLEANED_JSON = Path(os.getenv("CLEANED_JSON", "./data/cleaned.json"))
SQLITE_DB = Path(os.getenv("SQLITE_DB", "./data/output.db"))

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    tomatometer INTEGER,
    audience_score INTEGER,
    release_year INTEGER,
    movie_url TEXT,
    poster_url TEXT
);
"""

INSERT_SQL = """
INSERT INTO movies (title, tomatometer, audience_score, release_year, movie_url, poster_url)
VALUES (?, ?, ?, ?, ?, ?);
"""


def create_db_and_table(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()


def load_cleaned_and_insert(db_path: Path):
    if not CLEANED_JSON.exists():
        raise FileNotFoundError(f"Cleaned JSON not found: {CLEANED_JSON}")

    with open(CLEANED_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Optional: clear table (or keep existing)
    # cur.execute("DELETE FROM movies;")

    to_insert = []
    for r in records:
        title = r.get("title")
        tomatometer = r.get("tomatometer")
        audience_score = r.get("audience_score")
        release_year = r.get("release_year")
        movie_url = r.get("movie_url")
        poster_url = r.get("poster_url")
        to_insert.append((title, tomatometer, audience_score, release_year, movie_url, poster_url))

    cur.executemany(INSERT_SQL, to_insert)
    conn.commit()
    conn.close()
    print(f"Inserted {len(to_insert)} records into {db_path}")


def main():
    print("Starting loader...")
    create_db_and_table(SQLITE_DB)
    load_cleaned_and_insert(SQLITE_DB)
    print("Loader finished.")


if __name__ == "__main__":
    main()
