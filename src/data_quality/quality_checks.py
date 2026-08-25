"""
quality_checks.py
------------------
Explicit, auditable data-quality checks run against the RAW dataset (not the
already-cleaned one) so the report reflects what actually came in from the
source system. Mirrors the kind of Data Quality "Health Check" you'd wire up
as expectations/checks on a Foundry Dataset.
"""
import argparse
import json
import re
import pandas as pd

AMOUNT_RE = re.compile(r"[₹$,\s]")


def _to_float(val):
    if pd.isna(val):
        return None
    try:
        return float(AMOUNT_RE.sub("", str(val)))
    except ValueError:
        return None


def run_checks(raw_df: pd.DataFrame) -> dict:
    total = len(raw_df)
    amounts = raw_df["transaction_amount"].apply(_to_float)

    check_null_txn_id = raw_df["transaction_id"].isna()
    check_missing_customer = raw_df["customer_id"].isna()
    check_bad_amount = amounts.isna() | (amounts <= 0)
    check_dupe_txn_id = raw_df.duplicated(subset=["transaction_id"], keep="first")

    invalid_mask = (
        check_null_txn_id
        | check_missing_customer
        | check_bad_amount
        | check_dupe_txn_id
    )

    valid = int((~invalid_mask).sum())
    invalid = int(invalid_mask.sum())
    duplicate_rate = float(check_dupe_txn_id.mean())

    report = {
        "total_records": total,
        "valid_records": valid,
        "invalid_records": invalid,
        "quality_score_pct": round(valid / total * 100, 2),
        "checks": {
            "transaction_id_not_null": {
                "description": "transaction_id must not be NULL",
                "failures": int(check_null_txn_id.sum()),
                "passed": bool(check_null_txn_id.sum() == 0),
            },
            "transaction_amount_positive": {
                "description": "transaction_amount must be > 0 and numeric",
                "failures": int(check_bad_amount.sum()),
                "passed": bool(check_bad_amount.sum() == 0),
            },
            "customer_id_present": {
                "description": "customer_id must exist (not NULL)",
                "failures": int(check_missing_customer.sum()),
                "passed": bool(check_missing_customer.sum() == 0),
            },
            "duplicate_transaction_rate": {
                "description": "duplicate transaction_id rate must be < 2%",
                "failures": int(check_dupe_txn_id.sum()),
                "rate_pct": round(duplicate_rate * 100, 3),
                "passed": bool(duplicate_rate < 0.02),
            },
        },
        "missing_customer_id_count": int(check_missing_customer.sum()),
        "duplicate_record_count": int(check_dupe_txn_id.sum()),
        "bad_amount_count": int(check_bad_amount.sum()),
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default="../../data/raw/raw_transactions.csv")
    parser.add_argument("--out", dest="out_path", default="../../data/quality/quality_report.json")
    args = parser.parse_args()

    raw_df = pd.read_csv(args.in_path)
    report = run_checks(raw_df)

    with open(args.out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    print(f"\nWrote quality report to {args.out_path}")
