# Decision log: Group 8, Recipe Eco-Score & Swap Assistant

Newest entries first. Each entry says what we believed, what we chose, and why.

---

## 2026-11-09 (iteration 3): Streamlit UI

### Decision
A Streamlit page (`streamlit run src/app.py`) where the user stays in the loop:
- Each recipe line gets a dropdown with the matcher's **top 5 foods**, showing kg CO2e per kg and match score.
  The best one is preselected only when its score is ≥ the 0.80 threshold. Otherwise the line says
  "please pick" and is not counted until the user chooses. Why: the top 5 contains the right food 94% of
  the time, but the first choice only 75% of the time. Asking costs one click; a silent wrong match corrupts the total.
- Grams are editable, because the parser can misread amounts ("salt to taste" has none).
- A footprint section (total, per serving, total with the best swap per ingredient) with a bar chart per
  ingredient and a table view. A "not counted" warning lists every line that was left out, and why.
- The curated swaps are shown with their caveats (savings assume the same weight).

### Checked by hand (2026-11-09)
- Default bolognese: ≈ 15.2 kg CO2e, beef 94% of it. Changing spaghetti from "spaghetti squash" to
  "Dried pasta, raw" in the dropdown updates the total to ≈ 15.6.
- Test recipe "1 aubergine / 200g mushrooms / 500ml beef stock / 2 tbsp peanut butter / salt to taste / 500g mince":
  stock and peanut butter are matched correctly (≈ 0.2 kg in total). Aubergine, mushrooms, salt and mince are flagged
  "please pick" and listed as not counted. Picking "Beef, minced steak" (3rd in the mince dropdown, after poultry
  and ham) raises the total to ≈ 18.0 and brings up the beef → lentils swap.

---

## 2026-11-09 (iteration 2): Fixing the matcher without tuning on the test set

### Problem
Iteration 1 matched "minced beef" to "Poultry, minced meat", so the demo bolognese read ≈ 3.9 kg CO2e
instead of ≈ 15.5. We wanted to fix this without tuning on the test set, because a score tuned on
the test set says nothing about new recipes.

### Method
- **New dev set**, `data/eval/dev_lines.csv`: 48 new lines (16 easy, 18 traps, 8 synonyms, 4 typos, 2 with no
  correct food, e.g. raw mushrooms, which Agribalyse does not have). No line is shared with the test set.
  As before, we picked the correct foods by text search before running any model.
- **Every setting was chosen on dev only**, with `src/compare_matchers.py`. It tries 4 models × name cleanup on/off ×
  word-overlap bonus (0 / 0.15 / 0.3) × plain-ingredient penalty (0 / 0.1) × threshold (0.30 to 0.80).
- Then we ran `src/evaluate.py` **once** on the test set with the chosen settings.

### What we tried (all derived from earlier decisions, not from test-set misses)
1. **Other models:** `all-mpnet-base-v2` (larger general model), `BAAI/bge-small-en-v1.5` (small retrieval
   model) and `jonny9f/food_embeddings` (mpnet fine-tuned on 1.2M pairs of food names from Hugging Face).
   We skipped `disi-unibo-nlp/foodex-baseterm-retriever`: it is ~2 GB and was trained to match long food
   descriptions, not short names.
2. **Name cleanup:** drop "raw", "plain", "prepacked" and fat % from the embedded names. Every food is raw now
   (raw-weights decision), so these words carry no meaning.
3. **Word-overlap bonus:** + weight × share of the line's words (singular/plural folded) found in the food name.
4. **Plain-ingredient penalty:** −0.1 for canned/frozen/puree/powder/juice/smoked… foods when the line does not
   ask for that form (raw-ingredients decision). "Dried" is not penalised: it is the normal form of pulses and pasta.

### Dev-set results (best threshold per setting; full table from `python src/compare_matchers.py`)
| Model | Settings | Correct | Wrong | Top 5 |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | none (iteration 1) | 23/48 | 21 | 87% |
| all-MiniLM-L6-v2 | best (cleanup + overlap 0.15) | 27/48 | 16 | 87% |
| all-mpnet-base-v2 | best | 27/48 | 20 | 91% |
| bge-small-en-v1.5 | best (cleanup + overlap + penalty) | 31/48 | 11 | 85% |
| food_embeddings | none | 31/48 | 12 | 91% |
| **food_embeddings** | **overlap 0.3 + penalty 0.1, threshold 0.80** | **33/48** | **9** | 89% |

- The food-specific model is the biggest gain (+8 lines over MiniLM with no tweaks). The two tweaks add 2 more lines
  and cut wrong answers from 12 to 9. On 48 lines, 2 lines is within noise; we keep the tweaks because they
  are cheap and follow from our decisions, not because the gain is proven.
- Name cleanup helps the general models (MiniLM 23 → 27) but slightly hurts the food model (31 → 30),
  which was trained on names that include "raw". So it is off.

### Decision
Default matcher: `jonny9f/food_embeddings` (438 MB), overlap 0.3, penalty 0.1, threshold 0.80 (`src/match.py`).
Risk: the model has very few users and its card states no licence or training objective. It is fine for
a course demo; we would check with the author before any real use.

### Test-set results (run once, after choosing on dev)
| | Correct | CO2 within ±20% | Abstained | Wrong | Easy | Trap | Synonym | Typo | Top 5 |
|---|---|---|---|---|---|---|---|---|---|
| Keyword baseline | 13/48 (27%) | 35% | 17 | 19 | 11/15 | 1/17 | 0/11 | 0/4 | n/a |
| Iteration 1: MiniLM | 27/48 (56%) | 62% | 4 | 18 | 8/15 | 11/17 | 5/11 | 2/4 | 89% |
| **Iteration 2: food model + tweaks** | **36/48 (75%)** | **77%** | 8 | **5** | 12/15 | **17/17** | 5/11 | 1/4 | **94%** |

- The test score (75%) is close to the dev score (69%), so the settings do not look overfitted.
- Wrong answers dropped from 18 to 5. The 8 abstentions are shown to the user instead of being silently wrong.
- **Demo recipe:** "400g minced beef" now matches "Beef, minced steak, 10% fat, raw" (score 1.00); the bolognese reads
  ≈ 15.2 kg CO2e (the keyword baseline gives ≈ 15.5).

### Remaining failures
- "spaghetti" still matches spaghetti squash (small CO2 effect: 0.2 vs 0.6 kg), and "double cream" matches a double-cream
  cheese. "Courgettes" matches courgette puree, even with the penalty.
- The high threshold abstains on British words and typos the model half-knows: aubergine, mince, scallions, lardons,
  "brocoli", "chiken", "parmesean". In every case the right food is usually in the top 5, so a dropdown would fix it.

### Real / stub / faked: unchanged except
| Component | Status | Notes |
|---|---|---|
| Matcher | Real | Food-specific embedding model (pre-trained by a third party) + our overlap/penalty scoring and threshold, chosen on our dev set |

### Next
1. Streamlit UI with a top-5 dropdown for each ingredient. The top-5 recall is 94%, so most misses become one click.
2. Fine-tune an embedding model on Open Food Facts product name → Agribalyse code pairs, and compare it on the same dev/test sets.

---

## 2026-11-09: From keyword matching to an AI matcher (level 2 → level 3)

### Riskiest question
Can free-text ingredient lines ("500ml beef stock", "2 courgettes") be matched to the right
Agribalyse food reliably enough for the CO2 estimate to be trusted?

### What we found first
The keyword matcher scored 15/15 on our old 15-line test set, but only because its synonyms were
written for those exact lines. On lines it had never seen it failed badly: "beef stock" became beef
mince (35.7 vs 0.11 kg CO2e/kg, ~300× too high), and "peanut butter" and "butter beans" became butter.
The old test set could not show what an AI adds, so we replaced it (see Benchmark).

### Decisions
1. **Match against Agribalyse foods, not our 41 hand-made categories.** None of the hard cases
   has a correct answer among the 41 categories; every one of them exists in Agribalyse.
   The index is `data/index/foods.csv` (1,615 foods), built by `src/build_index.py`.
2. **Drop finished products.** The tool helps people cook with ingredients, so ready meals,
   baby food and ice cream are out, plus the cakes/pastries, breakfast cereals/biscuits and
   non-chocolate sweets sub-groups (578 foods). Exception: stock/broth stays (Agribalyse files it under soups).
3. **Raw weights.** Recipes give raw weights, so a cooked food is dropped when a raw version of
   it exists (258 foods: meat, fish, eggs, vegetables, pulses, potatoes, pasta/rice, fruit). This is not
   applied to charcuterie, because ham is sold cooked. Known gap: a cooked food stays when the raw one is named
   differently (e.g. "Green lentil, cooked" vs "Lentil, green, dried").
4. **Near duplicates count as the same food unless calories differ by more than 10% per 100 g.**
   Near duplicate = same Agribalyse sub-group + same name before the first comma. Example: the four fat
   levels of minced beef are different foods under this rule (130 to 249 kcal), while semi-skimmed milk
   UHT and pasteurised are the same. Calories come from CIQUAL 2025 (2020 as a fallback), joined
   on the CIQUAL code. The ANSES site was down for maintenance on 2026-11-09, so we used the copy
   in Open Food Facts' GitHub repository. 51 foods have no calories; for them, only an exact match counts.
5. **Model: `sentence-transformers/all-MiniLM-L6-v2`, pre-trained, no fine-tuning yet.**
   It is the standard small embedding model (~90 MB, runs on a laptop). The food names are embedded
   once, then each ingredient is one embedding plus a cosine similarity. We found food-specific models on Hugging Face
   (`jonny9f/food_embeddings`, `disi-unibo-nlp/foodex-baseterm-retriever`), but they have very few
   users and little documentation. We will compare them against MiniLM rather than assume they are better.
6. **Confidence threshold 0.5, set before the first run.** Below it the matcher abstains, and the
   line is listed as "not counted" instead of being silently wrong.
7. **Swaps stay on the 21 curated swaps between the 41 categories.** A matched food gets a category's
   swaps if it is that category's food (or a near duplicate), or if the category's synonyms appear in its
   name and the CO2 factors are within 25%. That way "Parmesan" gets the hard-cheese swaps and "beef stock"
   does not get the beef-mince ones.

### Benchmark
- **Metric:** % of test lines where the matched food is correct under the near-duplicate rule.
  Secondary metric: % of lines where the CO2 factor is within ±20% of the correct food's.
- **Test set:** `data/eval/ingredient_lines.csv`, 48 lines: 15 easy, 17 traps (beef stock, peanut butter,
  lamb's lettuce…), 11 British/US synonyms (courgette, mince, scallions…), 4 typos, and 1 line with no
  correct food (xanthan gum), where abstaining counts as correct. We picked the correct foods by text search
  **before** running the model, and we have not tuned anything on this set.
- **Baseline:** the keyword matcher. Its category is mapped to that category's Agribalyse food.

### Results (`python src/evaluate.py --sweep`)
| | Correct | CO2 within ±20% | Abstained | Wrong answers | Easy | Trap | Synonym | Typo |
|---|---|---|---|---|---|---|---|---|
| Keyword baseline | 13/48 (27%) | 35% | 17 | 19 | 11/15 | 1/17 | 0/11 | 0/4 |
| MiniLM, threshold 0.5 | **27/48 (56%)** | **62%** | 4 | 18 | 8/15 | 11/17 | 5/11 | 2/4 |

- The correct food is among MiniLM's top 5 for **42/47 lines (89%)**. A "pick one of these 5" dropdown
  in the UI would fix most misses with one click.
- Threshold trade-off: at 0.6 there are 23 correct, 13 abstentions and 13 wrong answers; at 0.5 there are 27 correct and 18 wrong.
  Wrong answers are worse than abstentions (the user never sees them), so a higher threshold plus a
  dropdown may suit the UI better.

### Where the AI fails (not hidden)
- **It gets the demo recipe's most important line wrong:** "minced beef" matches "Poultry, minced meat"
  (score 0.77), so the bolognese comes out at ≈ 3.9 kg CO2e instead of ≈ 15.5. The word "minced" outweighs "beef".
- "spaghetti" matches spaghetti squash, "chicken breasts" matches chicken fat, "large eggs" matches scrambled eggs,
  "aubergine" matches Auvergne blue cheese, and "scallions" matches scallops.
- Likely cause: Agribalyse names are written as "Food, cut, fat %, state", while recipes say "minced beef".
  The model compares surface wording, not what a cook means.

### Real / stub / faked (today)
| Component | Status | Notes |
|---|---|---|
| Parser (`parse.py`) | Real | Rules; units, fractions, piece weights |
| Ingredient index (`build_index.py`) | Real | Agribalyse + CIQUAL calories |
| Matcher (`match.py`) | Real | MiniLM off the shelf; keyword baseline kept |
| CO2 scoring (`score.py`) | Real | Raw weight × Agribalyse factor |
| Swaps (`swaps.py`) | Real, hand-curated | 21 swaps; savings assume the same weight |
| Open Food Facts product data | Not used yet | Only its copy of CIQUAL; planned as training data for fine-tuning |
| User interface | Missing | Command line only |

### Next
1. Improve the matcher on a **separate** development set, never on the 48-line test set: clean up the
   embedded names (drop "raw" and fat %, which carry no meaning now that every food is raw), and compare the two food-specific models.
2. Fine-tune MiniLM on Open Food Facts product name → Agribalyse code pairs.
3. Streamlit UI with a top-5 dropdown for each ingredient.
