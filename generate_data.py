import os
import random
import pandas as pd
from datetime import datetime, timedelta

from data_pipeline import AU_LOCATIONS, RAW_PATH, save_cleaned

random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

MERCHANTS = [
    "Woolworths", "Coles", "JB Hi-Fi", "Bunnings", "Kmart",
    "David Jones", "Harvey Norman", "Chemist Warehouse", "BWS",
    "Uber Eats", "DoorDash", "Netflix", "Spotify", "Apple Store",
    "Shell", "BP", "7-Eleven", "ANZ ATM", "CommBank ATM",
    "Online Transfer", "International Wire", "Casino Online",
    "Crypto Exchange", "Unknown Merchant", "Luxury Jewellers",
]

CATEGORIES = {
    "Woolworths": "Groceries", "Coles": "Groceries",
    "JB Hi-Fi": "Electronics", "Harvey Norman": "Electronics",
    "Bunnings": "Hardware", "Kmart": "Retail",
    "David Jones": "Retail", "Chemist Warehouse": "Pharmacy",
    "BWS": "Alcohol", "Uber Eats": "Food Delivery",
    "DoorDash": "Food Delivery", "Netflix": "Subscription",
    "Spotify": "Subscription", "Apple Store": "Digital",
    "Shell": "Fuel", "BP": "Fuel", "7-Eleven": "Convenience",
    "ANZ ATM": "Cash Withdrawal", "CommBank ATM": "Cash Withdrawal",
    "Online Transfer": "Transfer", "International Wire": "Transfer",
    "Casino Online": "Gambling", "Crypto Exchange": "Crypto",
    "Unknown Merchant": "Unknown", "Luxury Jewellers": "Luxury",
}

AU_LOCATION_LIST = sorted(AU_LOCATIONS)
ACCOUNT_IDS = [f"ACC{str(i).zfill(5)}" for i in range(1, 51)]
# Each account has a typical home city (Australian only)
ACCOUNT_HOME = {acc: random.choice(AU_LOCATION_LIST) for acc in ACCOUNT_IDS}


def generate_transactions(n=200):
    records = []
    base_time = datetime(2026, 4, 1, 8, 0, 0)

    for i in range(n):
        account = random.choice(ACCOUNT_IDS)
        merchant = random.choice(MERCHANTS)
        category = CATEGORIES[merchant]
        home = ACCOUNT_HOME[account]
        location = home if random.random() < 0.75 else random.choice(AU_LOCATION_LIST)

        is_fraud_candidate = random.random() < 0.22
        txn_time = base_time + timedelta(minutes=random.randint(0, 43200))

        if is_fraud_candidate:
            fraud_type = random.choice([
                "high_amount", "cross_state", "odd_hours",
                "rapid_fire", "suspicious_merchant", "unusual_location",
            ])
            if fraud_type == "high_amount":
                amount = round(random.uniform(3000, 15000), 2)
                merchant = random.choice(["Luxury Jewellers", "Harvey Norman", "Apple Store"])
                category = CATEGORIES[merchant]
            elif fraud_type == "cross_state":
                # Distant Australian city vs account home (same-day travel pattern)
                distant = [loc for loc in AU_LOCATION_LIST if loc != home]
                location = random.choice(distant)
                amount = round(random.uniform(500, 4000), 2)
            elif fraud_type == "odd_hours":
                txn_time = txn_time.replace(hour=random.choice([1, 2, 3, 4]))
                amount = round(random.uniform(200, 2000), 2)
            elif fraud_type == "rapid_fire":
                amount = round(random.uniform(100, 800), 2)
            elif fraud_type == "suspicious_merchant":
                merchant = random.choice([
                    "Casino Online", "Crypto Exchange",
                    "Unknown Merchant", "International Wire",
                ])
                category = CATEGORIES[merchant]
                amount = round(random.uniform(500, 5000), 2)
            elif fraud_type == "unusual_location":
                location = random.choice([loc for loc in AU_LOCATION_LIST if loc != home])
                amount = round(random.uniform(300, 2500), 2)
        else:
            if category == "Groceries":
                amount = round(random.uniform(15, 280), 2)
            elif category in ("Electronics", "Luxury"):
                amount = round(random.uniform(50, 1200), 2)
            elif category in ("Subscription", "Digital"):
                amount = round(random.uniform(5, 35), 2)
            elif category == "Fuel":
                amount = round(random.uniform(40, 120), 2)
            elif category == "Cash Withdrawal":
                amount = round(random.uniform(50, 500), 2)
            else:
                amount = round(random.uniform(10, 400), 2)

        records.append({
            "transaction_id": f"TXN{str(i + 1).zfill(5)}",
            "account_id": account,
            "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
            "merchant": merchant,
            "category": category,
            "amount": amount,
            "location": location,
            "status": "completed",
            "home_location": home,
        })

    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)

    # Inject a few invalid rows so the cleaning step has something to remove
    noise = pd.DataFrame([
        {
            "transaction_id": "TXN_NOISE01",
            "account_id": "ACC00001",
            "timestamp": "2026-04-02 10:00:00",
            "merchant": "Test",
            "category": "Unknown",
            "amount": 99.00,
            "location": "Singapore",
            "status": "completed",
            "home_location": "Sydney, NSW",
        },
        {
            "transaction_id": "TXN_NOISE02",
            "account_id": "ACC00003",
            "timestamp": "2026-04-02 12:00:00",
            "merchant": "Coles",
            "category": "Groceries",
            "amount": -50,
            "location": "Sydney, NSW",
            "status": "completed",
            "home_location": "Sydney, NSW",
        },
        {
            "transaction_id": "TXN00001",
            "account_id": "ACC00002",
            "timestamp": "2026-04-02 11:00:00",
            "merchant": "Coles",
            "category": "Groceries",
            "amount": 45.00,
            "location": "Melbourne, VIC",
            "status": "completed",
            "home_location": "Melbourne, VIC",
        },
    ])
    df = pd.concat([df, noise], ignore_index=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(RAW_PATH, index=False)

    from data_pipeline import clean_transactions
    clean_df, report = clean_transactions(df)
    save_cleaned(clean_df)

    print(f"Generated {len(df)} raw rows → {report['output_rows']} Australian transactions after cleaning.")
    print(f"  Removed non-Australia: {report['dropped_non_australia']}, duplicates: {report['dropped_duplicates']}")
    return clean_df


if __name__ == "__main__":
    generate_transactions()
