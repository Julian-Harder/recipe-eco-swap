"""Open Food Facts code without the network: product parsing, pair selection and scoring."""
import pandas as pd

from match import KeywordMatcher
from off_api import flatten
from off_validate import product_name, score, select_pairs


def test_flatten_reads_the_agribalyse_link():
    raw = {"code": "123", "product_name": "Lait demi-écrémé", "product_name_en": "Semi-skimmed milk",
           "countries_tags": ["en:united-kingdom"],
           "ecoscore_data": {"agribalyse": {"agribalyse_food_code": "19041", "co2_total": 1.2}}}
    p = flatten(raw)
    assert p["agribalyse_code"] == "19041"
    assert p["co2_total_kg_per_kg"] == 1.2
    assert product_name(p) == "Semi-skimmed milk"  # English name preferred


def test_flatten_uses_the_proxy_code_when_there_is_no_direct_one():
    raw = {"ecoscore_data": {"agribalyse": {"agribalyse_proxy_food_code": "20034"}}}
    assert flatten(raw)["agribalyse_code"] == "20034"


def test_select_pairs_filters(foods):
    codes = set(foods.index)
    products = [
        {"code": "1", "product_name": "Tesco Onions", "countries_tags": ["en:united-kingdom"], "agribalyse_code": "20034"},
        {"code": "2", "product_name": "TESCO ONIONS", "countries_tags": ["en:united-kingdom"], "agribalyse_code": "20034"},
        {"code": "3", "product_name": "Oignons jaunes", "countries_tags": ["en:france"], "agribalyse_code": "20034"},
        {"code": "4", "product_name": "Onion soup", "countries_tags": ["en:united-states"], "agribalyse_code": "99999"},
        {"code": "5", "product_name": "", "countries_tags": ["en:united-kingdom"], "agribalyse_code": "20034"},
        {"code": "6", "product_name": "Red onions", "countries_tags": ["en:ireland"], "agribalyse_code": None},
    ]
    pairs = select_pairs("onion", products, codes)
    # duplicate name, French market, code not in index, no name and no code are all dropped
    assert [p["barcode"] for p in pairs] == ["1"]
    assert pairs[0]["gold_codes"] == "20034"


def test_score_counts_right_wrong_and_no_answer(foods, categories):
    pairs = pd.DataFrame([
        {"product_name": "brown onions", "gold_codes": "20034"},           # keyword: onion -> right
        {"product_name": "free range eggs", "gold_codes": "20034"},        # keyword: eggs -> wrong
        {"product_name": "quinoa crackers", "gold_codes": "20034"},        # keyword: nothing -> no answer
    ])
    res = score(KeywordMatcher(categories), pairs, foods)
    assert (res["correct"], res["wrong"], res["abstained"]) == (1, 1, 1)
    assert len(res["misses"]) == 2
