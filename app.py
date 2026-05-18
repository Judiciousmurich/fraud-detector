from flask import Flask, render_template, jsonify, request, redirect, url_for
import pandas as pd
import os, json
from generate_data import generate_transactions
from data_pipeline import load_and_clean, CLEAN_PATH, AU_LOCATIONS
from scorer import score_transactions, RISK_THRESHOLD
from alerts import sync_alerts, get_logs_for_transaction, append_review_log

app = Flask(__name__)
DATA_PATH = CLEAN_PATH
REVIEW_PATH = os.path.join("data", "reviews.json")


def load_data():
    if not os.path.exists(DATA_PATH):
        generate_transactions()
    df, cleaning = load_and_clean(DATA_PATH)
    df = score_transactions(df)
    sync_alerts(df)

    reviews = load_reviews()
    df["review_status"] = df["transaction_id"].map(
        lambda tid: reviews.get(tid, "Pending")
    )
    df.attrs["cleaning"] = cleaning
    return df


def load_reviews():
    if os.path.exists(REVIEW_PATH):
        with open(REVIEW_PATH) as f:
            return json.load(f)
    return {}


def save_review(tid, status):
    reviews = load_reviews()
    reviews[tid] = status
    with open(REVIEW_PATH, "w") as f:
        json.dump(reviews, f)
    append_review_log(tid, status)


@app.route("/")
def dashboard():
    df = load_data()
    cleaning = df.attrs.get("cleaning", {})
    flagged = df[df["flagged"]]
    stats = {
        "total": len(df),
        "flagged": len(flagged),
        "high": len(df[df["risk_level"] == "HIGH"]),
        "medium": len(df[df["risk_level"] == "MEDIUM"]),
        "low": len(df[df["risk_level"] == "LOW"]),
        "pending": len(flagged[flagged["review_status"] == "Pending"]),
        "confirmed": len(flagged[flagged["review_status"] == "Confirmed Fraud"]),
        "cleared": len(flagged[flagged["review_status"] == "Cleared"]),
        "total_value": f"{df['amount'].sum():,.2f}",
        "flagged_value": f"{flagged['amount'].sum():,.2f}",
        "au_cities": len(AU_LOCATIONS),
        "risk_threshold": RISK_THRESHOLD,
        "cleaned_from": cleaning.get("input_rows", len(df)),
        "removed_non_au": cleaning.get("dropped_non_australia", 0),
    }

    cat_counts = df.groupby("category")["flagged"].sum().sort_values(ascending=False).head(6)
    chart_labels = cat_counts.index.tolist()
    chart_values = cat_counts.values.tolist()
    risk_dist = df["risk_level"].value_counts()
    recent_alerts = flagged.sort_values("risk_score", ascending=False).head(8).to_dict("records")

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_alerts=recent_alerts,
        chart_labels=json.dumps(chart_labels),
        chart_values=json.dumps(chart_values),
        risk_high=int(risk_dist.get("HIGH", 0)),
        risk_med=int(risk_dist.get("MEDIUM", 0)),
        risk_low=int(risk_dist.get("LOW", 0)),
    )


@app.route("/transactions")
def transactions():
    df = load_data()
    filter_level = request.args.get("risk", "ALL")
    search = request.args.get("search", "").strip().lower()

    if filter_level != "ALL":
        df = df[df["risk_level"] == filter_level]
    if search:
        df = df[
            df["transaction_id"].str.lower().str.contains(search)
            | df["account_id"].str.lower().str.contains(search)
            | df["merchant"].str.lower().str.contains(search)
            | df["location"].str.lower().str.contains(search)
        ]

    rows = df.sort_values("risk_score", ascending=False).to_dict("records")
    return render_template("transactions.html", rows=rows, filter_level=filter_level, search=search)


@app.route("/alerts")
def alerts():
    df = load_data()
    flagged = df[df["flagged"]].sort_values("risk_score", ascending=False)
    rows = []
    for _, row in flagged.iterrows():
        record = row.to_dict()
        record["log_history"] = get_logs_for_transaction(row["transaction_id"])
        rows.append(record)
    return render_template("alerts.html", rows=rows, risk_threshold=RISK_THRESHOLD)


@app.route("/review/<tid>", methods=["POST"])
def review(tid):
    status = request.form.get("status")
    save_review(tid, status)
    return redirect(request.referrer or url_for("alerts"))


@app.route("/api/stats")
def api_stats():
    df = load_data()
    return jsonify({
        "total": len(df),
        "flagged": int(df["flagged"].sum()),
        "high": int((df["risk_level"] == "HIGH").sum()),
        "scope": "Australia only",
    })


@app.route("/regenerate")
def regenerate():
    for path in [DATA_PATH, REVIEW_PATH, "data/alert_log.json", "data/review_log.json", "data/transactions_raw.csv"]:
        if os.path.exists(path):
            os.remove(path)
    generate_transactions()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_PATH):
        generate_transactions()
    app.run(debug=True, port=5000)
