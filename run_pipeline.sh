#!/usr/bin/env bash
# Runs the full Intelligent Fraud Risk & Decision Analytics Platform
# pipeline end-to-end, phase by phase, and regenerates the dashboard data.
set -euo pipefail
cd "$(dirname "$0")"

ROWS="${1:-100000}"
FRAUD_RATE="${2:-0.015}"

echo "==> Phase 1: Generating raw transaction data (${ROWS} rows, ${FRAUD_RATE} fraud rate)"
python3 src/etl/generate_raw_data.py --rows "$ROWS" --fraud-rate "$FRAUD_RATE" --out data/raw/raw_transactions.csv

echo "==> Phase 2: Data quality checks on raw data"
python3 src/data_quality/quality_checks.py --in data/raw/raw_transactions.csv --out data/quality/quality_report.json

echo "==> Phase 3: PySpark-equivalent ETL (clean + standardize)"
python3 src/etl/pandas_etl.py --in data/raw/raw_transactions.csv --out data/processed/clean_transactions.parquet

echo "==> Phase 4: Feature engineering"
python3 src/feature_engineering/build_features.py --in data/processed/clean_transactions.parquet --out data/features/features.parquet

echo "==> Phase 5: Train Logistic Regression + Random Forest, select best by ROC-AUC"
python3 src/ml/train_models.py --in data/features/features.parquet --model-out models/best_model.joblib --metrics-out outputs/model_metrics.json --importance-out outputs/feature_importance.csv

echo "==> Phase 6: Score transactions, generate risk levels + explainable alerts"
python3 src/ml/risk_scoring.py --in data/features/features.parquet --model models/best_model.joblib --out outputs/scored_transactions.parquet --alerts-out outputs/risk_alerts.json

echo "==> Phase 7: Materialize Foundry Ontology objects + links"
python3 src/ontology/ontology_export.py --scored outputs/scored_transactions.parquet --alerts outputs/risk_alerts.json --objects-out outputs/ontology_objects.json --links-out outputs/ontology_links.json --overview-out outputs/fraud_overview.json

echo "==> Phase 8: Build compact dashboard payload"
python3 src/ontology/build_dashboard_data.py --objects outputs/ontology_objects.json --overview outputs/fraud_overview.json --metrics outputs/model_metrics.json --quality data/quality/quality_report.json --out dashboard/dashboard_data.json

echo "==> Phase 9: Embed fresh data into dashboard/index.html"
python3 src/ontology/inject_dashboard_data.py --html dashboard/index.html --data dashboard/dashboard_data.json

echo ""
echo "Pipeline complete."
echo "  - Open dashboard/index.html directly in a browser to view the Workshop-style analytics console."
