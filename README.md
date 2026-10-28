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

## Data
Raw downloads go in `data/raw/` (not committed to git):

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
- `data/raw/` original downloads, `data/processed/` cleaned outputs
- `notebooks/` exploration
- `src/load_data.py` loads Agribalyse (Level 1)
- `src/off_api.py` cached Open Food Facts API client (barcode lookup + search)
- `src/pipeline.py` recipe -> scores -> swaps skeleton (Level 2)
