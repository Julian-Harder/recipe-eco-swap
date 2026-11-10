"""Score each matcher on data/eval/ingredient_lines.csv.

A prediction is correct if it is one of the line's gold foods or a near duplicate of one
(same sub-group and base name, calories within 10% per 100 g; see foods.same_food).
A line with no gold food is correct only if the matcher abstains (returns None).

Run from the project root:
    python src/evaluate.py            # keyword baseline vs AI matcher on the test set
    python src/evaluate.py --sweep    # also: AI results for a range of thresholds
    python src/evaluate.py --dev      # same on the dev set (the one settings are tuned on)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from foods import load_foods, same_food  # noqa: E402
from match import DEFAULT_MODEL, AIMatcher, KeywordMatcher  # noqa: E402
from parse import parse_line  # noqa: E402

EVAL = Path(__file__).resolve().parents[1] / "data" / "eval" / "ingredient_lines.csv"
DEV = EVAL.with_name("dev_lines.csv")
CO2_TOLERANCE = 0.20  # secondary metric: is the CO2 factor within 20% of the gold food's?


def gold_codes(cell) -> list[str]:
    return [c for c in str(cell).split("|") if c and c != "nan"]


def raw_predictions(matcher, data: pd.DataFrame) -> list[tuple[str | None, float]]:
    """(code, score) per line with no threshold applied, so thresholds can be compared cheaply."""
    saved = getattr(matcher, "threshold", None)
    if saved is not None:
        matcher.threshold = float("-inf")
    try:
        return [matcher.match_food(parse_line(line)["name"]) for line in data["line"]]
    finally:
        if saved is not None:
            matcher.threshold = saved


def score(preds, data: pd.DataFrame, foods: pd.DataFrame, threshold: float | None = None) -> pd.DataFrame:
    co2 = foods["co2_kg_per_kg"]
    rows = []
    for (code, sim), (_, r) in zip(preds, data.iterrows()):
        if threshold is not None and sim < threshold:
            code = None
        gold = gold_codes(r["gold_codes"])
        if gold:
            correct = any(same_food(code, g, foods) for g in gold)
            co2_ok = code in co2.index and any(abs(co2[code] - co2[g]) <= CO2_TOLERANCE * co2[g] for g in gold)
        else:
            correct = co2_ok = code is None
        rows.append({"line": r["line"], "kind": r["kind"], "gold_name": r["gold_name"], "pred": code,
                     "sim": sim, "correct": correct, "co2_ok": co2_ok, "abstained": code is None})
    return pd.DataFrame(rows)


def report(label: str, res: pd.DataFrame, foods: pd.DataFrame) -> None:
    wrong = int((~res["correct"] & ~res["abstained"]).sum())
    print(f"[{label}]")
    print(f"  correct: {res['correct'].sum()}/{len(res)} = {res['correct'].mean():.0%}"
          f" | CO2 factor within ±{CO2_TOLERANCE:.0%}: {res['co2_ok'].mean():.0%}"
          f" | abstained: {int(res['abstained'].sum())} | wrong answers: {wrong}")
    by_kind = res.groupby("kind", sort=False)["correct"].agg(["sum", "count"])
    print("  by kind: " + ", ".join(f"{k} {s}/{c}" for k, (s, c) in by_kind.iterrows()))
    for _, r in res[~res["correct"]].iterrows():
        got = "abstained" if pd.isna(r["pred"]) else repr(foods.at[r["pred"], "name"][:55])
        print(f"  miss [{r['kind']}] {r['line']!r}: expected {r['gold_name'][:45]!r}, got {got} (score {r['sim']:.2f})")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", action="store_true", help="show AI results for several thresholds")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="sentence-transformers model name")
    parser.add_argument("--dev", action="store_true", help="use the dev set instead of the test set")
    args = parser.parse_args()

    data = pd.read_csv(DEV if args.dev else EVAL, dtype=str)
    print(f"{'Dev' if args.dev else 'Test'} set: {len(data)} lines\n")
    foods = load_foods()

    keyword = KeywordMatcher()
    report("keyword baseline", score(raw_predictions(keyword, data), data, foods), foods)

    ai = AIMatcher(foods, model_name=args.model)
    preds = raw_predictions(ai, data)
    report(f"ai: {ai.model_name}, threshold {ai.threshold}", score(preds, data, foods, ai.threshold), foods)

    # If the UI offers the top 5 foods as a dropdown, how often is a correct one among them?
    with_gold = data[data["gold_codes"].notna()]
    in_top5 = sum(any(same_food(code, g, foods) for code, _ in ai.top_k(parse_line(line)["name"], 5)
                      for g in gold_codes(gold))
                  for line, gold in zip(with_gold["line"], with_gold["gold_codes"]))
    print(f"  correct food among the AI's top 5: {in_top5}/{len(with_gold)} = {in_top5 / len(with_gold):.0%}\n")

    if args.sweep:
        print("threshold  correct  abstained  wrong")
        for t in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
            res = score(preds, data, foods, t)
            wrong = int((~res["correct"] & ~res["abstained"]).sum())
            print(f"   {t:.2f}     {res['correct'].sum():>2}/{len(res)}      {int(res['abstained'].sum()):>2}      {wrong:>2}")
