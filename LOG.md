# Decision log: Group 8, Recipe Eco-Score & Swap Assistant

Newest entries first. Each entry says what we believed, what we chose, and why.

---

## 2026-11-19: Open Food Facts from Stub to Real

### Problem
Open Food Facts (OFF) is the course's required data source, but the pipeline only used OFF's copy of the
CIQUAL calorie table. `off_api.py` worked (cached barcode lookup and search) and nothing called it.

### Decision: two uses that need no fine-tuning
1. **External validation (`src/off_validate.py`).** OFF contributors link products to an Agribalyse food (that is
   how OFF computes the Eco-Score). Those links were made by other people on real, branded product names, so
   they are an independent check of our matcher, and harder than recipe lines.
   - Queries: the names of our 41 curated categories, fixed before looking at any result.
   - Kept: products sold in English-speaking countries (the model reads English), with a name and an
     Agribalyse code that is in our index; at most 15 per query; duplicate names dropped.
   - Saved to `data/eval/off_pairs.csv` (product name → Agribalyse code), which is also the training data for
     a later fine-tuning step.
   - Scored like the other sets: top-1 with the 0.80 threshold (no answer counts as wrong) and top 5.
2. **Barcode lookup in the app (section 4).** The user types a barcode; the app shows the product, OFF's
   Agribalyse food, its kg CO2e per kg and Eco-Score, next to what our matcher picks from the product name,
   and says whether they agree. Errors (unknown barcode, OFF unreachable) are shown, not raised.

### Tests
`tests/test_off.py` (no network): the Agribalyse link is read from OFF's JSON (direct or proxy code), the
English name is preferred, and pair selection drops other markets, unknown codes, missing names and
duplicates; scoring counts right / wrong / no answer. The app was run headless with a stand-in OFF client for a
found product, an unknown barcode and a network error. 68 fast tests pass. CI now installs `requests`.

### Real / stub / faked: change
| Component | Status | Notes |
|---|---|---|
| Open Food Facts | **Real** | external validation set + barcode lookup in the app (was: Stub) |

### First run (2026-11-19): the keyword baseline wins on OFF products
460 pairs from 40 of the 41 queries ("cheese (hard)" found no English-market product with a usable link).

| | Correct | Wrong | No answer | Top 5 |
|---|---|---|---|---|
| Keyword baseline | **257/460 (56%)** | 181 | 22 | n/a |
| AI matcher (threshold 0.80) | 190/460 (41%) | 139 | 131 | 392/460 (85%) |

We report this as it is: on branded product names the AI is **worse** than keyword matching under this metric.
We did not change the matcher to fix it. Three reasons are visible in the misses:
1. **OFF labels are noisy.** "Chicken breast" → "Chicken, meat and skin"; "British beef mince" → "Beef steak";
   "mushrooms" → morels (11 of 12); "bananas" → plantains (9 of 12). In such cases the AI's answer is often
   the right one and is counted wrong.
2. **The near-duplicate rule is strict here.** Beef mince 5% and 10% fat are different foods for the calorie rule
   but have the same CO2 factor (35.7). The keyword baseline always returns its category's default food, which
   is often the same coarse food OFF uses.
3. **Product names are long and branded** ("Simply... Piri Piri chicken breast slices"), so the AI falls under
   the 0.80 threshold for 28% of products and gives no answer, while the keyword matcher almost always answers
   (and is wrong 181 times, against 139 for the AI).

### Follow-up analysis (decided after the first run, stated as such)
- **Label audit:** 60 pairs drawn at random (seed 42) and checked by hand against the product name, without
  looking at either matcher's answer: 43 correct (72%), 8 approximate (13%, e.g. prawn cocktail → raw prawns),
  9 plainly wrong (15%: bananas → plantains, mushrooms → morels, skinless breast → meat and skin, mince → steak,
  double cream → light cream, salmon fishcakes → raw salmon). Saved in `data/eval/off_label_audit.csv`.
- **CO2 within ±20%**, the project's secondary metric, which this script had left out: for the footprint,
  5% vs 10% fat mince is the same answer.
- **AI forced to answer** (no threshold): how often its first choice is right when it must answer, which is
  closer to what the app does (a low-confidence line becomes a dropdown, not a blank).
- Scores on the 43 audited pairs with a correct label.

Results of the follow-up: [to be added]

---

## 2026-11-19: Holdout set, the number we trust

### Why
The 48-line test set is no longer blind: we have read its misses many times, and some synonym-list entries
are test lines. The dev set was used to choose settings. We need lines nobody has tuned on.

### How it was made
- **Lines:** 29 ingredient lines from six dishes (chicken curry, salad, pancakes with bacon, chocolate cake,
  salmon with dill, lentil soup), generated with Gemini by Marc from a short prompt (ordinary ingredients,
  British/American words, tricky names, an unusual ingredient), without access to our code, synonym list or
  evaluation sets, then reviewed by Marc. Written after all matcher choices were made. Gemini gave 30 lines;
  "2 tbsp maple syrup" was dropped because it is already a dev line (caught by the overlap test).
- **Labels:** the correct Agribalyse food(s) for each line were chosen by text search in `data/index/foods.csv`
  before any model ran on these lines. Several codes are accepted when the recipe line is ambiguous
  ("vegetable oil": blended, rapeseed or sunflower oil; "streaky bacon": smoked or salt-cured pork belly, or bacon).
  "50g pitted Kalamata olives" has no correct food (black olives are not in the index), so the right answer
  is no answer.
- **Mix:** 19 easy, 5 traps (curry powder, coconut milk, red wine vinegar, chicken stock, chicken thighs),
  4 British words (rocket, plain flour, streaky bacon, caster sugar), 1 with no correct food.
- **Limit:** Gemini wrote no typos, so typo correction is not measured here (only on dev, 4/4).
- `tests/test_score_and_data.py` checks that every gold code exists and that no holdout line is in test or dev.

### Rule
Run once, with the settings already in `main`: `python src/evaluate.py --holdout`. Whatever the result, it is
reported as is and nothing is tuned on it afterwards.

### Results (run once, 2026-11-19, Marc's MacBook)
| | Correct | CO2 within ±20% | Wrong | Abstained | Top 5 |
|---|---|---|---|---|---|
| Keyword baseline | 14/29 (48%) | 59% | 5 | 11 | n/a |
| **AI matcher (food_embeddings + normalization, threshold 0.80)** | **23/29 (79%)** | **79%** | **2** | 5 | **28/28 (100%)** |

- **This is the number we report: 79% on lines nobody tuned on, against 48% for keyword matching.** With 29 lines
  the uncertainty is large (roughly ±15 points, 95% interval), but the 31-point gap is about twice that.
- It sits between the dev score (85%) and the earlier blind test score (75%), so the dev tuning does not look overfitted.
- By kind: British words 4/4, the line with no correct food 1/1 (no answer), traps 3/5, easy 15/19.
- **The right food is in the top 5 for every line (28/28)**: in the app, every miss is fixed with one click.

### What went wrong (recorded, not fixed on this set)
- **Wrong answers (2), the dangerous kind because the user may not notice:**
  "red wine vinegar" → "Wine, red" (a trap: the word "wine" wins) and "large white onion" → "Onion, dried"
  (dried is not penalised, on purpose, because it is the normal form of pulses and pasta).
- **No answer (4), just under the 0.80 threshold (scores 0.64–0.79):** chicken thighs, English cucumber,
  free-range eggs, skin-on salmon fillets. All four lines carry descriptive words ("boneless", "free-range",
  "skin-on", "(about 150g each)", "English") that dilute the embedding. The app asks the user, and the right food
  is in the dropdown.
- Possible next step (to be tested on dev and judged on a NEW holdout, never on this one): drop descriptive words
  and text in brackets before matching, and penalise "dried" for vegetables.

---

## 2026-11-19: Deploying the app and collecting feedback (towards level 4)

### Why
Level 4 means someone outside the team used the tool and their feedback is logged. On 2 December another
team will use it. An app that only runs on one laptop after a 438 MB download is a demo risk.

### Decision
- **Hosting:** Streamlit Community Cloud, free, deploys from GitHub on every push to `main`.
  Alternatives considered: Hugging Face Spaces (also free, would also work), running it on one laptop on demo
  day (single point of failure). Community Cloud only deploys from a repository where the account is admin,
  so the repo owner deploys it.
- **Slim dependencies for the cloud:** `src/requirements.txt` with CPU-only PyTorch. The default Linux PyTorch
  wheel pulls about 2.5 GB of GPU libraries the app never uses. Jupyter, DuckDB and pytest are not needed there.
  The root `requirements.txt` stays the one for local work.
- **Feedback form in the app (section 4):** would it help them choose (yes / maybe / no), which lines were
  matched to the wrong food, a free comment, and an optional name or team. Each submission also stores the
  recipe, the total and what the app matched for each line, so a wrong match can be traced. Saved by
  `src/feedback.py` to `data/feedback/feedback.csv` (not in git, it may hold names).
- **Known limit:** the hosted app's disk is wiped when it restarts or sleeps. The sidebar has a download
  button; we download the CSV after every test session and copy the findings here. If we need more, the next
  step would be a Google Sheet as storage.
- Sidebar figures updated to the current matcher (dev set: 85% right, 100% in the top 5).

### Tests
`tests/test_feedback.py`: rows are appended with a header, and commas, quotes and new lines in comments
survive. The app was also run headless with Streamlit's AppTest (with a stand-in matcher): it renders all
four sections, saves a submission and refuses an empty one. 63 fast tests pass.

### Next
Deploy, run one test session with people outside the team before 2 December, and log what they said:
[to be added].

---

## 2026-11-19: Synonyms and typo correction before the AI matcher

### Problem
After the parser fixes, almost every remaining AI miss is a British/American word or a typo:
aubergine, mince, scallions, lardons, single/double cream (test); arugula, cilantro, garbanzo beans,
cornflour (dev); brocoli, chiken, parmesean, mozarella, spinnach. Agribalyse is written in its own
wording ("Eggplant", "Chick pea", "Lardoons", "Maize/corn starch") and the model compares wording.

### Decision (`src/normalize.py`, used by `AIMatcher` when `normalize=True`, the default)
1. **Synonyms:** about 70 British/American kitchen words and phrases mapped to Agribalyse wording,
   taken from general UK/US food glossaries (vegetables, pulses, meat, dairy, baking). One pass,
   longest phrase first, whole words only, so a replacement is never replaced again.
2. **Typo correction:** a word of 5+ letters that is not in the vocabulary (all words of the 1,615 food
   names + synonym targets + common recipe words) becomes its closest vocabulary word if the difflib
   similarity is ≥ 0.85. Plurals of known words are left alone. Synonyms run first, so "scallions" is
   never corrected to "scallops".
3. The keyword baseline is unchanged: it stays the baseline.

### Honesty about the test set
Some glossary entries (double/single cream, aubergine, mince, scallions, lardons) are also lines of the
48-line test set, and we have looked at that set's misses many times. A test-set gain from this change
would therefore be optimistic. So:
- settings are compared on the **dev set** (`python src/evaluate.py --dev` vs `--dev --no-normalize`);
- the test set is reported, but marked as no longer blind;
- the number we trust is a **new holdout set** (`data/eval/holdout_lines.csv`), written by a team member
  after this change, labelled by text search before any model runs, and run **once**
  (`python src/evaluate.py --holdout`).

### What changes on the eval lines (no model needed to check this)
Dev: 15 of 48 names change (plain flour → wheat flour, cornflour → corn starch, garbanzo beans → chick pea,
cilantro → coriander, arugula → rocket, mozarella → mozzarella, spinnach → spinach, sunflwer → sunflower…).
Test: 10 of 48 (aubergine → eggplant, mince → minced beef, scallions → spring onion, lardons → lardoons,
brocoli → broccoli, chiken → chicken, parmesean → parmesan, double/single cream, bell pepper).
No change that looks wrong.

### Tests
`tests/test_normalize.py`: synonyms, whole-word and single-pass rules, typos corrected, correct words
left alone (including "xanthan gum"), synonyms before typos. 61 fast tests pass.

### Results
Run on 2026-11-19 (Marc's MacBook). Same model, threshold 0.80 and settings; only normalization changes.

| AI matcher | Correct | CO2 within ±20% | Wrong | Abstained | Top 5 |
|---|---|---|---|---|---|
| Dev, without normalization | 33/48 (69%) | 77% | 9 | 8 | 41/46 (89%) |
| **Dev, with normalization** | **41/48 (85%)** | **88%** | **7** | **2** | **46/46 (100%)** |
| Test, before (iteration 2 + parser fixes) | 36/48 (75%) | 77% | 5 | 8 | 45/47 (96%) |
| Test, with normalization (**not blind**, see above) | 44/48 (92%) | 92% | 4 | 1 | 47/47 (100%) |
| Keyword baseline, dev / test | 22/48 (46%) / 13/48 (27%) | 54% / 35% | 12 / 19 | 16 / 17 | n/a |

- **Dev, the fair comparison: +8 lines (69% → 85%).** Typos 2/4 → 4/4, synonyms 5/8 → 7/8, traps 13/18 → 16/18
  (cornflour, green beans, red chillies). Wrong answers also go down (9 → 7): the gain is not bought with more
  confident mistakes.
- Abstentions drop from 8 to 2 on dev, and the right food is now in the top 5 for every dev and test line.
  In the app this means almost no line asks the user to search.
- The test number (92%) is reported but not trusted, because some glossary entries are test lines.
  The trusted number will be the holdout.

### Decision: keep (normalize=True by default)

### Remaining misses (to look at on dev only, not fixed here)
- Processed or cooked forms still win sometimes: "2 zucchini" → "Courgettes, puree", "150g lardons" →
  "Lardoons, cooked" (the raw-weights filter misses it because the raw and cooked names differ),
  "400g can chickpeas" → "Chick pea, dried" (the canned form is lost).
- Easy lines with a better-scoring variant: "2 carrots, diced" → grated carrots, "2 apples" → dried apple,
  "2 salmon fillets" → salmon rillettes, "50g dark chocolate" → filled chocolate, "4 chicken thighs" → roasted leg.

### Holdout
See the entry "Holdout set" (2026-11-19) above.

---

## 2026-11-19: Parser fixes (cans, heads, bunches, handfuls, "to taste")

### Problem
A wrong amount gives a wrong CO2e even when the food is matched correctly. The parser had five known
bugs, written down as `xfail` tests in the previous entry:
- "1 can chopped tomatoes" = 120 g instead of 400 g ("can" was not a unit, and "tomato" was found first
  in the piece weights).
- "1 head of broccoli": "head of" stayed in the name sent to the matcher; 100 g by default.
- "1 bunch fresh coriander": "bunch" stayed in the name; 100 g.
- "a handful of spinach": no amount at all.
- "salt to taste": "to taste" was sent to the matcher as part of the name.

### Decision (`src/parse.py`)
- New units: `can`/`tin` = 400 g (a standard can), `bunch` = 30 g and `handful` = 30 g (herbs, leaves),
  `slice` = 30 g, and `head`, whose weight depends on the vegetable (garlic 50 g, broccoli 350 g,
  lettuce 400 g, cauliflower 600 g, cabbage 900 g; 350 g otherwise).
- For cans the form is kept for the matcher: "1 can chopped tomatoes" → name "canned chopped tomatoes",
  so the processed-food penalty does not push it towards fresh tomatoes.
- "a"/"an" counts as 1 only before a unit ("a handful of", "a pinch of"). "a few sprigs" and "an onion"
  still give no amount, so the app asks instead of guessing.
- Trailing notes are dropped from the name: "to taste", "to serve", "(optional)".
- Default weights are rough averages; the user can still edit grams in the app.

### Tests
The 5 `xfail` cases now pass and became normal tests, plus 4 new ones (tins, head of garlic, slices,
"optional") and a check that "a few sprigs" still asks the user. 37 fast tests pass.

### Effect on the evaluation sets
Parsed output changes for only 3 of the 96 eval lines: "1 head of brocoli" (test) and
"1 bunch fresh coriander" (test) lose "head of"/"bunch" from the name, and "1 can tuna" (dev) becomes
"canned tuna". The demo bolognese is unchanged (its tomatoes are "400g can chopped tomatoes").
Re-run on 2026-11-19 (dev first, then the test set once):

| | Dev correct | Test correct | Test wrong | Test abstained | Test top 5 |
|---|---|---|---|---|---|
| AI matcher, before | 33/48 (69%) | 36/48 (75%) | 5 | 8 | 44/47 (94%) |
| AI matcher, after parser fixes | 33/48 (69%) | 36/48 (75%) | 5 | 8 | **45/47 (96%)** |
| Keyword baseline, after | 22/48 (46%) | 13/48 (27%) | 19 | 17 | n/a |

- Top-1 accuracy is unchanged. Expected: the fixes are about amounts, and the two changed test lines were
  already right ("coriander") or are still blocked by the typo ("brocoli": no answer, score 0.55).
- "brocoli" now has the right food in its top 5 (it was "head of brocoli" before), so top 5 goes from 94% to 96%:
  in the app it is one click instead of a search.
- The real gain is in grams, which the benchmark does not measure: a can is now 400 g, not 120 g
  (≈ 3× too low before), and a head of broccoli 350 g, not 100 g.
- The remaining misses are synonyms and typos (aubergine, mince, scallions, lardons, brocoli, chiken,
  parmesean): that is Step 3.

---

## 2026-11-19: Smoke test and unit tests before changing more code

### Why
Session 3: test the critical path first. The next steps change the parser, the matcher and the swaps,
and any of them could silently break the demo bolognese. We had no automated tests.

### Decision
- `tests/test_smoke.py`: the demo path end to end, with the keyword matcher (runs anywhere) and with the
  AI matcher (marked `slow`, skipped if the model cannot load). Checks: all lines come out, the total is
  ≈ 15.2 kg (AI) / ≈ 15.5 kg (keyword), beef matches "Beef, minced steak" and is > 80% of the total,
  a beef swap exists and every swap saves CO2e. Also three trap lines and the xanthan-gum abstention.
- `tests/test_parse.py`: 19 parser cases that work today, plus 5 known bugs marked `xfail(strict=True)`
  (can of tomatoes = 120 g instead of 400 g, "head of", "bunch", "handful", "to taste" left in the name).
  A fix makes the run fail with XPASS until the marker is removed, so fixes cannot regress unnoticed.
- `tests/test_score_and_data.py`: CO2e maths, unmatched lines kept but not counted, data files consistent
  (category codes exist in foods.csv, swaps use known categories, gold codes exist, test ∩ dev = ∅).
- GitHub Actions runs the fast tests on every push and pull request.

### Team rule
Run `pytest` before every merge into main; the AI smoke test must pass locally.

### Result (2026-11-19)
All tests: 31 passed, 5 expected failures (the known bugs), including the AI smoke test (run by Marc, 55 s).

### Noticed while writing the tests (not fixed here)
The demo bolognese gets the swap "cheese (hard) → yogurt" for parmesan: the dish-blind swap problem (Step 5).

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
