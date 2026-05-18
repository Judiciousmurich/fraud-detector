"""Load, review, and clean Australian payment transaction data."""
import os
import re
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_PATH = os.path.join(DATA_DIR, "transactions_raw.csv")
CLEAN_PATH = os.path.join(DATA_DIR, "transactions.csv")

# Australian cities only — all locations must match one of these
AU_LOCATIONS = {
    "Sydney, NSW",
    "Melbourne, VIC",
    "Brisbane, QLD",
    "Perth, WA",
    "Adelaide, SA",
    "Canberra, ACT",
    "Gold Coast, QLD",
    "Newcastle, NSW",
    "Hobart, TAS",
    "Darwin, NT",
}

LOCATION_ALIASES = {
    "sydney": "Sydney, NSW",
    "melbourne": "Melbourne, VIC",
    "brisbane": "Brisbane, QLD",
    "perth": "Perth, WA",
    "adelaide": "Adelaide, SA",
    "canberra": "Canberra, ACT",
    "gold coast": "Gold Coast, QLD",
    "newcastle": "Newcastle, NSW",
    "hobart": "Hobart, TAS",
    "darwin": "Darwin, NT",
}

STATE_BY_LOCATION = {
    loc: loc.split(", ")[-1] for loc in AU_LOCATIONS
}

REQUIRED_COLUMNS = [
    "transaction_id",
    "account_id",
    "timestamp",
    "merchant",
    "category",
    "amount",
    "location",
    "status",
]


def _normalize_location(value: str) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text in AU_LOCATIONS:
        return text
    key = text.lower()
    if key in LOCATION_ALIASES:
        return LOCATION_ALIASES[key]
    for loc in AU_LOCATIONS:
        if loc.lower() in key or key in loc.lower():
            return loc
    return None


def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Review and clean records; keep Australia locations only."""
    report = {
        "input_rows": len(df),
        "dropped_missing": 0,
        "dropped_invalid_amount": 0,
        "dropped_non_australia": 0,
        "dropped_duplicates": 0,
        "dropped_invalid_status": 0,
        "output_rows": 0,
    }

    df = df.copy()
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    before = len(df)
    df = df.dropna(subset=["transaction_id", "account_id", "timestamp", "amount", "location"])
    report["dropped_missing"] = before - len(df)

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    before = len(df)
    df = df[df["amount"].notna() & (df["amount"] > 0)]
    report["dropped_invalid_amount"] = before - len(df)

    df["location"] = df["location"].apply(_normalize_location)
    before = len(df)
    df = df[df["location"].isin(AU_LOCATIONS)]
    report["dropped_non_australia"] = before - len(df)

    df["status"] = df["status"].fillna("completed").str.strip().str.lower()
    before = len(df)
    df = df[df["status"] == "completed"]
    report["dropped_invalid_status"] = before - len(df)

    before = len(df)
    df = df.drop_duplicates(subset=["transaction_id"], keep="first")
    report["dropped_duplicates"] = before - len(df)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df[df["timestamp"].notna()]
    df["state"] = df["location"].map(STATE_BY_LOCATION)
    df = df.sort_values("timestamp").reset_index(drop=True)

    report["output_rows"] = len(df)
    return df, report


def load_and_clean(path: str | None = None) -> tuple[pd.DataFrame, dict]:
    path = path or CLEAN_PATH
    if not os.path.exists(path) and os.path.exists(RAW_PATH):
        path = RAW_PATH
    df = pd.read_csv(path)
    return clean_transactions(df)


def save_cleaned(df: pd.DataFrame, path: str | None = None) -> str:
    path = path or CLEAN_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = df.drop(columns=["state"], errors="ignore")
    out.to_csv(path, index=False)
    return path
