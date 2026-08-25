"""
build_dashboard_data.py
--------------------------
Creates a compact dashboard_data.json (a curated slice of the full ontology
export) sized for a browser-based Workshop-style dashboard: overview KPIs,
top risk alerts, a high-risk transaction table, and per-customer
investigation records for the riskiest customers only.
"""
import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects", default="../../outputs/ontology_objects.json")
    parser.add_argument("--overview", default="../../outputs/fraud_overview.json")
    parser.add_argument("--metrics", default="../../outputs/model_metrics.json")
    parser.add_argument("--quality", default="../../data/quality/quality_report.json")
    parser.add_argument("--out", default="../../dashboard/dashboard_data.json")
    args = parser.parse_args()

    with open(args.objects) as f:
        objects = json.load(f)
    with open(args.overview) as f:
        overview = json.load(f)
    with open(args.metrics) as f:
        metrics = json.load(f)
    with open(args.quality) as f:
        quality = json.load(f)

    customers_sorted = sorted(objects["Customer"], key=lambda c: c["risk_score"], reverse=True)
    top_customers = customers_sorted[:25]
    for c in top_customers:
        c["devices_used"] = c["devices_used"][:5]
        c["merchants_used"] = c["merchants_used"][:5]
        c["locations_used"] = c["locations_used"][:5]

    transactions_sorted = sorted(objects["Transaction"], key=lambda t: float(t["fraud_probability"]), reverse=True)
    top_transactions = transactions_sorted[:100]

    alerts_sorted = sorted(objects["RiskAlert"], key=lambda a: a["fraud_probability"], reverse=True)
    top_alerts = alerts_sorted[:50]

    payload = {
        "overview": overview,
        "model_metrics": {
            "logistic_regression": metrics["logistic_regression"],
            "random_forest": metrics["random_forest"],
            "best_model": metrics["best_model"],
        },
        "data_quality": quality,
        "top_customers": top_customers,
        "top_transactions": top_transactions,
        "top_alerts": top_alerts,
    }

    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote compact dashboard payload to {args.out}")


if __name__ == "__main__":
    main()
