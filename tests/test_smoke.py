"""Smoke test of the demo path: the bolognese we show on 2 December, end to end.

recipe text -> parse -> match -> CO2e -> swaps

Run it before every merge:   pytest
Only the fast tests:         pytest -m "not slow"

The keyword version runs anywhere (no model needed). The AI version is the real demo path; it loads
jonny9f/food_embeddings (438 MB, downloaded on first use) and is skipped when that is not possible.
"""
import os

import pytest

from match import KeywordMatcher
from pipeline import SAMPLE_RECIPE, run

N_LINES = len([line for line in SAMPLE_RECIPE.splitlines() if line.strip()])


def check_demo_result(scored, total, swaps, expected_total, tolerance):
    # 1. Every line of the recipe comes out of the pipeline.
    assert len(scored) == N_LINES

    # 2. The total is about what LOG.md says.
    assert total == pytest.approx(expected_total, abs=tolerance)

    # 3. Beef is matched to minced beef and is by far the biggest emitter (iteration 1 matched poultry).
    beef = scored[scored["line"].str.contains("minced beef")].iloc[0]
    assert str(beef["food"]).startswith("Beef, minced steak")
    assert beef["share"] > 0.8

    # 4. A swap for beef exists and every suggested swap actually saves CO2e.
    assert any(s["from"] == "beef mince" for s in swaps)
    assert all(s["kg_co2e_saved"] > 0 for s in swaps)

    # 5. The parmesan grated on top is not replaced by yogurt (dish-aware swaps, LOG 2026-11-19).
    assert not any("parmesan" in s["line"] and s["to"] == "yogurt" for s in swaps)

    # 6. No AI swap for the tomatoes (seen on the deployed app: canned tomatoes -> raw beetroot, LOG 2026-11-20).
    assert not any("tomato" in s["line"] and s.get("source") == "ai" for s in swaps)


def test_demo_path_keyword_baseline(foods, categories, swaps):
    scored, total, suggestions = run(SAMPLE_RECIPE, KeywordMatcher(categories),
                                     foods=foods, categories=categories, swaps=swaps)
    # All 8 lines are counted with the keyword matcher; LOG.md: ≈ 15.5 kg CO2e.
    assert scored["kg_co2e"].notna().all()
    check_demo_result(scored, total, suggestions, expected_total=15.5, tolerance=0.5)


@pytest.fixture(scope="module")
def ai_matcher(foods):
    # In CI (REQUIRE_AI_MODEL=1) a missing model is a failure, not a skip: the demo path must be tested.
    required = os.environ.get("REQUIRE_AI_MODEL") == "1"
    if not required:
        pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed")
    from match import AIMatcher

    try:
        return AIMatcher(foods)
    except Exception as exc:  # no internet / Hugging Face unreachable on first run
        if required:
            raise
        pytest.skip(f"AI model could not be loaded: {exc}")


@pytest.mark.slow
def test_demo_path_ai_matcher(ai_matcher, foods, categories, swaps):
    scored, total, suggestions = run(SAMPLE_RECIPE, ai_matcher,
                                     foods=foods, categories=categories, swaps=swaps)
    # LOG.md (2026-11-09, iteration 3): ≈ 15.2 kg CO2e with the AI matcher.
    check_demo_result(scored, total, suggestions, expected_total=15.2, tolerance=1.0)


@pytest.mark.slow
def test_ai_matcher_handles_the_traps(ai_matcher, foods):
    """The lines that motivated the AI matcher: the keyword baseline gets these wrong."""
    expected = {
        "beef stock": "Broth, stock or bouillon, beef",
        "peanut butter": "Peanut butter",
        "butter beans": "Butter bean",
    }
    for name, start in expected.items():
        code, score = ai_matcher.match_food(name)
        assert code is not None, f"{name!r}: no answer (score {score:.2f})"
        assert foods.at[code, "name"].startswith(start), f"{name!r} -> {foods.at[code, 'name']}"


@pytest.mark.slow
def test_ai_matcher_abstains_on_unknown_food(ai_matcher):
    # xanthan gum is not in Agribalyse: better no answer than a wrong one.
    code, _ = ai_matcher.match_food("xanthan gum")
    assert code is None
