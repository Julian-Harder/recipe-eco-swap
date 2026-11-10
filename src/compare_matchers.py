"""Compare embedding models and matcher settings on the DEV set (data/eval/dev_lines.csv).

The test set (ingredient_lines.csv) is deliberately not used here: settings are chosen on dev,
then evaluate.py runs the chosen one on test once. Run from the project root:
    python src/compare_matchers.py
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from evaluate import gold_codes, raw_predictions, score  # noqa: E402
from foods import load_foods, same_food  # noqa: E402
from match import AIMatcher  # noqa: E402
from parse import parse_line  # noqa: E402

DEV = Path(__file__).resolve().parents[1] / "data" / "eval" / "dev_lines.csv"
MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",   # small general model (our starting point)
    "sentence-transformers/all-mpnet-base-v2",  # larger general model
    "BAAI/bge-small-en-v1.5",                   # small retrieval model
    "jonny9f/food_embeddings",                  # mpnet fine-tuned on food names (Hugging Face)
]
LEXICAL_WEIGHTS = [0.0, 0.15, 0.3]
PROCESSED_PENALTIES = [0.0, 0.1]
THRESHOLDS = [round(0.30 + 0.05 * i, 2) for i in range(11)]  # 0.30 .. 0.80


def top5_recall(matcher, data, foods) -> float:
    rows = data[data["gold_codes"].notna()]
    hits = sum(any(same_food(c, g, foods) for c, _ in matcher.top_k(parse_line(line)["name"], 5)
                   for g in gold_codes(gold))
               for line, gold in zip(rows["line"], rows["gold_codes"]))
    return hits / len(rows)


def best_threshold(preds, data, foods) -> dict:
    """Threshold with the most correct lines; ties go to fewer wrong answers."""
    best = None
    for t in THRESHOLDS:
        res = score(preds, data, foods, t)
        wrong = int((~res["correct"] & ~res["abstained"]).sum())
        row = {"threshold": t, "correct": int(res["correct"].sum()), "wrong": wrong,
               "abstained": int(res["abstained"].sum())}
        if best is None or (row["correct"], -row["wrong"]) > (best["correct"], -best["wrong"]):
            best = row
    return best


if __name__ == "__main__":
    data = pd.read_csv(DEV, dtype=str)
    foods = load_foods()
    rows = []
    for model, clean in itertools.product(MODELS, [False, True]):
        matcher = AIMatcher(foods, model_name=model, clean_names=clean)
        for lex, pen in itertools.product(LEXICAL_WEIGHTS, PROCESSED_PENALTIES):
            matcher.lexical_weight, matcher.processed_penalty = lex, pen
            best = best_threshold(raw_predictions(matcher, data), data, foods)
            rows.append({"model": model.split("/")[-1], "clean": clean, "lexical": lex, "processed": pen,
                         **best, "top5": round(top5_recall(matcher, data, foods), 2)})
            print(rows[-1], flush=True)
    table = pd.DataFrame(rows).sort_values(["correct", "wrong"], ascending=[False, True])
    print(f"\nDev set: {len(data)} lines. Best settings first:\n")
    print(table.to_string(index=False))
