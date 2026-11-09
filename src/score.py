"""Turn matched ingredient lines into kg CO2e per ingredient and a recipe total."""
import pandas as pd


def score_recipe(lines: list[dict]) -> tuple[pd.DataFrame, float]:
    """Each line needs grams and co2_kg_per_kg (kg CO2e per kg of food). Returns (table, total kg CO2e).

    Lines without grams or a CO2 factor get kg_co2e = NaN and are left out of the total;
    pipeline.py lists them so the user sees what was not counted.
    """
    df = pd.DataFrame(lines)
    df["kg_co2e"] = df["grams"].astype(float) / 1000 * df["co2_kg_per_kg"].astype(float)
    total = float(df["kg_co2e"].sum(skipna=True))
    df["share"] = df["kg_co2e"] / total if total else float("nan")
    return df, total
