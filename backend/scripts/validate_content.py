"""Validate the course content package. Usage: python -m scripts.validate_content [dir]"""
import sys
from pathlib import Path

from app.content.loader import ContentError, load_course
from app.content.validator import validate_course

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "content" / "ru"


def main(argv: list[str]) -> int:
    content_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_DIR
    try:
        course = load_course(content_dir)
    except ContentError as exc:
        print(f"FEHLER beim Laden: {exc}")
        return 2

    errors = validate_course(course)
    if errors:
        print(f"{len(errors)} Problem(e) in {content_dir}:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"OK — {len(course.units)} Einheiten, {len(course.lexemes)} Lexeme, "
        f"{len(course.screening)} Sonden"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
