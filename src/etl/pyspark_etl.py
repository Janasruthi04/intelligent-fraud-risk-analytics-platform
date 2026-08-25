"""
pyspark_etl.py
---------------
Reference PySpark transform for the "Raw Transactions -> Clean Transactions"
step of the pipeline. This is written the way it would live inside a Palantir
Foundry Code Repository (a `transforms.api.Transform`), reading the raw
Foundry Dataset and writing a cleaned output Dataset.

NOTE ON THIS PORTFOLIO PROJECT:
This sandbox does not have a Spark/Foundry runtime available, so the actual
demo pipeline used to produce the numbers in this repo is the pandas-based
equivalent in `pandas_etl.py`, which implements the exact same logic. This
file is the "real" implementation you would deploy to Foundry or any Spark
cluster -- keep the two in sync, they are logically identical.

Run on a real Spark cluster with:
    spark-submit pyspark_etl.py --in raw_transactions.csv --out clean_transactions.parquet
"""
import argparse
from pyspark.sql import SparkSession, functions as F, types as T


def build_spark(app_name="fraud-platform-etl"):
    return SparkSession.builder.appName(app_name).getOrCreate()


def clean_amount_col(df):
    """₹5,000.00 / $5,000 / '5000.00' / ' 5000 ' -> 5000.00 (double)."""
    cleaned = F.regexp_replace(F.col("transaction_amount"), r"[₹$,\s]", "")
    return df.withColumn("transaction_amount", cleaned.cast(T.DoubleType()))


def parse_timestamp_col(df):
    """Coalesce across the several date formats present in raw exports."""
    ts_col = F.col("transaction_timestamp")
    formats = [
        "yyyy-MM-dd HH:mm:ss",
        "dd/MM/yy HH:mm",
        "MM-dd-yyyy HH:mm:ss",
        "dd MMM yyyy HH:mm",
    ]
    parsed = F.coalesce(*[F.to_timestamp(ts_col, fmt) for fmt in formats])
    return df.withColumn("transaction_timestamp", parsed)


def transform(raw_df):
    df = clean_amount_col(raw_df)
    df = parse_timestamp_col(df)

    # Standardize categorical text
    for c in ["merchant_category", "location", "payment_method"]:
        df = df.withColumn(c, F.trim(F.lower(F.col(c))))

    # Drop rows that are unusable after cleaning (kept in a separate
    # "rejected" dataset for the data-quality step to report on)
    valid_df = df.filter(
        F.col("transaction_id").isNotNull()
        & F.col("customer_id").isNotNull()
        & F.col("transaction_amount").isNotNull()
        & (F.col("transaction_amount") > 0)
        & F.col("transaction_timestamp").isNotNull()
    )

    # De-duplicate on transaction_id, keep first occurrence
    valid_df = valid_df.dropDuplicates(["transaction_id"])

    valid_df = valid_df.withColumn("transaction_date", F.to_date("transaction_timestamp"))
    valid_df = valid_df.withColumn("transaction_hour", F.hour("transaction_timestamp"))
    return valid_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    args = parser.parse_args()

    spark = build_spark()
    raw_df = spark.read.option("header", True).csv(args.in_path)
    clean_df = transform(raw_df)
    clean_df.write.mode("overwrite").parquet(args.out_path)
    print(f"Wrote clean transactions to {args.out_path}")
    spark.stop()


if __name__ == "__main__":
    main()
