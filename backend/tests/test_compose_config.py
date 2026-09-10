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


def _tts_environment() -> dict[str, str]:
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    entries = compose["services"]["tts"]["environment"]
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


def test_beide_dienste_sprechen_mit_denselben_stimmen():
    """Der Stimmname geht in den Zwischenspeicher-Schlüssel ein.

    Laufen backend und tts auseinander, liefert der Zwischenspeicher Ton, der
    mit einer anderen Stimme erzeugt wurde — und niemand merkt es, weil der
    Schlüssel passt.
    """
    backend = _backend_environment()
    tts = _tts_environment()
    for name in ("PIPER_VOICE", "PIPER_VOICE_FEMALE"):
        assert name in backend and name in tts, f"{name} fehlt bei einem der beiden Dienste"
        assert backend[name] == tts[name], (
            f"{name}: backend {backend[name]!r} gegen tts {tts[name]!r}"
        )


def _service_environment(name: str) -> dict[str, str]:
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    entries = compose["services"][name].get("environment", [])
    return dict(entry.split("=", 1) for entry in entries)


def test_ein_dienst_zieht_das_sprachmodell():
    """Ohne ihn startet Ollama leer.

    Das Backend fängt den Fehler still auf und liefert statt der Erklärung die
    Regel der Einheit — es sieht also aus, als liefe alles, und niemand merkt,
    dass das Modell fehlt.
    """
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    assert "ollama-init" in compose["services"], (
        "Kein Dienst zieht das Modell — nach einem frischen Clone bliebe Ollama leer"
    )


def test_backend_und_modell_zug_meinen_dasselbe_modell():
    """Sonst zöge der eine Dienst ein Modell, das der andere nie anspricht."""
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    gezogen = " ".join(compose["services"]["ollama-init"]["entrypoint"])
    modell = _service_environment("backend")["OLLAMA_MODEL"]
    assert modell in gezogen, f"backend will {modell}, gezogen wird: {gezogen}"


def test_der_default_im_code_passt_zur_compose_datei():
    """Wer ohne Compose startet, bekommt sonst ein anderes Modell als im Betrieb."""
    from app.config import Settings

    modell = _service_environment("backend")["OLLAMA_MODEL"]
    vorgabe = modell.split(":-", 1)[1].rstrip("}")
    assert Settings().ollama_model == vorgabe
