"""
build_features.py
-------------------
Builds the feature set used for fraud model training from the cleaned
transactions table. Grouped exactly as described in the project design doc:
  - Transaction features
  - Customer behavior features
  - Device behavior features
  - Location behavior features
"""
import argparse
import pandas as pd


def add_transaction_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["transaction_timestamp"] = pd.to_datetime(df["transaction_timestamp"])
    df = df.sort_values("transaction_timestamp")

    df["transaction_hour"] = df["transaction_timestamp"].dt.hour
    df["is_night_transaction"] = df["transaction_hour"].apply(lambda h: 1 if (h < 5 or h == 23) else 0)

    # transaction_frequency: rolling count of this customer's transactions
    # in the preceding 24h / 7d windows (computed below with customer feats)
    return df


def add_customer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.set_index("transaction_timestamp")

    def rolling_count(group, window):
        return group.rolling(window, closed="left").count()

    out_frames = []
    for cust_id, grp in df.groupby("customer_id", group_keys=False):
        grp = grp.sort_index()
        grp["transactions_last_24h"] = grp["transaction_id"].rolling("24h", closed="left").count().fillna(0)
        grp["transactions_last_7d"] = grp["transaction_id"].rolling("7D", closed="left").count().fillna(0)
        grp["avg_transaction_amount"] = grp["transaction_amount"].expanding().mean().shift(1)
        grp["max_transaction_amount"] = grp["transaction_amount"].expanding().max().shift(1)
        out_frames.append(grp)

    result = pd.concat(out_frames).reset_index()
    result["avg_transaction_amount"] = result["avg_transaction_amount"].fillna(result["transaction_amount"])
    result["max_transaction_amount"] = result["max_transaction_amount"].fillna(result["transaction_amount"])
    result["amount_vs_avg_ratio"] = (
        result["transaction_amount"] / result["avg_transaction_amount"].replace(0, 1)
    )
    return result


def add_device_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    device_customer_counts = df.groupby("device_id")["customer_id"].nunique().rename("number_of_customers_per_device")
    device_txn_counts = df.groupby("device_id")["transaction_id"].count().rename("device_transaction_frequency")
    df = df.merge(device_customer_counts, on="device_id", how="left")
    df = df.merge(device_txn_counts, on="device_id", how="left")
    return df


def add_location_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cust_location_counts = (
        df.groupby("customer_id")["location"].nunique().rename("number_of_locations_used")
    )
    df = df.merge(cust_location_counts, on="customer_id", how="left")

    # location_change_frequency: how often consecutive transactions for a
    # customer switch location (proxy for "traveling identity" fraud signal)
    df = df.sort_values(["customer_id", "transaction_timestamp"])
    df["prev_location"] = df.groupby("customer_id")["location"].shift(1)
    df["location_changed"] = (df["location"] != df["prev_location"]).astype(int)
    change_freq = df.groupby("customer_id")["location_changed"].mean().rename("location_change_frequency")
    df = df.drop(columns=["location_changed"]).merge(change_freq, on="customer_id", how="left")
    df = df.drop(columns=["prev_location"])
    return df


def build(df: pd.DataFrame) -> pd.DataFrame:
    df = add_transaction_features(df)
    df = add_customer_features(df)
    df = add_device_features(df)
    df = add_location_features(df)
    df = df.sort_values("transaction_timestamp").reset_index(drop=True)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default="../../data/processed/clean_transactions.parquet")
    parser.add_argument("--out", dest="out_path", default="../../data/features/features.parquet")
    args = parser.parse_args()

    clean_df = pd.read_parquet(args.in_path)
    feat_df = build(clean_df)
    feat_df.to_parquet(args.out_path, index=False)

    print(f"Built {feat_df.shape[1]} columns / {len(feat_df):,} rows of features")
    print(f"Wrote features to {args.out_path}")
