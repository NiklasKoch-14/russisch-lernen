import re
from pathlib import Path

SUFFIXES = (".webp", ".png", ".svg")
"""Suchreihenfolge: ein extern erzeugtes Rasterbild schlägt die gezeichnete SVG."""

MEDIA_TYPES = {".webp": "image/webp", ".png": "image/png", ".svg": "image/svg+xml"}

_SAFE_ID = re.compile(r"[a-z0-9_]+")


def art_path(art_dir: Path, art_id: str) -> Path | None:
    """Die Bilddatei zu einer Id, oder None.

    Die Id kommt aus einer URL. Sie muss deshalb streng geprueft werden, sonst
    liesse sich ueber `../` aus dem Bildverzeichnis herauslesen.
    """
    if not _SAFE_ID.fullmatch(art_id):
        return None
    for suffix in SUFFIXES:
        candidate = art_dir / f"{art_id}{suffix}"
        if candidate.is_file():
            return candidate
    return None
