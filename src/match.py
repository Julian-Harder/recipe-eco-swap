"""Map a parsed ingredient name to a category in data/curated/categories.csv."""
import re
from pathlib import Path

import pandas as pd

CURATED = Path(__file__).resolve().parents[1] / "data" / "curated"


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

    def match(self, name: str) -> str | None:
        name = name.lower()
        for pattern, category in self._patterns:
            if pattern.search(name):
                return category
        return None


class AIMatcher:
    """Same interface as KeywordMatcher, backed by an LLM or embeddings."""

    name = "ai"

    def __init__(self, categories: pd.DataFrame | None = None):
        self.categories = load_categories() if categories is None else categories

    def match(self, name: str) -> str | None:
        # TODO: ask a model to pick one of self.categories["category"] (or None) for `name`.
        raise NotImplementedError("AIMatcher is not implemented yet")
