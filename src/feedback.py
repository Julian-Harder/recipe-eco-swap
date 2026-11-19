"""Save what testers tell us about the app, one row per submission, to a CSV file.

Level 4 of the course: someone outside the team used the tool and their feedback is logged.

Note for the deployed app (Streamlit Community Cloud): its disk is wiped when the app restarts or
sleeps, so download the CSV from the sidebar ("For the team") after every test session and copy what
matters into LOG.md. Locally the file stays in data/feedback/ (not in git: it may hold names).
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

FEEDBACK_FILE = Path(__file__).resolve().parents[1] / "data" / "feedback" / "feedback.csv"
FIELDS = ["timestamp", "tester", "useful", "wrong_lines", "comment", "recipe", "total_kg_co2e", "matches"]


def save_feedback(tester: str, useful: str | None, wrong_lines: list[str], comment: str, recipe: str,
                  total_kg_co2e: float, matches: list[dict], path: Path = FEEDBACK_FILE) -> dict:
    """Append one submission and return the row that was written."""
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tester": tester.strip(),
        "useful": useful or "",
        "wrong_lines": " | ".join(wrong_lines),
        "comment": comment.strip(),
        "recipe": recipe.strip(),
        "total_kg_co2e": round(float(total_kg_co2e), 2),
        # What the app showed for each line, so a wrong match can be traced later.
        "matches": json.dumps([{"line": m["line"], "food": m.get("food"), "grams": m.get("grams")}
                               for m in matches], ensure_ascii=False),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    return row


def read_feedback(path: Path = FEEDBACK_FILE) -> str:
    """The whole CSV as text (empty string if nobody has given feedback yet)."""
    return path.read_text(encoding="utf-8") if path.exists() else ""
