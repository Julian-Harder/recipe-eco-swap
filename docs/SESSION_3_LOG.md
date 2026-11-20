# Session 3 log: managing the project to the 2 December demo

Course: Perspectives on AI, Business and Sustainability (PAIBS) · Group 8 · Recipe Eco-Score & Swap Assistant
Session: 11 November 2026 · This log written up: 20 November 2026

**How to read this log.** Sections 1–7 follow the seven exercises of Session 3. Where an exercise produced
something in class with other teams (the photo of the wall, the red team's post-its, token counts, the smoke-test
swap), that result is marked **[TEAM TO FILL]**: it must come from the team's notes or photos, not be
reconstructed. Everything else is written from the state of the repository on 20 November and is dated so.

---

## 1. Hill chart and dependency wall (Work 1)

**Photo of the class wall:** [TEAM TO FILL: add the photo from 11 November here]

**Where each component is today (20 November).** Uphill = we do not yet know if or how it will work;
downhill = we know what to do, only work is left. Rule: a component is downhill only if we know how to finish it.

| Component | 11 Nov (from the Session 3 logs) | 20 Nov | Why |
|---|---|---|---|
| Agribalyse index (CO2e per kg) | Downhill (done) | Done | 1,615 raw ingredients, committed |
| Recipe parsing (quantities, units) | Downhill | Done | Cans, heads, bunches, handfuls fixed; 28 tests |
| AI ingredient matching | Uphill → downhill | Done | Holdout 79% vs keyword 48%; top 5 = 100% |
| Synonyms and typos | — | Done | Dev 69% → 85% |
| CO2e calculation | Done | Done | Tested arithmetic, unmatched lines kept |
| Swaps | Downhill (rule) | Downhill | Dish-aware + AI swaps built; **human review not done** |
| Open Food Facts | Stub | Done | Validation set (460 products) + barcode lookup |
| Streamlit interface | Done (local) | Done (local) | Feedback form added |
| **Deployment** | — | **Uphill** | Not yet tried on Streamlit Cloud: we do not know if the 438 MB model fits and loads in time |
| **Outside feedback (level 4)** | — | **Uphill** | Depends on deployment and on finding testers |
| Presentation | — | Uphill | Not started |

**Dependencies (what needs what)**
```
Deployment ──► Outside feedback ──► Level 4 ──► Presentation (results, level)
     ▲
     └── needs repo admin rights (only the repo owner)
Swap review (2 members) ──► Swap results in the log ──► Presentation
Smoke test / code freeze ──► Rehearsal ──► Demo on 2 December
```

**Bottleneck (red dot): deployment.** It is a *people dependency*: Streamlit Community Cloud only deploys from a
repository where the account is admin, and on a personal GitHub repository only the owner is admin. Everything on
the level-4 path waits for it. Mitigation: owner deploys this weekend; fallback in the pre-mortem (section 5).

---

## 2. Press release (Work 2)

*Written as if published on 2 December 2026, after the demo. It is also the script for the presentation.*

**Headline.** Home cooks can now see the climate cost of a recipe, and swap its worst ingredient, in seconds.

**Problem.** People who want to eat more sustainably have no easy way to know which ingredient of a meal matters.
Eco-labels exist for some packaged products, not for a recipe written in your own words, with British or American
names, typos and amounts like "1 can" or "a handful".

**Solution.** Paste a recipe. The assistant reads each line, works out the amount in grams, and matches the
ingredient to one of 1,615 foods in the French public database Agribalyse (ADEME) with an AI model that understands food
names ("beef stock" is not beef, "aubergine" is an eggplant, "chiken" is chicken). It shows the estimated kg CO2e
of the meal and of each ingredient, and suggests swaps that fit the dish: lentils for beef in a bolognese, mackerel
for salmon, never yogurt for the parmesan on top. When it is not sure, it asks the user to pick from its top five.
A barcode box shows what Open Food Facts says about a packaged product.

**User quote (hypothetical, as the exercise asks).** "I knew meat was bad, but I didn't know the beef was 90% of my
bolognese. Half beef, half lentils, and it still tastes like Sunday."

**FAQ 1: Where do the numbers come from?** From Agribalyse (ADEME), the French reference database for the
environmental impact of food, per kg of raw ingredient. They are averages for a food category, not measurements of
a specific product or farm, so the app shows them as estimates ("≈ 15.2 kg CO2e").

**FAQ 2: How accurate is the matching?** On 29 recipe lines written after all our choices were made, the AI picks
the right food 79% of the time, against 48% for simple keyword matching, and the right food is in its top five
every time. On branded product names from Open Food Facts, keyword matching is as good or better; we report that too.

**FAQ 3: What is still faked or simplified?** Nothing in the main loop is faked. Simplifications: amounts for
"1 onion" or "a bunch" are default weights the user can edit; swaps assume the same weight of the replacement;
curated swaps are hand-written rules, AI swaps come from similarity within a food group and were reviewed by
[TEAM TO FILL: result of the swap review].

---

## 3. Buy a feature: scope for 2 December (Work 3)

**In-class token counts:** [TEAM TO FILL: tokens each card received from other teams on 11 November, and which
team(s) invested most]

Cards as they stand on 20 November (price in tokens = effort, 1–3):

| Feature | Price | Done when | MoSCoW | Status 20 Nov |
|---|---|---|---|---|
| End-to-end app: recipe → CO2e → swaps | 3 | Bolognese runs in the app; smoke test passes | Must | Done |
| AI matcher beats keyword baseline | 3 | Holdout accuracy > baseline, logged | Must | Done (79% vs 48%) |
| Parser handles common amounts | 1 | Can/head/bunch/handful tests pass | Must | Done |
| Synonyms and typos | 2 | Dev accuracy improves, no more wrong answers | Should | Done (69% → 85%) |
| Open Food Facts used for real | 2 | Validation set + barcode lookup, result logged | Must (course) | Done |
| Dish-aware swaps + AI swaps | 2 | No parmesan → yogurt; review ≥ 2 members | Should | Built; review pending |
| Deployed app | 1 | Public URL loads the bolognese | Must (level 4) | Pending |
| Feedback form + test session | 2 | ≥ 3 outside testers, findings in the log | Must (level 4) | Form done; session pending |
| Strip descriptive words before matching | 1 (spike) | Dev accuracy up, time-box 1 day | Could | Not started |
| Fine-tune the model on OFF pairs | 3 (spike) | Beats current model on dev, time-box 3 days | Won't (Term 2) | Not started |
| Nutrition / price comparison | 3 | — | Won't | Out of scope |

**Cut list (not before 2 December):** fine-tuning, nutrition and price comparison, quantity-aware swaps
(replacement weight). Spike to run only if everything else is done: stripping descriptive words.

---

## 4. Why projects fail: Healthcare.gov and Knight Capital (Work 4)

[TEAM TO FILL: the team's own post-it answers from class]

What we took from it, applied: the parts are integrated through one smoke test of the exact demo path
(`tests/test_smoke.py`), run by CI on every push (fast tests) and locally before every merge (AI test), so
integration is not left to the last week.

---

## 5. Pre-mortem with a red team (Work 5)

**Red team's post-its (from the paired team on 11 November):** [TEAM TO FILL]

**Our own pre-mortem, 20 November.** *Assume the demo failed on 2 December. Why?*

| # | Risk | Likelihood | Impact | Fallback |
|---|---|---|---|---|
| 1 | **The deployed app does not work on demo day**: never deployed, out of memory with the 438 MB model, or asleep and slow to wake | Medium | High | Run the demo locally on a laptop that already has the model; open the hosted app 10 min before to wake it. Reduced on 20 Nov: CI now installs the deployment dependencies and runs the AI demo test on every push |
| 2 | **No outside feedback, so no level 4** | Medium | Medium | Ask another team to test it during the session and log their feedback live |
| 3 | **A wrong match on stage** ("red wine vinegar" → red wine, onion → dried onion) makes the number look absurd | Low (demo path is tested) | High | Demo only the tested bolognese path; show the top-5 dropdown as the safety net and name the limitation |
| 4 | A last-minute change breaks the demo | Low | High | Code freeze on 28 November; smoke test must pass before every merge |
| 5 | Only two members can run the project | Medium | Medium | Everyone does a fresh install from the README before the freeze (section 7) |

**Top 3:** risks 1, 2 and 3.

**Decision rules (state + date, decided before the result):**
- **Risk 1:** if the app is not deployed and loading the bolognese **by 25 November**, *revise*: deploy on
  Hugging Face Spaces from a member's fork; if that also fails **by 28 November**, *stop* hosting and demo locally,
  declared in the log.
- **Risk 2:** if fewer than 3 people outside the team have used the app **by 28 November**, run the test with
  another class team on 2 December and log it there.
- **Risk 3:** the smoke test must pass at the code freeze (28 November); if it fails, *stop* new work until it passes.

---

## 6. Milestones and team rules (Work 6)

**Milestones to 2 December**

Owners marked *(proposed)* are a suggestion to be confirmed by the team.

| Date | Milestone | Done when | Owner |
|---|---|---|---|
| 19 Nov | Tests, parser, matcher, holdout, OFF, swaps | Merged in `main`, logged | Marc (done) |
| 20 Nov | CI runs the AI demo test with the deployment dependencies | `full-tests` job green on `main` | Marc |
| 22 Nov | App deployed | Public URL loads the bolognese | Julian (only the repo owner can deploy) |
| 25 Nov | Swap review | Two members judged the swaps independently; result in LOG.md | Ian + Justin *(proposed: neither wrote the swap code, so less bias)* |
| 25 Nov | Fresh install by everyone | Each member ran `python -m pytest` from a fresh clone | Everyone |
| 27 Nov | Feedback session | ≥ 3 outside testers; CSV downloaded; findings in LOG.md | Luuk *(proposed)* |
| 27 Nov | Fill the [TEAM TO FILL] parts of this log | Photo, red-team post-its, tokens, smoke-test swap added | Justin *(proposed)* |
| 27 Nov | Slides draft | Architecture, real vs faked, results, limitations, roadmap, log slide | Marc + Ian *(proposed)* |
| **28 Nov** | **Code freeze** | Only bug fixes after this date; CI green | Marc *(proposed: checks CI before each merge)* |
| 30 Nov | Rehearsal | Full demo run on the deployed app, timed | Everyone |
| 2 Dec | Demo day | — | Everyone |

**Team rules**

| Area | Chosen rule |
|---|---|
| Branches | One branch per task, merged within 1–2 days |
| Review | Every pull request reviewed by another member before merging |
| Integration | Merge into `main` at least twice a week |
| Testing | `pytest` (smoke test of the demo path) before every merge; CI runs the fast tests on every push |

**Honest note on review:** pull requests #2–#9 (19 November) were merged by their author without a second
reviewer, to move fast before the freeze. From 20 November the review rule applies; PRs #2–#9 can still be
reviewed after the fact.

---

## 7. Smoke-test swap (Work 7)

**With another team on 11 November:** [TEAM TO FILL: where they got stuck using only our README, who fixed what]

**Fresh-install test, 19 November (Marc, macOS, fresh clone following the README):**

| Where it got stuck | Cause | Fix | Status |
|---|---|---|---|
| `gh auth login` could not save the login | `~/.config` owned by root on that laptop | `sudo chown -R $(whoami) ~/.config` | Machine-specific, noted |
| AI tests skipped (3 skipped) | Anaconda's `pytest` ran instead of the one in `.venv` | Run `python -m pytest`; `conda deactivate` before activating `.venv` | README updated |
| Imports failed after moving the folder | A virtual environment stops working when moved | Delete and recreate `.venv` | README updated |
| First AI run slow | 438 MB model download | Expected; noted in README | — |

After the fixes, a fresh clone runs the full suite (31 tests at the time, now 77) and the app.

**Fresh-clone test in a clean Linux environment, 20 November** (Python 3.13, only the README, nothing pre-installed):

| Step | Result |
|---|---|
| `git clone`, `python3 -m venv .venv`, `pip install -r requirements.txt` | Works, but **6.1 GB and ~6 min**: on Linux pip installs the GPU build of PyTorch. Fix: README now says to install CPU-only PyTorch first on Linux/Windows without a GPU |
| `python -m pytest -rs` | 74 passed, 3 skipped; the skips name the cause (the model host was not reachable from that network), as designed |
| `python src/pipeline.py --keyword` | Bolognese, total and swaps printed (beef → lentils / beans; no parmesan → yogurt) |
| `streamlit run src/app.py` | App starts and answers (HTTP 200) |

To make the AI part of this check automatic, CI now has a `full-tests` job: clean Ubuntu, Python 3.12, the
deployed app's own `src/requirements.txt`, model download, and every test including the AI smoke test. A missing
model fails the job instead of skipping it.

**To do before the freeze:** every member runs the fresh install once (milestone 25 November) and adds any new
stuck point here.
