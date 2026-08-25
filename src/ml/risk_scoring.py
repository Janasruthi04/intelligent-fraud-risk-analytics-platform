"""
risk_scoring.py
-----------------
Scores every transaction with the trained model, converts fraud_probability
into a business-friendly risk_level (LOW/MEDIUM/HIGH), and generates a
simple, explainable "contributing factors" breakdown for HIGH risk
transactions -- without requiring a heavyweight SHAP dependency (this uses a
transparent, rule-based deviation-from-normal explanation approach driven by
the same features the model saw; swap in true SHAP values if `shap` is
available in your environment).
"""
import argparse
import json
import joblib
import numpy as np
import pandas as pd

from train_models import NUMERIC_FEATURES, CATEGORICAL_FEATURES  # noqa: E402


def risk_level(p: float) -> str:
    if p < 0.30:
        return "LOW"
    elif p < 0.70:
        return "MEDIUM"
    return "HIGH"


FACTOR_RULES = [
    ("amount_vs_avg_ratio", 2.0, "Transaction amount far above this customer's usual average"),
    ("is_night_transaction", 0.5, "Transaction occurred late at night / early morning"),
    ("number_of_customers_per_device", 3, "Device has been used by an unusually high number of customers"),
    ("transactions_last_24h", 5, "High transaction frequency in the last 24 hours"),
    ("location_change_frequency", 0.5, "Customer's location has been changing frequently"),
    ("number_of_locations_used", 4, "Customer has used an unusually high number of locations"),
]


def contributing_factors(row: pd.Series) -> list:
    factors = []
    for col, threshold, label in FACTOR_RULES:
        val = row.get(col)
        if val is not None and not pd.isna(val) and val >= threshold:
            factors.append(label)
    if not factors:
        factors.append("Model flagged an unusual combination of transaction attributes")
    return factors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default="../../data/features/features.parquet")
    parser.add_argument("--model", dest="model_path", default="../../models/best_model.joblib")
    parser.add_argument("--out", dest="out_path", default="../../outputs/scored_transactions.parquet")
    parser.add_argument("--alerts-out", dest="alerts_out", default="../../outputs/risk_alerts.json")
    args = parser.parse_args()

    df = pd.read_parquet(args.in_path)
    df = df.dropna(subset=NUMERIC_FEATURES + CATEGORICAL_FEATURES).reset_index(drop=True)

    model = joblib.load(args.model_path)
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    proba = model.predict_proba(X)[:, 1]

    df["fraud_probability"] = np.round(proba, 4)
    df["risk_level"] = df["fraud_probability"].apply(risk_level)

    df.to_parquet(args.out_path, index=False)

    high_risk = df[df["risk_level"] == "HIGH"].sort_values("fraud_probability", ascending=False)
    alerts = []
    for i, (_, row) in enumerate(high_risk.head(500).iterrows()):
        alerts.append({
            "alert_id": f"AL{str(i).zfill(6)}",
            "transaction_id": row["transaction_id"],
            "customer_id": row["customer_id"],
            "merchant_id": row["merchant_id"],
            "device_id": row["device_id"],
            "amount": round(float(row["transaction_amount"]), 2),
            "fraud_probability": float(row["fraud_probability"]),
            "risk_level": row["risk_level"],
            "contributing_factors": contributing_factors(row),
            "status": "OPEN",
            "alert_type": "FRAUD_RISK",
        })

    with open(args.alerts_out, "w") as f:
        json.dump(alerts, f, indent=2)

    summary = df["risk_level"].value_counts().to_dict()
    print("Risk level distribution:", summary)
    print(f"Scored transactions written to {args.out_path}")
    print(f"{len(alerts)} risk alerts written to {args.alerts_out}")


if __name__ == "__main__":
    main()
