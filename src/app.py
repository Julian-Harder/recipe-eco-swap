"""Streamlit UI: paste a recipe, check each ingredient's match, see the CO2e footprint and swaps.

Run from the project root:
    streamlit run src/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from foods import load_foods  # noqa: E402
from match import AIMatcher, KeywordMatcher, load_categories  # noqa: E402
from parse import parse_line  # noqa: E402
from pipeline import SAMPLE_RECIPE, swap_category  # noqa: E402
from score import score_recipe  # noqa: E402
from swaps import load_swaps, suggest_swaps  # noqa: E402

SKIP = "skip"
BAR_COLOR = "#2a78d6"  # one series, one hue

st.set_page_config(page_title="Recipe Eco-Score", page_icon="🌱", layout="wide")


@st.cache_resource(show_spinner="Loading the food model (the first run downloads ~440 MB)…")
def load_everything():
    foods = load_foods()
    categories = load_categories()
    return foods, categories, load_swaps(), AIMatcher(foods), KeywordMatcher(categories)


foods, categories, swaps, matcher, keyword = load_everything()

with st.sidebar:
    st.header("How it works")
    st.markdown(
        "1. Each line is split into amount and ingredient.\n"
        "2. An embedding model finds the 5 closest of 1,615 Agribalyse ingredients.\n"
        "3. You confirm or correct the match.\n"
        "4. Weight × Agribalyse kg CO2e per kg gives the footprint.\n"
        "5. Curated swaps suggest lower-impact alternatives."
    )
    st.markdown(
        f"**Matcher:** `{matcher.model_name}`. It picks a food on its own when its score is "
        f"≥ {matcher.threshold:.2f}; below that it asks you.\n\n"
        "**Test set (48 lines):** right food 75% of the time, in the top 5 94% of the time "
        "(keyword baseline: 27%)."
    )
    st.caption("Data: Agribalyse (ADEME/INRAE), CIQUAL calories (ANSES, via Open Food Facts). "
               "Results are estimates per food category, not measurements of a specific product.")

st.title("Recipe Eco-Score & Swap Assistant")
st.caption("Paste a recipe with one ingredient per line, check the matches, then see the footprint and lower-impact swaps.")

left, right = st.columns([3, 1])
recipe = left.text_area("Recipe", SAMPLE_RECIPE, height=230)
servings = right.number_input("Servings", min_value=1, max_value=50, value=4)
lines = [line.strip() for line in recipe.splitlines() if line.strip()]
if not lines:
    st.info("Paste a recipe to start.")
    st.stop()

# 1. Ingredient matching, with a top-5 dropdown per line
st.subheader("1. Check the ingredients")
st.caption("The model's best guess is preselected when it is confident. Lines marked "
           ":orange[please pick] need your choice. Fix the grams if the amount was misread.")
head = st.columns([3, 6, 1.4])
head[0].markdown("**Recipe line**")
head[1].markdown("**Matched food** (top 5 · kg CO2e per kg · match score)")
head[2].markdown("**Grams**")

matched = []
for i, line in enumerate(lines):
    parsed = parse_line(line)
    candidates = matcher.top_k(parsed["name"], 5)
    confident = candidates[0][1] >= matcher.threshold
    labels = {code: f"{foods.at[code, 'name']} · {foods.at[code, 'co2_kg_per_kg']:.2f} · {score:.2f}"
              for code, score in candidates}
    labels[SKIP] = "Skip this ingredient (none of these)"
    scores = dict(candidates)

    col_line, col_food, col_grams = st.columns([3, 6, 1.4])
    col_line.markdown(f"{line}" + ("" if confident else "  \n:orange[please pick]"))
    choice = col_food.selectbox(
        f"Food for {line}", list(labels), index=0 if confident else None, format_func=labels.get,
        placeholder="Not sure: pick the right food", key=f"food-{i}-{line}", label_visibility="collapsed")
    grams = col_grams.number_input(
        f"Grams for {line}", min_value=0.0, value=float(parsed["grams"] or 0.0), step=10.0,
        key=f"grams-{i}-{line}", label_visibility="collapsed")

    code = choice if choice not in (None, SKIP) else None
    reason = None
    if choice is None:
        reason = "no food picked"
    elif choice == SKIP:
        reason = "skipped"
    elif grams <= 0:
        reason = "amount unknown: enter grams"
    matched.append({
        "line": line, "name": parsed["name"], "grams": grams if reason is None else None,
        "food_code": code, "food": foods.at[code, "name"] if code else None,
        "match_score": scores.get(code), "co2_kg_per_kg": foods.at[code, "co2_kg_per_kg"] if code else None,
        "category": swap_category(code, categories, foods, keyword), "reason": reason,
    })

scored, total = score_recipe(matched)
counted = scored.dropna(subset=["kg_co2e"]).sort_values("kg_co2e", ascending=False)
suggestions = suggest_swaps(counted, swaps, categories)

# 2. Footprint
st.subheader("2. Footprint")
best_saving = {}
for s in suggestions:
    best_saving[s["line"]] = max(best_saving.get(s["line"], 0.0), s["kg_co2e_saved"])
with_swaps = total - sum(best_saving.values())
m1, m2, m3 = st.columns(3)
m1.metric("Whole recipe, kg CO2e", f"≈ {total:.1f}")
m2.metric("Per serving, kg CO2e", f"≈ {total / servings:.2f}")
m3.metric("With best swaps, kg CO2e", f"≈ {with_swaps:.1f}",
          delta=f"-{total - with_swaps:.1f} kg" if total > with_swaps else None, delta_color="inverse",
          help="If you make the biggest-saving swap for each ingredient below.")

if len(counted):
    chart = (
        alt.Chart(counted)
        .mark_bar(color=BAR_COLOR, cornerRadiusEnd=4, size=16)
        .encode(
            x=alt.X("kg_co2e:Q", title="kg CO2e"),
            y=alt.Y("line:N", sort="-x", title=None),
            tooltip=[alt.Tooltip("line:N", title="Recipe line"),
                     alt.Tooltip("food:N", title="Matched food"),
                     alt.Tooltip("kg_co2e:Q", title="kg CO2e", format=".2f"),
                     alt.Tooltip("share:Q", title="Share of total", format=".0%")])
        .properties(height=max(120, 30 * len(counted)))
        .configure_axis(gridOpacity=0.3, domain=False)
    )
    st.altair_chart(chart)
    with st.expander("Table view"):
        table = counted[["line", "food", "grams", "co2_kg_per_kg", "kg_co2e", "share"]].copy()
        table["share"] = table["share"] * 100
        st.dataframe(table, hide_index=True, column_config={
            "line": "Recipe line", "food": "Matched food", "grams": st.column_config.NumberColumn("Grams", format="%.0f"),
            "co2_kg_per_kg": st.column_config.NumberColumn("kg CO2e / kg", format="%.2f"),
            "kg_co2e": st.column_config.NumberColumn("kg CO2e", format="%.2f"),
            "share": st.column_config.NumberColumn("Share", format="%.0f%%")})

not_counted = scored[scored["kg_co2e"].isna()]
if len(not_counted):
    st.warning("Not counted in the total: " + "; ".join(
        f"**{r['line']}** ({r['reason'] or 'no CO2 value'})" for _, r in not_counted.iterrows()))

# 3. Swaps
st.subheader("3. Lower-impact swaps")
if not suggestions:
    st.write("No curated swaps for these ingredients yet.")
for s in suggestions:
    note = f" *{s['notes']}*" if isinstance(s["notes"], str) and s["notes"] else ""
    st.markdown(f"- **{s['line']}**: {s['from']} → **{s['to']}** saves ≈ {s['kg_co2e_saved']:.1f} kg CO2e "
                f"({s['kg_co2e_before']:.1f} → {s['kg_co2e_after']:.1f}). {s['reason']}.{note}")
st.caption("Savings assume the same weight of the replacement, which is a simplification (see each swap's note).")
