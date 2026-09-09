"""Gemeinsame JSON-Lesehilfen für die Content- und Dorf-Lader.

Beide Pakete lesen Content-JSON nach demselben Muster: Datei laden, Fehler in
`ContentError` verpacken, `[lexeme_id, form_key]`-Paare zu `TokenRef`-Tupeln
normalisieren. Damit diese Logik nicht zweimal gepflegt werden muss, liegt sie
hier zentral.
"""

import json
from pathlib import Path

from app.content.models import TokenRef


class ContentError(Exception):
    """Raised when the content package cannot be read or is structurally invalid."""


def _read_json(path: Path) -> dict | list:
    if not path.exists():
        raise ContentError(f"Datei fehlt: {path.name} ({path})")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"Ungültiges JSON in {path.name}: {exc}") from exc


def _token(raw: object, where: str) -> TokenRef:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ContentError(f"Token in {where} muss [lexeme_id, form_key] sein, war: {raw!r}")
    return (str(raw[0]), str(raw[1]))


def _tokens(raw: object, where: str) -> list[TokenRef]:
    if not isinstance(raw, list):
        raise ContentError(f"Tokenliste in {where} muss eine Liste sein, war: {raw!r}")
    return [_token(item, where) for item in raw]
