"""Turn matched ingredient lines into kg CO2e per ingredient and a recipe total."""
import pandas as pd


def score_recipe(parsed_matched_lines: list[dict], categories_df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Each line needs keys line, name, grams, category. Returns (per-ingredient table, total kg CO2e).

    Lines without grams, category or a CO2 value get kg_co2e = NaN and are left out of the total.
    """
    co2 = categories_df.set_index("category")["co2_kg_per_kg"]
    df = pd.DataFrame(parsed_matched_lines, columns=["line", "name", "grams", "category"])
    df["co2_kg_per_kg"] = df["category"].map(co2)
    df["kg_co2e"] = df["grams"].astype(float) / 1000 * df["co2_kg_per_kg"]
    total = float(df["kg_co2e"].sum(skipna=True))
    df["share"] = df["kg_co2e"] / total if total else float("nan")
    return df, total
