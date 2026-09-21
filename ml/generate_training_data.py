from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import config
from common.features import compute_features
from common.rules import classify_window
from common.simulator import ScenarioIntent, generate_scenario
from ml.feature_order import FEATURE_COLUMNS, LABEL_COLUMN

DATA_DIR = ROOT / "ml" / "data"
OUTPUT_PATH = DATA_DIR / "training_data.csv"

ALL_INTENTS = list(ScenarioIntent)


def generate_dataset(
    target_per_class: int, max_iterations: int, seed: int
) -> tuple[list[dict], Counter]:
    rng = random.Random(seed)
    counts: Counter = Counter()
    rows: list[dict] = []

    iterations = 0
    while iterations < max_iterations and any(
        counts[label] < target_per_class for label in config.ALL_LABELS
    ):
        iterations += 1
        intent = rng.choice(ALL_INTENTS)
        n = rng.randint(config.MIN_SAMPLES_IN_WINDOW, config.WINDOW_SIZE)
        measurements = generate_scenario(intent, rng, n=n, station_id="train-sim")
        features = compute_features(measurements)
        label, reasons = classify_window(features)

        if counts[label] >= target_per_class:
            continue

        vector = features.flat_vector(config.PRIMARY_POLLUTANTS)
        row = dict(zip(FEATURE_COLUMNS, vector))
        row[LABEL_COLUMN] = label
        row["intent"] = intent.value
        row["reasons"] = " | ".join(reasons)
        rows.append(row)
        counts[label] += 1

    return rows, counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-per-class", type=int, default=300)
    parser.add_argument("--max-iterations", type=int, default=200_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows, counts = generate_dataset(args.target_per_class, args.max_iterations, args.seed)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = FEATURE_COLUMNS + [LABEL_COLUMN, "intent", "reasons"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Zapisano {len(rows)} przykładów do {OUTPUT_PATH}")
    print("Rozkład klas:")
    for label in config.ALL_LABELS:
        print(f"  {label:35s} {counts[label]}")
    missing = [label for label in config.ALL_LABELS if counts[label] < args.target_per_class]
    if missing:
        print(
            "UWAGA: nie osiągnięto zadanej liczby przykładów dla klas: "
            f"{missing}. Zwiększ --max-iterations lub dostosuj common/simulator.py."
        )


if __name__ == "__main__":
    main()
