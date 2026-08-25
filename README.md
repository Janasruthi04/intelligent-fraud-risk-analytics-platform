# Intelligent Fraud Risk & Decision Analytics Platform

**Palantir Foundry (Ontology pattern) · PySpark · Python · SQL-style transforms · Machine Learning · Data Quality · Explainable AI**

An end-to-end fraud analytics platform: raw transactions → PySpark-style ETL →
explicit data-quality validation → feature engineering → ML fraud scoring →
a Foundry-style **Ontology** (Customer / Transaction / Merchant / Device / Risk Alert)
→ a Workshop-style analytics console for investigation and business decisions.

This project was built as a portfolio piece targeting **Palantir Foundry Data &
Analytics** roles (e.g. PwC Associate – Palantir D&A Advisory), where the goal
isn't a generic dashboard, but a single project that demonstrates data
engineering, data quality discipline, applied ML, and Foundry's Ontology /
entity-investigation pattern together.

> **Honesty note:** this sandbox does not have a live Palantir Foundry
> workspace or Spark cluster attached. Every phase below was actually
> executed end-to-end using PySpark-equivalent logic (pandas) and a real
> synthetic dataset — nothing here is a mockup of numbers. The Foundry-specific
> pieces (Ontology object types, Actions, Workshop) are implemented as
> schema-as-code / a Workshop-style web console that reproduces the pattern
> faithfully, with clear notes on what would change when deployed to a real
> Foundry instance. See [`docs/FOUNDRY_MAPPING.md`](docs/FOUNDRY_MAPPING.md).

---

## Architecture

```
                    RAW DATA (synthetic, IEEE-CIS-style)
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Data Ingestion      │   src/etl/generate_raw_data.py
                    │  (Foundry Dataset)   │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │  PySpark ETL         │   src/etl/pyspark_etl.py (prod)
                    │  Cleaning /          │   src/etl/pandas_etl.py  (ran here)
                    │  Transformation      │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │  Data Quality        │   src/data_quality/quality_checks.py
                    │  Validation          │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │  Feature Engineering │   src/feature_engineering/build_features.py
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │  ML Fraud Prediction │   src/ml/train_models.py
                    │  (Logistic + RF)     │   src/ml/risk_scoring.py
                    └──────────┬──────────┘
                               ▼
              ┌───────────────────────────────────┐
              │        FOUNDRY ONTOLOGY            │  src/ontology/ontology_schema.py
              │                                     │  src/ontology/ontology_export.py
              │  Customer · Transaction · Merchant  │
              │  Device · Risk Alert                │
              └───────────────┬─────────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │  Workshop-style      │   dashboard/index.html
                    │  Analytics Console   │   dashboard/app.js
                    └──────────┬──────────┘
                               ▼
                       BUSINESS DECISION
```

## What this demonstrates

| Requirement                | Where |
|---|---|
| Python / SQL-style transforms | `src/etl`, `src/feature_engineering` |
| PySpark | `src/etl/pyspark_etl.py` (production reference) |
| ETL / Data Pipeline | `run_pipeline.sh`, `src/etl/` |
| Data Quality | `src/data_quality/quality_checks.py` |
| Feature Engineering | `src/feature_engineering/build_features.py` |
| Machine Learning (scikit-learn) | `src/ml/train_models.py` |
| Model evaluation (precision/recall/F1/ROC-AUC) | `outputs/model_metrics.json` |
| Explainable AI | `src/ml/risk_scoring.py` (contributing factors per alert) |
| Palantir Foundry Ontology (object types + relationships) | `src/ontology/ontology_schema.py` |
| Foundry Actions (Review / Investigate / Escalate) | `src/ontology/ontology_schema.py` |
| Workshop-style analytics / business decisioning | `dashboard/index.html` |
| Data lineage / auditability | `docs/FOUNDRY_MAPPING.md`, `run_pipeline.sh` |

## Quickstart

```bash
pip install -r requirements.txt
./run_pipeline.sh              # defaults: 100,000 rows, 1.5% fraud rate
./run_pipeline.sh 250000 0.02  # or customize row count / fraud rate

# then open dashboard/index.html directly in a browser
```

`run_pipeline.sh` runs every phase in order and regenerates everything —
raw data, the cleaned dataset, the quality report, engineered features, both
trained models, risk-scored transactions, the Ontology export, and the
dashboard — so the whole repo is reproducible from one command.

## Repository layout

```
fraud-platform/
├── src/
│   ├── etl/                 # Phase 1-2: ingestion + PySpark/pandas ETL
│   ├── data_quality/        # Phase 3: explicit validation checks
│   ├── feature_engineering/ # Phase 4: transaction/customer/device/location features
│   ├── ml/                  # Phase 5-6: model training + risk scoring + explainability
│   └── ontology/            # Phase 7: Foundry Ontology schema, export, dashboard data
├── data/
│   ├── raw/                 # synthetic raw transactions (messy, like a real export)
│   ├── processed/           # cleaned transactions
│   ├── quality/             # data quality report (JSON)
│   └── features/            # engineered feature table
├── models/                  # trained model artifact (best of LR / RF by ROC-AUC)
├── outputs/                 # metrics, feature importances, scored transactions,
│                             # risk alerts, ontology objects/links
├── dashboard/                # Workshop-style analytics console (self-contained HTML/JS)
├── docs/                     # Foundry mapping notes + resume guidance
├── run_pipeline.sh
└── requirements.txt
```

## The dataset

A synthetic, IEEE-CIS-style transactions dataset (`src/etl/generate_raw_data.py`)
with the fields: `transaction_id, customer_id, transaction_amount,
transaction_timestamp, merchant_id, merchant_category, location, device_id,
payment_method, is_fraud`.

It's intentionally **messy on purpose** — inconsistent currency formatting
(`₹5,000.00` / `$5,000` / `5000.00`), inconsistent date formats, ~0.4% missing
customer IDs, ~0.8% duplicate rows, and a handful of invalid (negative) amounts
— so the ETL and Data Quality phases have real work to do, and the quality
report reflects genuine validation rather than a rubber stamp. Fraud labels
are generated with **overlapping, noisy signal** (not a clean separation) so
the model comparison tells an honest story instead of a suspicious 100% AUC.

## Data quality (Phase 3)

Explicit, auditable checks run against the raw data before cleaning:

```json
{
  "total_records": 100800,
  "valid_records": 99301,
  "invalid_records": 1499,
  "quality_score_pct": 98.51,
  "checks": {
    "transaction_id_not_null": {"failures": 0, "passed": true},
    "transaction_amount_positive": {"failures": 303, "passed": false},
    "customer_id_present": {"failures": 403, "passed": false},
    "duplicate_transaction_rate": {"failures": 800, "rate_pct": 0.794, "passed": true}
  }
}
```

(Exact numbers vary slightly per run since the dataset is regenerated with a
fixed seed but is fully reproducible via `run_pipeline.sh`.)

## Machine Learning (Phase 5-6)

Two models are trained and compared — **Logistic Regression** (class-weighted
baseline) and **Random Forest** (300 trees, balanced-subsample) — and the
best is selected by **ROC-AUC**, not accuracy:

> Fraud datasets are heavily imbalanced (~1.5% positive class here), so a
> model that predicts "not fraud" every time would still score ~98%
> accuracy while catching zero fraud. Precision, recall, F1-score, and
> ROC-AUC give a far more honest picture of model quality than accuracy
> alone — this is deliberately surfaced on the dashboard's Overview page.

`fraud_probability` is converted into a business-friendly `risk_level`:

```
0.00 – 0.30 → LOW
0.30 – 0.70 → MEDIUM
0.70 – 1.00 → HIGH
```

Every HIGH-risk transaction gets a **Risk Alert** with plain-language
**contributing factors** (transaction far above the customer's usual average,
device shared across unusually many customers, frequent location changes,
etc.) — the explainability story: *"I didn't want the model to only output a
probability; I wanted the analyst to understand why the transaction was
flagged."*

## Foundry Ontology (Phase 7)

Object types and relationships, defined as schema-as-code in
`src/ontology/ontology_schema.py` and materialized into real instances by
`src/ontology/ontology_export.py`:

```
Customer  --makes-->      Transaction
Transaction --at-->       Merchant
Transaction --from-->     Device
Transaction --generates--> Risk Alert
```

Plus three Ontology **Actions** (`ReviewTransaction`,
`MarkAlertAsInvestigated`, `EscalateHighRiskTransaction`) that model the
analyst workflow as state transitions on a `RiskAlert` object — exactly the
shape these would take as Foundry Action Types.

## Workshop-style analytics console (Phase 8)

`dashboard/index.html` — a single self-contained file (data is embedded, so
it works by double-clicking, no server needed) with four pages that mirror a
real Foundry Workshop application:

1. **Fraud Overview** — KPIs, risk distribution, model comparison, data
   quality health check.
2. **High-Risk Transactions** — searchable, sortable ledger.
3. **Customer Investigation** — select a customer, see transaction history,
   devices, merchants, locations, and risk score.
4. **Transaction Investigation** — an entity graph (Customer → Device →
   Transaction → Merchant → Risk Alert) plus the explainable contributing
   factors for that alert.

## What to put on your resume

Only after you've actually run this, understood every phase, and could
defend it in an interview:

> **Intelligent Fraud Risk & Decision Analytics Platform**
> *Palantir Foundry (Ontology) · PySpark · Python · SQL · Machine Learning*
> - Built an end-to-end data pipeline (PySpark-based ETL, automated data-quality
>   validation, feature engineering) processing 100K+ synthetic financial
>   transactions.
> - Trained and compared Logistic Regression and Random Forest fraud models,
>   selecting by ROC-AUC and evaluating with precision, recall, and F1-score
>   given severe class imbalance.
> - Designed a Foundry-style Ontology connecting Customers, Transactions,
>   Merchants, Devices, and Risk Alerts to support entity-level fraud
>   investigation.
> - Built a Workshop-style analytics console for monitoring high-risk
>   transactions, customer risk profiles, and explainable model alerts.

**What not to claim:** avoid "Expert in Palantir Foundry" or a specific
years-of-experience figure. Say **"Palantir Foundry — hands-on project
experience"** and be ready to walk through exactly what you built versus what
you approximated outside a live Foundry instance (see
[`docs/FOUNDRY_MAPPING.md`](docs/FOUNDRY_MAPPING.md)) — that honesty is a
stronger interview signal than overclaiming.

## Next steps if you want to go further

- Get access to a real Foundry instance (Palantir Foundry for Builders /
  Academy) and port `ontology_schema.py`'s object types directly into a live
  Ontology Manager, and `pyspark_etl.py` into a Code Repository transform.
- Swap the rule-based `contributing_factors()` in `risk_scoring.py` for real
  SHAP values (`pip install shap`) for formal feature-attribution explanations.
- Replace the synthetic dataset with the real IEEE-CIS Fraud Detection
  dataset (Kaggle) for a higher-stakes portfolio story, keeping the same
  pipeline.
