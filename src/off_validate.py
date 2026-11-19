"""External validation with Open Food Facts: does our matcher agree with OFF's own Agribalyse link?

Open Food Facts (OFF) contributors link many products to an Agribalyse food (that is how OFF computes the
Eco-Score). Those links were made by other people, for other reasons, on real product names
("Tesco British Semi Skimmed Milk 2 Pints"), so they are an independent check of our matcher.

    python src/off_validate.py --collect   # search OFF and save the pairs (slow: ~6 s per search, cached)
    python src/off_validate.py             # score the AI matcher (and the keyword baseline) on the saved pairs

Queries are the names of our 41 curated categories (data/curated/categories.csv), chosen before looking at
any result. Only products sold in English-speaking countries are kept (the model reads English), and only
those whose Agribalyse code is in our 1,615-food index. The pairs are saved to data/eval/off_pairs.csv,
which is also the training data for a future fine-tuning step.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from foods import load_foods, same_food  # noqa: E402
from match import load_categories  # noqa: E402

PAIRS = Path(__file__).resolve().parents[1] / "data" / "eval" / "off_pairs.csv"
ENGLISH_COUNTRIES = {"en:united-kingdom", "en:united-states", "en:ireland", "en:canada", "en:australia",
                     "en:new-zealand"}
PAGE_SIZE = 50
MAX_PER_QUERY = 15  # so no single category dominates the score


def product_name(p: dict) -> str:
    return (p.get("product_name_en") or p.get("product_name") or "").strip()


def select_pairs(query: str, products: list[dict], food_codes: set[str]) -> list[dict]:
    """Keep English-market products with a name and an Agribalyse code that is in our index."""
    out, seen = [], set()
    for p in products:
        name, code = product_name(p), p.get("agribalyse_code")
        countries = set(p.get("countries_tags") or [])
        if not name or not code or not (countries & ENGLISH_COUNTRIES):
            continue
        code = str(code)
        if code not in food_codes:
            continue  # e.g. a ready meal we removed from the index
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"query": query, "barcode": p.get("code"), "product_name": name, "brands": p.get("brands"),
                    "gold_codes": code, "off_co2_kg_per_kg": p.get("co2_total_kg_per_kg")})
        if len(out) >= MAX_PER_QUERY:
            break
    return out


def collect(search=None) -> pd.DataFrame:
    from off_api import search_products

    search = search or search_products
    food_codes = set(load_foods().index)
    rows = []
    for query in load_categories()["category"]:
        found = select_pairs(query, search(query, page_size=PAGE_SIZE), food_codes)
        print(f"  {query:<16} {len(found):>2} products")
        rows += found
    pairs = pd.DataFrame(rows).drop_duplicates(subset="product_name")
    PAIRS.parent.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(PAIRS, index=False)
    print(f"\nSaved {len(pairs)} product → Agribalyse pairs to {PAIRS}")
    return pairs


def score(matcher, pairs: pd.DataFrame, foods: pd.DataFrame, top_k: bool = False) -> dict:
    """Top-1 accuracy (with the matcher's threshold: no answer counts as wrong) and, for the AI, top-5."""
    correct = abstained = in_top5 = 0
    misses = []
    for _, r in pairs.iterrows():
        code, _ = matcher.match_food(r["product_name"])
        ok = same_food(code, r["gold_codes"], foods)
        correct += ok
        abstained += code is None
        if top_k:
            in_top5 += any(same_food(c, r["gold_codes"], foods) for c, _ in matcher.top_k(r["product_name"], 5))
        if not ok:
            misses.append((r["product_name"], foods.at[r["gold_codes"], "name"],
                           None if code is None else foods.at[code, "name"]))
    n = len(pairs)
    return {"n": n, "correct": correct, "abstained": abstained, "wrong": n - correct - abstained,
            "top5": in_top5 if top_k else None, "misses": misses}


def report(label: str, res: dict, show: int = 15) -> None:
    n = res["n"]
    line = (f"[{label}] correct {res['correct']}/{n} = {res['correct'] / n:.0%} | wrong {res['wrong']}"
            f" | no answer {res['abstained']}")
    if res["top5"] is not None:
        line += f" | right food in top 5: {res['top5']}/{n} = {res['top5'] / n:.0%}"
    print(line)
    for product, gold, got in res["misses"][:show]:
        print(f"  miss {product[:45]!r}: OFF says {gold[:40]!r}, got {got[:40] if got else 'no answer'!r}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect", action="store_true", help="search Open Food Facts and save the pairs first")
    args = parser.parse_args()

    if args.collect or not PAIRS.exists():
        collect()
    pairs = pd.read_csv(PAIRS, dtype={"gold_codes": str, "barcode": str})
    foods = load_foods()
    print(f"\nOpen Food Facts pairs: {len(pairs)} products from {pairs['query'].nunique()} queries\n")

    from match import AIMatcher, KeywordMatcher

    report("keyword baseline", score(KeywordMatcher(), pairs, foods))
    ai = AIMatcher(foods)
    report(f"ai: {ai.model_name}, threshold {ai.threshold}", score(ai, pairs, foods, top_k=True))
