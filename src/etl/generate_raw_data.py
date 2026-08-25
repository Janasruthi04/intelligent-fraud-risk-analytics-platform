"""
generate_raw_data.py
---------------------
Generates a synthetic, IEEE-CIS-style financial transactions dataset for the
Intelligent Fraud Risk & Decision Analytics Platform.

In a real PwC / Palantir Foundry engagement this raw data would be ingested
directly into a Foundry Dataset (01_raw_transactions). Here we synthesize a
realistic transactions table -- with intentionally messy formatting (currency
symbols, inconsistent date formats, missing values, duplicates) -- so the
downstream PySpark ETL step has real cleaning work to do.

Usage:
    python generate_raw_data.py --rows 100000 --out ../../data/raw/raw_transactions.csv
"""
import argparse
import random
import string
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RNG_SEED = 42


def random_id(prefix, n, width=6):
    return [f"{prefix}{str(i).zfill(width)}" for i in n]


def messy_amount(x):
    """Return amount formatted inconsistently, like real-world raw exports."""
    style = random.random()
    if style < 0.4:
        return f"₹{x:,.2f}"
    elif style < 0.7:
        return f"{x:.2f}"
    elif style < 0.9:
        return f"${x:,.0f}"
    else:
        return f" {x} "  # stray whitespace


def messy_date(dt):
    """Return date formatted inconsistently."""
    style = random.random()
    if style < 0.4:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    elif style < 0.7:
        return dt.strftime("%d/%m/%y %H:%M")
    elif style < 0.9:
        return dt.strftime("%m-%d-%Y %H:%M:%S")
    else:
        return dt.strftime("%d %b %Y %H:%M")


def generate(n_rows: int, fraud_rate: float, seed: int = RNG_SEED) -> pd.DataFrame:
    random.seed(seed)
    np.random.seed(seed)

    n_customers = max(500, n_rows // 40)
    n_merchants = max(200, n_rows // 120)
    n_devices = max(400, n_rows // 60)

    customer_ids = [f"C{str(i).zfill(6)}" for i in range(n_customers)]
    merchant_ids = [f"M{str(i).zfill(5)}" for i in range(n_merchants)]
    device_ids = [f"D{str(i).zfill(6)}" for i in range(n_devices)]

    merchant_categories = [
        "grocery", "electronics", "travel", "restaurant", "fuel",
        "online_retail", "utilities", "entertainment", "healthcare", "jewelry",
    ]
    merchant_cat_map = {m: random.choice(merchant_categories) for m in merchant_ids}

    locations = [
        "Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata", "Hyderabad",
        "Pune", "Ahmedabad", "Kochi", "Jaipur", "Lucknow", "Chandigarh",
    ]
    payment_methods = ["credit_card", "debit_card", "upi", "net_banking", "wallet"]

    start_date = datetime(2025, 1, 1)
    n_fraud = int(n_rows * fraud_rate)
    is_fraud_flags = np.array([1] * n_fraud + [0] * (n_rows - n_fraud))
    np.random.shuffle(is_fraud_flags)

    rows = []
    for i in range(n_rows):
        cust = random.choice(customer_ids)
        merch = random.choice(merchant_ids)
        is_fraud = int(is_fraud_flags[i])

        # Fraudulent transactions *tend toward* higher amounts, odd hours,
        # and rarely-used devices -- but the signal deliberately overlaps
        # with normal behavior so the problem isn't trivially separable
        # (real fraud data is noisy; a model that hits 100% AUC is a red
        # flag of a synthetic/leaky dataset, not a good model).
        if is_fraud:
            # ~65% look like classic fraud, ~35% blend in with normal traffic
            if random.random() < 0.65:
                amount = round(np.random.lognormal(mean=7.6, sigma=1.1), 2)
                hour = random.choice([0, 1, 2, 3, 4, 22, 23] + list(range(6, 22)))
                device = random.choice(device_ids[-int(n_devices * 0.25):])
            else:
                amount = round(np.random.lognormal(mean=6.2, sigma=0.9), 2)
                hour = random.randint(0, 23)
                device = random.choice(device_ids)
            loc = random.choice(locations)
        else:
            amount = round(np.random.lognormal(mean=6.1, sigma=0.9), 2)
            # small chance of a legitimate late-night purchase
            hour = random.randint(0, 23) if random.random() < 0.08 else random.randint(6, 22)
            device = random.choice(device_ids)
            loc = random.choice(locations)

        day_offset = random.randint(0, 210)
        ts = start_date + timedelta(days=day_offset, hours=hour,
                                     minutes=random.randint(0, 59),
                                     seconds=random.randint(0, 59))

        rows.append({
            "transaction_id": f"TX{str(i).zfill(7)}",
            "customer_id": cust,
            "transaction_amount": messy_amount(amount),
            "transaction_timestamp": messy_date(ts),
            "merchant_id": merch,
            "merchant_category": merchant_cat_map[merch],
            "location": loc,
            "device_id": device,
            "payment_method": random.choice(payment_methods),
            "is_fraud": is_fraud,
        })

    df = pd.DataFrame(rows)

    # --- Inject realistic data-quality issues ---------------------------------
    # 1. Missing customer_id (simulates upstream ingestion gaps)
    missing_idx = df.sample(frac=0.004, random_state=seed).index
    df.loc[missing_idx, "customer_id"] = None

    # 2. Missing / null transaction_amount
    missing_amt_idx = df.sample(frac=0.002, random_state=seed + 1).index
    df.loc[missing_amt_idx, "transaction_amount"] = None

    # 3. Duplicate rows (simulates duplicate ingestion / retries)
    dup_rows = df.sample(frac=0.008, random_state=seed + 2)
    df = pd.concat([df, dup_rows], ignore_index=True)

    # 4. A few negative / zero amounts (bad data, should fail quality checks)
    bad_amt_idx = df.sample(frac=0.001, random_state=seed + 3).index
    df.loc[bad_amt_idx, "transaction_amount"] = "-50.00"

    # Shuffle final rows so duplicates aren't all at the tail
    df = df.sample(frac=1.0, random_state=seed + 4).reset_index(drop=True)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100000)
    parser.add_argument("--fraud-rate", type=float, default=0.012)
    parser.add_argument("--out", type=str, default="../../data/raw/raw_transactions.csv")
    args = parser.parse_args()

    df = generate(args.rows, args.fraud_rate)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df):,} raw transaction rows to {args.out}")
    print(f"Fraud rate (ground truth): {df['is_fraud'].mean():.4%}")
