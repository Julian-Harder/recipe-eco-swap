"""Score each matcher against data/eval/ingredient_lines.csv.

Run from the project root: python src/evaluate.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from match import AIMatcher, KeywordMatcher, load_categories  # noqa: E402
from parse import parse_line  # noqa: E402

EVAL = Path(__file__).resolve().parents[1] / "data" / "eval" / "ingredient_lines.csv"


def evaluate(matcher, data: pd.DataFrame) -> None:
    misses, correct = [], 0
    for _, row in data.iterrows():
        try:
            pred = matcher.match(parse_line(row["line"])["name"])
        except NotImplementedError:
            print(f"[{matcher.name}] skipped: not implemented\n")
            return
        if pred == row["gold_category"]:
            correct += 1
        else:
            misses.append((row["line"], row["gold_category"], pred))
    print(f"[{matcher.name}] accuracy: {correct}/{len(data)} = {correct / len(data):.0%}")
    for line, gold, pred in misses:
        print(f"  miss: {line!r}: expected {gold!r}, got {pred!r}")
    print()


if __name__ == "__main__":
    data = pd.read_csv(EVAL)
    categories = load_categories()
    for matcher in (KeywordMatcher(categories), AIMatcher(categories)):
        evaluate(matcher, data)
