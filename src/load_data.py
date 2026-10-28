"""Level 1: load the Agribalyse Synthèse CSV."""
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def load_agribalyse(filename: str = "agribalyse_synthese.csv") -> pd.DataFrame:
    path = RAW / filename
    # Agribalyse exports are usually comma separated UTF-8; adjust sep if needed.
    df = pd.read_csv(path)
    # The export contains thousands of fully empty trailing rows.
    df = df.dropna(how="all")
    return df


if __name__ == "__main__":
    df = load_agribalyse()
    print(df.shape)
    print(df.columns.tolist())
    print(df.head())
