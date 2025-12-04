"""
Cleaner: loads data/raw.json, cleans and normalizes, writes data/cleaned.json.

Usage:
    python src/cleaner.py
"""
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

RAW_JSON = Path(os.getenv("RAW_JSON", "./data/raw.json"))
CLEANED_JSON = Path(os.getenv("CLEANED_JSON", "./data/cleaned.json"))


def normalize_percentage(value):
    """'87%' or '87' -> 87 (int). 'N/A' or None -> None"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    v = str(value).strip()
    if v.lower() in ("n/a", "", "-", "na", "—"):
        return None
    # extract first number
    m = re.search(r'(\d{1,3})', v)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None


def normalize_year(value):
    """Extract 4-digit year, else None"""
    if value is None:
        return None
    v = str(value)
    m = re.search(r'(\d{4})', v)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None


def make_absolute_url(base, url):
    if not url:
        return None
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return "https://www.rottentomatoes.com" + url
    return url


def load_raw_df():
    if not RAW_JSON.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_JSON}")
    with open(RAW_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)


def clean_dataframe(df):
    # Ensure expected columns exist
    for c in ["title", "tomatometer", "audience_score", "release_year", "movie_url", "poster_url"]:
        if c not in df.columns:
            df[c] = None

    # Strip titles and normalize whitespace
    df["title"] = df["title"].astype(str).str.strip().replace({"": None})
    df = df[~df["title"].isna()].copy()

    # Normalize percentages
    df["tomatometer"] = df["tomatometer"].apply(normalize_percentage)
    df["audience_score"] = df["audience_score"].apply(normalize_percentage)

    # Normalize year
    df["release_year"] = df["release_year"].apply(normalize_year)

    # Absolute urls
    df["movie_url"] = df["movie_url"].apply(lambda x: make_absolute_url("https://www.rottentomatoes.com", x))
    df["poster_url"] = df["poster_url"].apply(lambda x: make_absolute_url("https://www.rottentomatoes.com", x))

    # Drop duplicates by title + year (if year not present, dedupe by title)
    before = len(df)
    df.drop_duplicates(subset=["title", "release_year"], inplace=True)
    after = len(df)
    print(f"Removed {before - after} duplicates")

    # Remove rows with no tomatometer and no audience_score maybe? We'll keep if one exists.
    df = df[~(df["tomatometer"].isna() & df["audience_score"].isna())].copy()

    # Optional: remove entries with very short titles
    df = df[df["title"].str.len() > 1]

    # Reset index
    df.reset_index(drop=True, inplace=True)
    return df


def main():
    print("Starting cleaning...")
    df = load_raw_df()
    print(f"Loaded {len(df)} raw records")
    cleaned = clean_dataframe(df)
    print(f"Cleaned records: {len(cleaned)}")

    # Ensure at least 100 records (warning if not)
    if len(cleaned) < 100:
        print("WARNING: cleaned dataset has less than 100 records. You may want to scrape more or expand pages.")

    CLEANED_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(CLEANED_JSON, "w", encoding="utf-8") as f:
        json.dump(cleaned.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print(f"Saved cleaned data to {CLEANED_JSON}")


if __name__ == "__main__":
    main()
