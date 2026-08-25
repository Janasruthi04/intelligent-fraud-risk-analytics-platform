"""
train_models.py
-----------------
Trains and compares two fraud models (Logistic Regression, Random Forest),
evaluates with metrics appropriate for an imbalanced classification problem
(precision/recall/F1/ROC-AUC, not just accuracy), and saves the best model
plus feature importances for the explainability step.
"""
import argparse
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
)

NUMERIC_FEATURES = [
    "transaction_amount", "transaction_hour", "is_night_transaction",
    "transactions_last_24h", "transactions_last_7d", "avg_transaction_amount",
    "max_transaction_amount", "amount_vs_avg_ratio",
    "number_of_customers_per_device", "device_transaction_frequency",
    "number_of_locations_used", "location_change_frequency",
]
CATEGORICAL_FEATURES = ["merchant_category", "payment_method"]
TARGET = "is_fraud"


def build_preprocessor():
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )


def evaluate(model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }


def get_feature_importance(pipeline, model_name) -> pd.DataFrame:
    preproc = pipeline.named_steps["preprocess"]
    feature_names = list(NUMERIC_FEATURES) + list(
        preproc.named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES)
    )
    clf = pipeline.named_steps["model"]
    if hasattr(clf, "feature_importances_"):
        importances = clf.feature_importances_
    elif hasattr(clf, "coef_"):
        importances = np.abs(clf.coef_[0])
    else:
        return pd.DataFrame()

    fi = pd.DataFrame({"feature": feature_names, "importance": importances})
    fi = fi.sort_values("importance", ascending=False).reset_index(drop=True)
    fi["model"] = model_name
    return fi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default="../../data/features/features.parquet")
    parser.add_argument("--model-out", dest="model_out", default="../../models/best_model.joblib")
    parser.add_argument("--metrics-out", dest="metrics_out", default="../../outputs/model_metrics.json")
    parser.add_argument("--importance-out", dest="importance_out", default="../../outputs/feature_importance.csv")
    args = parser.parse_args()

    df = pd.read_parquet(args.in_path)
    df = df.dropna(subset=NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET])

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    results = {}
    importances = []
    fitted_pipelines = {}

    # ---- Model 1: Logistic Regression -----------------------------------
    lr_pipeline = Pipeline([
        ("preprocess", build_preprocessor()),
        ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])
    lr_pipeline.fit(X_train, y_train)
    results["logistic_regression"] = evaluate(lr_pipeline, X_test, y_test)
    importances.append(get_feature_importance(lr_pipeline, "logistic_regression"))
    fitted_pipelines["logistic_regression"] = lr_pipeline

    # ---- Model 2: Random Forest ------------------------------------------
    rf_pipeline = Pipeline([
        ("preprocess", build_preprocessor()),
        ("model", RandomForestClassifier(
            n_estimators=300, max_depth=12, min_samples_leaf=5,
            class_weight="balanced_subsample", random_state=42, n_jobs=-1,
        )),
    ])
    rf_pipeline.fit(X_train, y_train)
    results["random_forest"] = evaluate(rf_pipeline, X_test, y_test)
    importances.append(get_feature_importance(rf_pipeline, "random_forest"))
    fitted_pipelines["random_forest"] = rf_pipeline

    # ---- Select best model by ROC-AUC (best metric for imbalanced fraud) --
    best_name = max(results, key=lambda k: results[k]["roc_auc"])
    best_pipeline = fitted_pipelines[best_name]
    results["best_model"] = best_name

    joblib.dump(best_pipeline, args.model_out)
    with open(args.metrics_out, "w") as f:
        json.dump(results, f, indent=2)

    importance_df = pd.concat(importances, ignore_index=True)
    importance_df.to_csv(args.importance_out, index=False)

    print(json.dumps(results, indent=2))
    print(f"\nBest model: {best_name} -> saved to {args.model_out}")
    print(f"Feature importances written to {args.importance_out}")


if __name__ == "__main__":
    main()
