"""Level 2: skeleton recipe -> eco-score -> swap pipeline."""


def parse_recipe(text: str) -> list[str]:
    """Split a recipe into ingredient names (one per line for now)."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def match_ingredient(name: str, agribalyse):
    """TODO: find the closest Agribalyse product for an ingredient."""
    raise NotImplementedError


def score_recipe(ingredients, agribalyse):
    """TODO: sum per-ingredient impact (e.g. kg CO2 eq / kg)."""
    raise NotImplementedError


def suggest_swaps(ingredients, agribalyse):
    """TODO: propose lower-impact alternatives in the same food group."""
    raise NotImplementedError


if __name__ == "__main__":
    print(parse_recipe("beef\nrice\nbutter"))
