"""Validate the course and village content. Usage: python -m scripts.validate_content [dir]"""
import sys
from pathlib import Path

from app.content.loader import ContentError, load_course
from app.content.morphology import check_morphology
from app.content.validator import validate_course
from app.game.loader import load_village
from app.game.validator import validate_village

ROOT = Path(__file__).resolve().parents[2] / "content"
DEFAULT_DIR = ROOT / "ru"
DEFAULT_GAME_DIR = ROOT / "game"


def main(argv: list[str]) -> int:
    content_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_DIR
    game_dir = content_dir.parent / "game"
    try:
        course = load_course(content_dir)
        village = load_village(game_dir)
    except ContentError as exc:
        print(f"FEHLER beim Laden: {exc}")
        return 2

    errors = (
        validate_course(course)
        + check_morphology(course)
        + validate_village(course, village, game_dir / "art")
    )
    if errors:
        print(f"{len(errors)} Problem(e) in {content_dir.parent}:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"OK — {len(course.units)} Einheiten, {len(course.lexemes)} Lexeme, "
        f"{len(course.screening)} Sonden, {len(course.dialogs)} Gespräche, "
        f"{len(village.places)} Orte, {len(village.scenes)} Szenen"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
