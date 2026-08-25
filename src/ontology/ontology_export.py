"""
ontology_export.py
---------------------
Materializes Customer / Transaction / Merchant / Device / RiskAlert object
instances (and the links between them) from the scored transactions +
risk alerts produced earlier in the pipeline, then exports:
  - outputs/ontology_objects.json   (object instances, keyed by type)
  - outputs/ontology_links.json     (relationship edges)
  - outputs/fraud_overview.json     (KPIs for Workshop Page 1)

This is the artifact the `dashboard/` Workshop-style app reads from.
"""
import argparse
import json
import pandas as pd


def build_ontology(scored_path: str, alerts_path: str):
    df = pd.read_parquet(scored_path)
    with open(alerts_path) as f:
        alerts = json.load(f)

    # --- Customer objects ---------------------------------------------
    customers = (
        df.groupby("customer_id")
        .agg(
            total_transactions=("transaction_id", "count"),
            avg_amount=("transaction_amount", "mean"),
            max_amount=("transaction_amount", "max"),
            avg_fraud_probability=("fraud_probability", "mean"),
            devices_used=("device_id", lambda s: sorted(set(s))),
            merchants_used=("merchant_id", lambda s: sorted(set(s))),
            locations_used=("location", lambda s: sorted(set(s))),
            high_risk_txn_count=("risk_level", lambda s: int((s == "HIGH").sum())),
        )
        .reset_index()
    )
    customers["risk_score"] = (customers["avg_fraud_probability"] * 100).round(2)
    customer_objs = customers.to_dict(orient="records")

    # --- Merchant objects -----------------------------------------------
    # merchant_category is fixed per merchant; location is where the
    # transaction occurred (customers transact with a merchant chain from
    # many cities), so we take the merchant's most common transaction
    # location rather than group by every location combo.
    merchants = (
        df.groupby("merchant_id")
        .agg(
            merchant_category=("merchant_category", "first"),
            primary_location=("location", lambda s: s.value_counts().idxmax()),
            total_transactions=("transaction_id", "count"),
            fraud_flagged=("risk_level", lambda s: int((s == "HIGH").sum())),
        )
        .reset_index()
    )
    merchant_objs = merchants.to_dict(orient="records")

    # --- Device objects ---------------------------------------------------
    devices = (
        df.groupby("device_id")
        .agg(unique_customers=("customer_id", "nunique"),
             total_transactions=("transaction_id", "count"),
             high_risk_txns=("risk_level", lambda s: int((s == "HIGH").sum())))
        .reset_index()
    )
    device_objs = devices.to_dict(orient="records")

    # --- Transaction objects (cap for export size) -----------------------
    txn_cols = [
        "transaction_id", "customer_id", "merchant_id", "device_id",
        "transaction_amount", "transaction_timestamp", "merchant_category",
        "location", "payment_method", "fraud_probability", "risk_level",
    ]
    high_risk_txns = df[df["risk_level"] == "HIGH"].sort_values(
        "fraud_probability", ascending=False
    ).head(500)
    transaction_objs = high_risk_txns[txn_cols].astype(str).to_dict(orient="records")

    objects = {
        "Customer": customer_objs,
        "Merchant": merchant_objs,
        "Device": device_objs,
        "Transaction": transaction_objs,
        "RiskAlert": alerts,
    }

    # --- Links -------------------------------------------------------------
    links = []
    for t in transaction_objs:
        links.append({"type": "Customer_makes_Transaction", "from": t["customer_id"], "to": t["transaction_id"]})
        links.append({"type": "Transaction_at_Merchant", "from": t["transaction_id"], "to": t["merchant_id"]})
        links.append({"type": "Transaction_from_Device", "from": t["transaction_id"], "to": t["device_id"]})
    for a in alerts:
        links.append({"type": "Transaction_generates_RiskAlert", "from": a["transaction_id"], "to": a["alert_id"]})

    # --- Fraud overview KPIs (Workshop Page 1) -----------------------------
    overview = {
        "total_transactions": int(len(df)),
        "fraud_transactions": int(df["risk_level"].isin(["HIGH"]).sum()),
        "fraud_rate_pct": round(float((df["risk_level"] == "HIGH").mean() * 100), 3),
        "high_risk_transactions": int((df["risk_level"] == "HIGH").sum()),
        "medium_risk_transactions": int((df["risk_level"] == "MEDIUM").sum()),
        "low_risk_transactions": int((df["risk_level"] == "LOW").sum()),
        "average_transaction_amount": round(float(df["transaction_amount"].mean()), 2),
        "total_risk_alerts": len(alerts),
    }

    return objects, links, overview


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scored", default="../../outputs/scored_transactions.parquet")
    parser.add_argument("--alerts", default="../../outputs/risk_alerts.json")
    parser.add_argument("--objects-out", default="../../outputs/ontology_objects.json")
    parser.add_argument("--links-out", default="../../outputs/ontology_links.json")
    parser.add_argument("--overview-out", default="../../outputs/fraud_overview.json")
    args = parser.parse_args()

    objects, links, overview = build_ontology(args.scored, args.alerts)

    with open(args.objects_out, "w") as f:
        json.dump(objects, f, indent=2, default=str)
    with open(args.links_out, "w") as f:
        json.dump(links, f, indent=2, default=str)
    with open(args.overview_out, "w") as f:
        json.dump(overview, f, indent=2, default=str)

    print(f"Objects: Customer={len(objects['Customer'])}, Merchant={len(objects['Merchant'])}, "
          f"Device={len(objects['Device'])}, Transaction={len(objects['Transaction'])}, "
          f"RiskAlert={len(objects['RiskAlert'])}")
    print(f"Links: {len(links)}")
    print("Overview:", json.dumps(overview, indent=2))
