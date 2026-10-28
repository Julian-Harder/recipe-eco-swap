"""Open Food Facts API client with an on-disk JSON cache and polite rate limiting."""
import hashlib
import json
import re
import time
from pathlib import Path

import requests

CACHE = Path(__file__).resolve().parents[1] / "data" / "processed" / "off_cache"
BASE = "https://world.openfoodfacts.org"
SEARCH_URL = "https://search.openfoodfacts.org/search"
HEADERS = {"User-Agent": "PAIBS-RecipeEcoSwap/0.1 (student project)"}

# The API returns the eco-score as ecoscore_*; environmental_score_* is requested too
# in case it is renamed. ecoscore_data.agribalyse holds the Agribalyse code and CO2 breakdown.
FIELDS = ",".join([
    "code", "product_name", "brands", "categories_tags", "countries_tags",
    "nutriscore_grade", "ecoscore_grade", "ecoscore_score",
    "environmental_score_grade", "environmental_score_score",
    "ecoscore_data", "product_quantity", "product_quantity_unit",
])

# Minimum seconds between network calls: ~100 req/min for products, ~10 req/min for search.
MIN_INTERVAL = {"product": 0.6, "search": 6.0}
_last_call = {"product": 0.0, "search": 0.0}


def _wait(kind: str) -> None:
    delay = MIN_INTERVAL[kind] - (time.monotonic() - _last_call[kind])
    if delay > 0:
        time.sleep(delay)
    _last_call[kind] = time.monotonic()


def _cached_get(kind: str, key: str, url: str, params: dict) -> dict:
    path = CACHE / kind / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    _wait(kind)
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    if resp.status_code == 404:
        data = {"status": 0, "status_verbose": "product not found"}
    else:
        resp.raise_for_status()
        data = resp.json()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def flatten(product: dict) -> dict:
    """Keep the useful fields and pull the Agribalyse link out of ecoscore_data."""
    agb = (product.get("ecoscore_data") or {}).get("agribalyse") or {}
    return {
        "code": product.get("code"),
        "product_name": product.get("product_name"),
        "brands": product.get("brands"),
        "categories_tags": product.get("categories_tags"),
        "countries_tags": product.get("countries_tags"),
        "nutriscore_grade": product.get("nutriscore_grade"),
        "eco_grade": product.get("environmental_score_grade") or product.get("ecoscore_grade"),
        "eco_score": product.get("environmental_score_score") or product.get("ecoscore_score"),
        "product_quantity": product.get("product_quantity"),
        "product_quantity_unit": product.get("product_quantity_unit"),
        "agribalyse_code": agb.get("agribalyse_food_code") or agb.get("agribalyse_proxy_food_code"),
        "agribalyse_name_en": agb.get("name_en"),
        "co2_total_kg_per_kg": agb.get("co2_total"),
        "ef_total": agb.get("ef_total"),
    }


def get_product(barcode: str) -> dict | None:
    """Return a flattened product dict, or None if Open Food Facts doesn't know the barcode."""
    barcode = re.sub(r"\D", "", str(barcode))
    data = _cached_get("product", barcode, f"{BASE}/api/v2/product/{barcode}.json", {"fields": FIELDS})
    if data.get("status") != 1:
        return None
    return flatten(data["product"])


def search_products(query: str, page_size: int = 20) -> list[dict]:
    """Full-text product search; results are flattened like get_product.

    Uses search.openfoodfacts.org because the legacy /cgi/search.pl endpoint returns 503s.
    """
    key = hashlib.sha1(f"{query.lower().strip()}|{page_size}".encode()).hexdigest()[:16]
    params = {"q": query, "page_size": page_size, "fields": FIELDS}
    data = _cached_get("search", key, SEARCH_URL, params)
    return [flatten(p) for p in data.get("hits", [])]


if __name__ == "__main__":
    for code in ["3250390523970", "3410280010182", "3850355007660"]:
        print(get_product(code))
    for p in search_products("oat milk", page_size=5):
        print(p["code"], p["product_name"], p["eco_grade"], p["agribalyse_code"])
