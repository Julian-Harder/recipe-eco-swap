# Recipe Eco-Score & Swap Assistant (PAIBS, Group 8)

Takes a recipe, estimates its environmental footprint per ingredient using
Agribalyse data, and suggests lower-impact swaps.

## Setup
All Python packages live in a project virtual environment (`.venv`), nothing global:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # pandas, sentence-transformers, requests, ...
```

## How to run
From the project root, with the venv active:
```bash
streamlit run src/app.py           # the web app: paste a recipe, confirm matches, see footprint and swaps
python src/pipeline.py             # sample recipe -> matched foods, CO2e per ingredient, total, swaps (AI matcher)
python src/pipeline.py --keyword   # same, with the keyword baseline
python src/evaluate.py             # keyword baseline vs AI matcher on the test set (add --dev for the dev set)
python src/compare_matchers.py     # compare models/settings on the dev set (slow: downloads ~1 GB of models)
python src/build_index.py          # only when the raw data changes: rebuilds data/index/foods.csv
```
The first run of the AI matcher downloads `jonny9f/food_embeddings` (438 MB) from Hugging Face.
Settings are tuned on the dev set only; the test set is for the final number. Decisions, results and
what is real vs. stubbed are in [LOG.md](LOG.md).

## Data
`data/raw/` is **not in git**: everyone downloads it locally with the commands below.
`data/index/` (generated, so the app runs without the raw downloads), `data/curated/` (our hand-made
tables) and `data/eval/` (the test set) **are** in git.

| File | What it is |
|---|---|
| `data/index/foods.csv` | the 1,615 Agribalyse ingredients the matcher searches: code, English/French name, sub-group, kg CO2e per kg, kcal per 100 g (CIQUAL). Ready meals and cooked duplicates removed; see LOG.md |
| `data/curated/categories.csv` | ~40 ingredient categories: Agribalyse code, kg CO2e per kg ("Changement climatique"), synonyms separated by `\|`. Used by the keyword baseline and to attach swaps. |
| `data/curated/swaps.csv` | hand-curated swaps between categories, with reason and notes |
| `data/eval/ingredient_lines.csv` | **test set**: 48 lines with the correct Agribalyse code(s) (`\|`-separated) and a kind: easy, trap, synonym, typo, none. Never tune on it. |
| `data/eval/dev_lines.csv` | **dev set**: 48 different lines, same format, used to choose models and settings |

Raw downloads (put them in `data/raw/`):

| Source | Location | Get it with |
|---|---|---|
| Agribalyse Synthèse CSV (core: CO2e and EF score per kg, ~2,450 foods) | `data/raw/agribalyse_synthese.csv` | `curl -L -o data/raw/agribalyse_synthese.csv "https://www.data.gouv.fr/api/1/datasets/r/41397293-3e85-4959-8936-940bb79d91fc"` |
| CIQUAL 2025 + 2020 nutrition tables (calories, for the near-duplicate rule), Open Food Facts' copy | `data/raw/ciqual/` | `mkdir -p data/raw/ciqual && for v in 2025_ENG_2025_11_03 2020_ENG_2020_07_07; do curl -L -o data/raw/ciqual/CIQUAL$v.csv "https://raw.githubusercontent.com/openfoodfacts/openfoodfacts-server/main/external-data/ciqual/ciqual/CIQUAL$v.csv"; done` |
| Open Prices (Open Food Facts price records, ~337k rows) | `data/raw/prices.jsonl.gz` | `curl -L -o data/raw/prices.jsonl.gz "https://prices.openfoodfacts.org/data/prices.jsonl.gz"` |
| Open Food Facts products (barcode -> name, eco-score, Agribalyse code, CO2) | fetched on demand via `src/off_api.py`, cached in `data/processed/off_cache/` | `from src.off_api import get_product, search_products` |

Notes:
- `load_agribalyse()` drops the empty rows in the export (14,956 -> 2,451).
- Read Open Prices with `pd.read_json(path, lines=True, dtype={"product_code": str})` so barcodes stay strings.
- `off_api.py` caches every response as JSON, so repeated calls never hit the network,
  and rate-limits itself (~100 product lookups/min, ~10 searches/min). The Agribalyse link
  for a product is in `ecoscore_data.agribalyse` (exposed as `agribalyse_code`, `co2_total_kg_per_kg`).
- The full Open Food Facts parquet dump (8 GB) is not used.

## Layout
- `data/raw/` original downloads (not in git), `data/processed/` cleaned outputs (not in git)
- `data/index/` generated ingredient index, `data/curated/` categories and swaps tables, `data/eval/` evaluation set
- `notebooks/` exploration
- `src/load_data.py` loads Agribalyse (Level 1)
- `src/build_index.py` builds `data/index/foods.csv` from Agribalyse + CIQUAL
- `src/foods.py` `load_foods()` and `same_food(a, b)`, the near-duplicate rule (calories within 10%)
- `src/off_api.py` cached Open Food Facts API client (barcode lookup + search)
- `src/parse.py` `parse_line("200g minced beef")` -> quantity, unit, name, grams
- `src/match.py` `KeywordMatcher` (baseline) and `AIMatcher` (food embedding model + word overlap); both have `match_food(name) -> (code, score)`
- `src/compare_matchers.py` model/settings comparison on the dev set
- `src/score.py` `score_recipe(lines)` -> kg CO2e per ingredient + total
- `src/swaps.py` `suggest_swaps(...)` -> swaps with CO2 saved, biggest emitters first
- `src/pipeline.py` runs everything end to end on a sample recipe (command line)
- `src/app.py` Streamlit UI: top-5 food dropdown per line, editable grams, footprint chart, swaps
- `src/evaluate.py` accuracy, misses, top-5 recall and a threshold sweep for each matcher
- `LOG.md` decision log: what we believed, chose and measured

## Team workflow
1. `git pull` before you start working.
2. Make small, focused commits with clear messages.
3. Work on a branch per task (`git switch -c parsing-units`) and open a PR, or at least
   run `git pull --rebase` before you `git push` to main.
4. Everyone commits under their own name (`git config user.name` / `user.email`).
5. Never commit `data/raw/`, `data/processed/`, `.venv/`, or any API key/token.
6. If you change a curated table or the matcher, run `python src/evaluate.py` and
   `python src/pipeline.py` before pushing.
