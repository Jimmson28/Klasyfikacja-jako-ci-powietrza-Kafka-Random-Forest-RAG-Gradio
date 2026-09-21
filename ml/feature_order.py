from common import config

STAT_KEYS = ("mean", "std", "min", "max", "cv", "pct_change")

FEATURE_COLUMNS = ["missing_ratio", "n_present"] + [
    f"{pollutant}_{key}" for pollutant in config.PRIMARY_POLLUTANTS for key in STAT_KEYS
]

LABEL_COLUMN = "label"
