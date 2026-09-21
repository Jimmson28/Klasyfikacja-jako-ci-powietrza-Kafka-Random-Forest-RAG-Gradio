from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from ml.feature_order import FEATURE_COLUMNS, LABEL_COLUMN

DATA_PATH = ROOT / "ml" / "data" / "training_data.csv"
MODEL_DIR = ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "random_forest.joblib"
METADATA_PATH = MODEL_DIR / "model_metadata.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    if not DATA_PATH.exists():
        raise SystemExit(
            f"Brak {DATA_PATH}. Najpierw uruchom: python -m ml.generate_training_data"
        )

    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLUMNS].values
    y = df[LABEL_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.random_state, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        random_state=args.random_state,
        class_weight="balanced",
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    report_text = classification_report(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=sorted(y.unique())).tolist()

    print(report_text)
    print("Macierz pomyłek (wiersze = prawdziwa klasa, kolumny = predykcja):")
    print(sorted(y.unique()))
    for row in cm:
        print(row)

    importances = dict(zip(FEATURE_COLUMNS, clf.feature_importances_.tolist()))
    print("\nWażność cech:")
    for name, imp in sorted(importances.items(), key=lambda kv: -kv[1]):
        print(f"  {name:20s} {imp:.4f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)

    metadata = {
        "feature_columns": FEATURE_COLUMNS,
        "label_column": LABEL_COLUMN,
        "classes": sorted(y.unique().tolist()),
        "n_estimators": args.n_estimators,
        "max_depth": args.max_depth,
        "test_accuracy": report["accuracy"],
        "classification_report": report,
        "feature_importances": importances,
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nZapisano model: {MODEL_PATH}")
    print(f"Zapisano metadane: {METADATA_PATH}")
    print(f"Dokładność (test): {report['accuracy']:.3f}")


if __name__ == "__main__":
    main()
