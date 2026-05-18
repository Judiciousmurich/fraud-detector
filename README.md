# FraudShield — Real-Time Payment Fraud Detector

**ICT503 Applied IT Project B · Group Assessment 3**

**Team:** Rumman Zaman (202471203) · Md. Zahidul Islam (202471200) · Kazi Maruf Ahmed (202471206) · Dewan Sariful Islam (202470995)

---

## Overview

FraudShield is a prototype fraud detection system for **Australian payment transactions**. It follows a four-step workflow:

1. **Data input** — Load sample AU payment data; review and clean records  
2. **Risk scoring** — Score each transaction (unusual amounts, frequency, account patterns)  
3. **Alert trigger** — Flag transactions above the risk threshold and log alerts automatically  
4. **Admin review** — Dashboard for flagged transactions with risk score, status, and log history  

All transaction locations are constrained to **Australian cities only** (Sydney, Melbourne, Brisbane, Perth, Adelaide, Canberra, Gold Coast, Newcastle, Hobart, Darwin).

---

## How to Run the Project

### First-time setup

Requires **Python 3.10+**.

```bash
cd fraud_detector

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

### Every time after that

```bash
cd fraud_detector
source venv/bin/activate
python3 app.py
```

### Open in browser

```
http://localhost:5000
```

On first run, sample data is generated automatically if `data/transactions.csv` does not exist. Use **↺ New Dataset** in the sidebar to regenerate data.

---

## Features

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Stats overview, charts, top flagged transactions |
| Transactions | `/transactions` | All transactions with risk scores, search & filter |
| Alerts | `/alerts` | Flagged transactions with admin review and log history |

---

## Fraud Scoring Logic

Each transaction is scored **0–100** based on:

| Indicator | Score Added |
|-----------|-------------|
| Amount ≥ $2,500 | +40 |
| Amount $1,000–$2,499 | +20 |
| Unusual amount for account (4× typical) | +15 |
| Cross-state activity within 4 hours | +30 |
| Atypical state for account | +10 |
| Transaction between 12am–5am AEST | +20 |
| High-risk merchant (Casino, Crypto, etc.) | +25 |
| Suspicious category (Gambling, Unknown, Transfer) | +15 |
| Rapid consecutive transactions (3+ in 30 min) | +20 |
| High daily transaction frequency (8+ per day) | +15 |

**Risk levels**

- **HIGH** — Score ≥ 60 (flagged; alert generated)  
- **MEDIUM** — Score 30–59  
- **LOW** — Score &lt; 30  

---

## Project Structure

```
fraud_detector/
├── app.py              # Flask web application
├── data_pipeline.py    # Load, clean, Australia-only filter
├── scorer.py           # Fraud scoring engine
├── alerts.py           # Automatic alerts & review log history
├── generate_data.py    # Sample AU transaction data generator
├── requirements.txt
├── data/               # CSV data, reviews, alert logs
├── templates/          # HTML pages
│   ├── base.html
│   ├── dashboard.html
│   ├── transactions.html
│   └── alerts.html
└── static/css/
    └── style.css
```

---

## Regenerating sample data (optional)

With the virtual environment activated:

```bash
python3 generate_data.py
```

Or click **↺ New Dataset** in the app sidebar.
