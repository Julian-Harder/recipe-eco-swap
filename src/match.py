"""Map a parsed ingredient name to a food.

Both matchers expose match_food(name) -> (agribalyse_code or None, score), so evaluate.py and
pipeline.py can use either one.
- KeywordMatcher (baseline): synonyms from data/curated/categories.csv, then the category's code.
- AIMatcher: sentence embeddings + cosine similarity over every food in data/index/foods.csv.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from foods import load_foods

CURATED = Path(__file__).resolve().parents[1] / "data" / "curated"

# Chosen on the dev set with src/compare_matchers.py (see LOG.md, 2026-11-09 iteration 2):
# a mpnet model fine-tuned on food names, plus a word-overlap bonus and a small penalty for
# processed foods the recipe line did not ask for. Name cleanup helped the general models but not this one.
DEFAULT_MODEL = "jonny9f/food_embeddings"
DEFAULT_THRESHOLD = 0.80  # below this score the matcher abstains (returns None)
DEFAULT_CLEAN_NAMES = False
DEFAULT_LEXICAL_WEIGHT = 0.3
DEFAULT_PROCESSED_PENALTY = 0.1

# Some models expect an instruction in front of search queries.
QUERY_PREFIXES = {"BAAI/bge-small-en-v1.5": "Represent this sentence for searching relevant passages: "}

# Name parts that carry no meaning once every food in the index is raw (see build_index.py).
UNINFORMATIVE_PARTS = re.compile(r"^(?:raw|plain|prepacked|(?:around )?[\d.,-]+% fat)$", re.I)

# Words marking a processed form. Recipes list plain ingredients, so when the line does not ask
# for one of these, such foods are ranked a little lower. "dried" is left out on purpose:
# dried is the normal form of pulses, pasta and rice.
PROCESSED = {"canned", "frozen", "dehydrated", "puree", "powder", "juice", "paste", "smoked",
             "concentrated", "concentrate", "flakes", "crisps", "sauce", "compote", "coulis", "salted"}
QUERY_ALIASES = {"can": "canned", "tin": "canned", "tinned": "canned", "ground": "powder", "pureed": "puree"}
STOPWORDS = {"of", "or", "and", "with", "w", "the", "a", "an", "in", "for", "to", "fresh", "large",
             "small", "medium", "raw", "grated", "chopped", "sliced", "diced", "whole", "x"}


def clean_name(name: str) -> str:
    """"Beef, minced steak, 10% fat, raw" -> "Beef, minced steak"."""
    parts = [p.strip() for p in name.split(",")]
    kept = [p for p in parts if not UNINFORMATIVE_PARTS.match(p)]
    return ", ".join(kept) or name


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("oes"):
        return word[:-2]  # potatoes -> potato
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]  # courgettes -> courgette
    return word


def words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z]+", text.lower()) if w not in STOPWORDS}


def load_categories(path: Path = CURATED / "categories.csv") -> pd.DataFrame:
    return pd.read_csv(path, dtype={"agribalyse_code": str})


class KeywordMatcher:
    """Match on the synonyms column; the longest matching synonym wins ("olive oil" beats "oil")."""

    name = "keyword"

    def __init__(self, categories: pd.DataFrame | None = None):
        categories = load_categories() if categories is None else categories
        pairs = []
        for _, row in categories.iterrows():
            for syn in str(row["synonyms"]).split("|"):
                syn = syn.strip().lower()
                if syn:
                    pairs.append((syn, row["category"]))
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        self._patterns = [(re.compile(rf"\b{re.escape(s)}\b"), c) for s, c in pairs]
        self._codes = {c: (k if isinstance(k, str) else None)
                       for c, k in zip(categories["category"], categories["agribalyse_code"])}

    def match(self, name: str) -> str | None:
        """Return the category name, or None."""
        name = name.lower()
        for pattern, category in self._patterns:
            if pattern.search(name):
                return category
        return None

    def match_food(self, name: str) -> tuple[str | None, float]:
        code = self._codes.get(self.match(name))
        return code, (1.0 if code else 0.0)


class AIMatcher:
    """Embed the ingredient name and return the most similar food name from the index.

    Uses a pre-trained sentence-transformers model (we have not fine-tuned it ourselves yet). The
    food names are embedded once at start-up; each query is one embedding plus a dot product.

    score = cosine similarity
            + lexical_weight * share of the ingredient's words found in the food name
            - processed_penalty if the food is processed (canned, puree...) and the line didn't ask for it
    """

    name = "ai"

    def __init__(self, foods: pd.DataFrame | None = None, model_name: str = DEFAULT_MODEL,
                 threshold: float = DEFAULT_THRESHOLD, clean_names: bool = DEFAULT_CLEAN_NAMES,
                 lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
                 processed_penalty: float = DEFAULT_PROCESSED_PENALTY):
        from sentence_transformers import SentenceTransformer  # slow import, only when used

        self.foods = load_foods() if foods is None else foods
        self.threshold = threshold
        self.model_name = model_name
        self.clean_names = clean_names
        self.lexical_weight = lexical_weight
        self.processed_penalty = processed_penalty
        self.model = SentenceTransformer(model_name)
        self._prefix = QUERY_PREFIXES.get(model_name, "")
        self._codes = self.foods["code"].tolist()
        names = self.foods["name"].tolist()
        texts = [clean_name(n) for n in names] if clean_names else names
        self._vectors = self.model.encode(texts, batch_size=128, normalize_embeddings=True,
                                          show_progress_bar=False)
        self._food_words = [words(n) for n in names]
        self._processed = np.array([bool(w & PROCESSED) for w in self._food_words])
        self._query_cache: dict[str, np.ndarray] = {}

    def _embed_query(self, text: str) -> np.ndarray:
        if text not in self._query_cache:
            self._query_cache[text] = self.model.encode([self._prefix + text], normalize_embeddings=True,
                                                        show_progress_bar=False)[0]
        return self._query_cache[text]

    def scores(self, name: str) -> np.ndarray:
        name = name.lower()
        scores = self._vectors @ self._embed_query(name)
        query_words = words(name)
        if self.lexical_weight and query_words:
            overlap = np.array([len(query_words & fw) / len(query_words) for fw in self._food_words])
            scores = scores + self.lexical_weight * overlap
        if self.processed_penalty:
            asked = {QUERY_ALIASES.get(w, w) for w in query_words} & PROCESSED
            if not asked:
                scores = scores - self.processed_penalty * self._processed
        return scores

    def top_k(self, name: str, k: int = 5) -> list[tuple[str, float]]:
        """The k best-scoring foods as (code, score), best first."""
        scores = self.scores(name)
        best = np.argsort(-scores)[:k]
        return [(self._codes[i], float(scores[i])) for i in best]

    def match_food(self, name: str) -> tuple[str | None, float]:
        code, score = self.top_k(name, 1)[0]
        return (code if score >= self.threshold else None), score
