# Recipe Eco-Score & Swap Assistant (PAIBS, Group 8)

Takes a recipe, estimates its environmental footprint per ingredient using
Agribalyse data, and suggests lower-impact swaps.

## Setup
All Python packages live in a project virtual environment (`.venv`), nothing global:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # pandas, pyarrow, jupyter, duckdb, requests
```

## How to run
From the project root, with the venv active:
```bash
python src/pipeline.py   # sample recipe -> per-ingredient CO2e table, total, suggested swaps
python src/evaluate.py   # matcher accuracy on data/eval/ingredient_lines.csv
```

## Data
`data/raw/` is **not in git**: everyone downloads it locally with the commands below.
`data/curated/` (our hand-made tables) and `data/eval/` (the test set) **are** in git.

| File | What it is |
|---|---|
| `data/curated/categories.csv` | ~40 ingredient categories: Agribalyse code, kg CO2e per kg ("Changement climatique"), synonyms separated by `\|`. A blank code means no good generic match was found yet. |
| `data/curated/swaps.csv` | hand-curated swaps between categories, with reason and notes |
| `data/eval/ingredient_lines.csv` | ingredient lines with the correct category; grow this to 100+ |

Raw downloads (put them in `data/raw/`):

| Source | Location | Get it with |
|---|---|---|
| Agribalyse Synthèse CSV (core: CO2e and EF score per kg, ~2,450 foods) | `data/raw/agribalyse_synthese.csv` | `curl -L -o data/raw/agribalyse_synthese.csv "https://www.data.gouv.fr/api/1/datasets/r/41397293-3e85-4959-8936-940bb79d91fc"` |
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
- `data/curated/` categories and swaps tables, `data/eval/` evaluation set
- `notebooks/` exploration
- `src/load_data.py` loads Agribalyse (Level 1)
- `src/off_api.py` cached Open Food Facts API client (barcode lookup + search)
- `src/parse.py` `parse_line("200g minced beef")` -> quantity, unit, name, grams
- `src/match.py` `KeywordMatcher` (synonyms) and `AIMatcher` stub (same `.match(name)` interface)
- `src/score.py` `score_recipe(...)` -> kg CO2e per ingredient + total
- `src/swaps.py` `suggest_swaps(...)` -> swaps with CO2 saved, biggest emitters first
- `src/pipeline.py` runs everything end to end on a sample recipe (Level 2)
- `src/evaluate.py` accuracy + misses for each matcher

## Team workflow
1. `git pull` before you start working.
2. Make small, focused commits with clear messages.
3. Work on a branch per task (`git switch -c parsing-units`) and open a PR, or at least
   run `git pull --rebase` before you `git push` to main.
4. Everyone commits under their own name (`git config user.name` / `user.email`).
5. Never commit `data/raw/`, `data/processed/`, `.venv/`, or any API key/token.
6. If you change a curated table or the matcher, run `python src/evaluate.py` and
   `python src/pipeline.py` before pushing.
