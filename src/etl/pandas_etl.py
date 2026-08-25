"""
pandas_etl.py
--------------
Executable, logic-equivalent port of pyspark_etl.py, used to actually run the
pipeline in this sandbox (no Spark cluster available here). Same cleaning
rules, same de-duplication key, same validity filter -- just pandas instead
of Spark DataFrame API, so the numbers in this repo's outputs are real and
reproducible with `python pandas_etl.py`.
"""
import argparse
import re
import pandas as pd

AMOUNT_RE = re.compile(r"[₹$,\s]")

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%y %H:%M",
    "%m-%d-%Y %H:%M:%S",
    "%d %b %Y %H:%M",
]


def clean_amount(val):
    if pd.isna(val):
        return None
    s = AMOUNT_RE.sub("", str(val))
    try:
        return float(s)
    except ValueError:
        return None


def parse_timestamp(val):
    if pd.isna(val):
        return pd.NaT
    for fmt in DATE_FORMATS:
        try:
            return pd.to_datetime(val, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.NaT


def transform(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    df["transaction_amount"] = df["transaction_amount"].apply(clean_amount)
    df["transaction_timestamp"] = df["transaction_timestamp"].apply(parse_timestamp)

    for c in ["merchant_category", "location", "payment_method"]:
        df[c] = df[c].astype(str).str.strip().str.lower()

    valid_mask = (
        df["transaction_id"].notna()
        & df["customer_id"].notna()
        & df["transaction_amount"].notna()
        & (df["transaction_amount"] > 0)
        & df["transaction_timestamp"].notna()
    )
    valid_df = df.loc[valid_mask].copy()
    valid_df = valid_df.drop_duplicates(subset=["transaction_id"], keep="first")

    valid_df["transaction_date"] = valid_df["transaction_timestamp"].dt.date
    valid_df["transaction_hour"] = valid_df["transaction_timestamp"].dt.hour
    return valid_df.reset_index(drop=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default="../../data/raw/raw_transactions.csv")
    parser.add_argument("--out", dest="out_path", default="../../data/processed/clean_transactions.parquet")
    args = parser.parse_args()

    raw_df = pd.read_csv(args.in_path)
    clean_df = transform(raw_df)
    clean_df.to_parquet(args.out_path, index=False)

    print(f"Raw rows:   {len(raw_df):,}")
    print(f"Clean rows: {len(clean_df):,}")
    print(f"Dropped:    {len(raw_df) - len(clean_df):,}")
    print(f"Wrote clean transactions to {args.out_path}")
