"""Automatic alert generation and admin review log history."""
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ALERT_LOG_PATH = os.path.join(DATA_DIR, "alert_log.json")
REVIEW_LOG_PATH = os.path.join(DATA_DIR, "review_log.json")


def _load_json(path: str) -> list | dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return [] if path.endswith("_log.json") and "alert" in path else {}


def _save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def sync_alerts(df) -> list[dict]:
    """Create alert log entries for newly flagged transactions."""
    logs = _load_json(ALERT_LOG_PATH)
    if not isinstance(logs, list):
        logs = []
    existing_ids = {e["transaction_id"] for e in logs}

    for _, row in df[df["flagged"]].iterrows():
        tid = row["transaction_id"]
        if tid in existing_ids:
            continue
        logs.append({
            "transaction_id": tid,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event": "ALERT_TRIGGERED",
            "message": f"Risk score {row['risk_score']}/100 — {row['risk_reasons']}",
            "risk_score": int(row["risk_score"]),
            "risk_level": row["risk_level"],
        })
        existing_ids.add(tid)

    _save_json(ALERT_LOG_PATH, logs)
    return logs


def get_logs_for_transaction(tid: str) -> list[dict]:
    alert_logs = _load_json(ALERT_LOG_PATH)
    review_logs = _load_json(REVIEW_LOG_PATH)
    if not isinstance(review_logs, dict):
        review_logs = {}

    entries = [e for e in alert_logs if e.get("transaction_id") == tid]
    entries.extend(review_logs.get(tid, []))
    entries.sort(key=lambda e: e.get("timestamp", ""))
    return entries


def append_review_log(tid: str, status: str, note: str = "") -> None:
    logs = _load_json(REVIEW_LOG_PATH)
    if not isinstance(logs, dict):
        logs = {}
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": "ADMIN_REVIEW",
        "message": f"Status updated to: {status}" + (f" — {note}" if note else ""),
        "status": status,
    }
    logs.setdefault(tid, []).append(entry)
    _save_json(REVIEW_LOG_PATH, logs)
