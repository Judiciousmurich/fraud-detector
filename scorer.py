import pandas as pd
from data_pipeline import STATE_BY_LOCATION

# ── Thresholds ────────────────────────────────────────────────────────────────
RISK_THRESHOLD   = 60
HIGH_AMOUNT      = 2500
MEDIUM_AMOUNT    = 1000
ODD_HOUR_START   = 0
ODD_HOUR_END     = 5
RAPID_WINDOW_MIN = 30
RAPID_COUNT      = 3
DAILY_BURST      = 8          # transactions per account per day
CROSS_STATE_HRS  = 4          # impossible travel window (hours)

SUSPICIOUS_CATEGORIES = {"Gambling", "Crypto", "Unknown", "Transfer"}
HIGH_RISK_MERCHANTS = {
    "Casino Online", "Crypto Exchange", "Unknown Merchant", "International Wire",
}


def _account_baselines(df: pd.DataFrame) -> dict:
    """Typical amount and home state per account (Australian patterns)."""
    baselines = {}
    for account, group in df.groupby("account_id"):
        amounts = group["amount"]
        states = group["state"].mode()
        baselines[account] = {
            "median_amount": amounts.median(),
            "home_state": states.iloc[0] if len(states) else None,
            "typical_states": set(group["state"].value_counts().head(2).index),
        }
    return baselines


def _cross_state_ids(df: pd.DataFrame) -> set:
    """Flag accounts with transactions in different states within a short window."""
    flagged = set()
    for account, group in df.sort_values("timestamp").groupby("account_id"):
        rows = group.to_dict("records")
        for i in range(1, len(rows)):
            prev, curr = rows[i - 1], rows[i]
            if prev["state"] == curr["state"]:
                continue
            hours = abs((curr["timestamp"] - prev["timestamp"]).total_seconds()) / 3600
            if hours <= CROSS_STATE_HRS:
                flagged.add(prev["transaction_id"])
                flagged.add(curr["transaction_id"])
    return flagged


def _daily_burst_ids(df: pd.DataFrame) -> set:
    flagged = set()
    df = df.copy()
    df["date"] = df["timestamp"].dt.date
    for (account, day), group in df.groupby(["account_id", "date"]):
        if len(group) >= DAILY_BURST:
            flagged.update(group["transaction_id"])
    return flagged


def score_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if "state" not in df.columns:
        df["state"] = df["location"].map(STATE_BY_LOCATION)
    df["hour"] = df["timestamp"].dt.hour

    baselines = _account_baselines(df)
    cross_state_ids = _cross_state_ids(df)
    daily_burst_ids = _daily_burst_ids(df)

    df_sorted = df.sort_values(["account_id", "timestamp"])
    rapid_ids = set()
    for account, group in df_sorted.groupby("account_id"):
        times = group["timestamp"].tolist()
        ids = group["transaction_id"].tolist()
        for i in range(len(times)):
            count = sum(
                1 for j in range(len(times))
                if i != j
                and abs((times[i] - times[j]).total_seconds()) <= RAPID_WINDOW_MIN * 60
            )
            if count >= RAPID_COUNT:
                rapid_ids.add(ids[i])

    scores, reasons = [], []
    for _, row in df.iterrows():
        score = 0
        rsns = []
        base = baselines.get(row["account_id"], {})

        # 1. Unusual amount (absolute + vs account pattern)
        if row["amount"] >= HIGH_AMOUNT:
            score += 40
            rsns.append(f"High amount (${row['amount']:,.2f})")
        elif row["amount"] >= MEDIUM_AMOUNT:
            score += 20
            rsns.append(f"Elevated amount (${row['amount']:,.2f})")

        median = base.get("median_amount") or 0
        if median > 0 and row["amount"] >= median * 4:
            score += 15
            rsns.append(f"Unusual for account (4× typical ${median:,.0f})")

        # 2. Frequency — rapid-fire and daily burst
        if row["transaction_id"] in rapid_ids:
            score += 20
            rsns.append("Rapid consecutive transactions")
        if row["transaction_id"] in daily_burst_ids:
            score += 15
            rsns.append("High daily transaction frequency")

        # 3. Account patterns — cross-state velocity & atypical state
        if row["transaction_id"] in cross_state_ids:
            score += 30
            rsns.append(f"Cross-state activity ({row['location']})")
        elif base.get("home_state") and row["state"] not in base.get("typical_states", {base["home_state"]}):
            score += 10
            rsns.append(f"Atypical state for account ({row['state']})")

        # 4. Odd hours
        if ODD_HOUR_START <= row["hour"] <= ODD_HOUR_END:
            score += 20
            rsns.append(f"Unusual hour ({row['hour']:02d}:xx AEST)")

        # 5. High-risk merchant / category
        if row["merchant"] in HIGH_RISK_MERCHANTS:
            score += 25
            rsns.append(f"High-risk merchant ({row['merchant']})")
        elif row["category"] in SUSPICIOUS_CATEGORIES:
            score += 15
            rsns.append(f"Suspicious category ({row['category']})")

        score = min(score, 100)
        scores.append(score)
        reasons.append("; ".join(rsns) if rsns else "No indicators")

    df["risk_score"] = scores
    df["risk_reasons"] = reasons
    df["risk_level"] = df["risk_score"].apply(
        lambda s: "HIGH" if s >= RISK_THRESHOLD else ("MEDIUM" if s >= 30 else "LOW")
    )
    df["flagged"] = df["risk_score"] >= RISK_THRESHOLD
    df["review_status"] = "Pending"
    df["alert_generated"] = df["flagged"]
    return df
