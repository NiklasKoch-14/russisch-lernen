"""Prüft den Betriebsstand aus `docker-compose.yml` gegen das Image.

Die übrigen Tests laufen im Repo-Baum, wo die Pfad-Defaults aus `config.py`
zufällig stimmen: sie zeigen von `backend/app/config.py` aus zwei Ebenen hoch
auf `content/`. Im Image liegt dieselbe Datei unter `/app/app/config.py`, zwei
Ebenen höher ist also `/` — der Default zeigt dort auf `/content` und damit ins
Leere. Jedes Inhaltsverzeichnis muss deshalb in der Compose-Datei gesetzt sein,
sonst läuft der Kurs oder das Dorf nur lokal.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]

CONTENT_SETTINGS = ("CONTENT_DIR", "GAME_DIR")
"""Die Einstellungen, deren Default aus dem Modulpfad abgeleitet wird."""


def _backend_environment() -> dict[str, str]:
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    entries = compose["services"]["backend"]["environment"]
    return dict(entry.split("=", 1) for entry in entries)


def _image_content_dir() -> str:
    """Wohin das Dockerfile `content/` kopiert — absolut, vom WORKDIR aus."""
    dockerfile = (REPO / "backend" / "Dockerfile").read_text(encoding="utf-8")
    workdir = re.search(r"^WORKDIR\s+(\S+)", dockerfile, re.MULTILINE)
    copied = re.search(r"^COPY\s+content\s+\./(\S+)", dockerfile, re.MULTILINE)
    assert workdir is not None, "Das Dockerfile setzt kein WORKDIR"
    assert copied is not None, "Das Dockerfile kopiert content nicht mehr relativ"
    return f"{workdir.group(1).rstrip('/')}/{copied.group(1)}"


def test_das_backend_bekommt_jedes_inhaltsverzeichnis_als_pfad_im_image():
    environment = _backend_environment()
    content_dir = _image_content_dir()
    for name in CONTENT_SETTINGS:
        assert name in environment, (
            f"{name} fehlt in docker-compose.yml — im Container zeigt der Default ins Leere"
        )
        assert environment[name].startswith(f"{content_dir}/"), (
            f"{name}={environment[name]} liegt nicht unter {content_dir}, "
            "wohin das Dockerfile den Inhalt kopiert"
        )


def test_die_gesetzten_verzeichnisse_gibt_es_auch_im_repo():
    """Ein Tippfehler im Pfad fällt sonst erst im laufenden Container auf."""
    content_dir = _image_content_dir()
    for name, value in _backend_environment().items():
        if name in CONTENT_SETTINGS:
            relative = value[len(content_dir) + 1 :]
            assert (REPO / "content" / relative).is_dir(), (
                f"{name}={value} zeigt auf content/{relative}, das es im Repo nicht gibt"
            )
