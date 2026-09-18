"""Wächter dafür, dass der Lernfortschritt den Rechner nie verlässt.

Im Repo stehen nur Code und Kursinhalte. Alles Persönliche — Profil, gelöste
Aufgaben, Wiederholungsplan — liegt in einer SQLite-Datei, die erst beim
Starten entsteht. Wer klont, fängt deshalb bei null an und schreibt nur in
seine eigene Datei. Diese Tests halten beide Hälften der Zusage fest: keine
Datenbank im Archiv, und keine, die ein unbedachtes `git add .` einsammeln
könnte.
"""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]

DATENBANK_ENDUNGEN = (".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3")

MOEGLICHE_ABLAGEN = (
    "speaker.db",
    "speaker.db-wal",
    "backend/speaker.db",
    "backend/data/speaker.db",
    "fortschritt.sqlite3",
)
"""Pfade, an denen eine Datenbank landen kann, wenn jemand `DB_PATH` umsetzt."""


def _ohne_git_ueberspringen() -> None:
    if shutil.which("git") is None or not (REPO / ".git").exists():
        pytest.skip("Kein git-Arbeitsbaum — die Ignore-Regeln sind hier nicht prüfbar")


def test_im_archiv_liegt_keine_datenbank():
    _ohne_git_ueberspringen()
    versioniert = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    gefunden = [p for p in versioniert if p.endswith(DATENBANK_ENDUNGEN)]
    assert not gefunden, (
        "Diese Dateien sind versioniert und trügen fremden Fortschritt in jeden Clone: "
        f"{gefunden}"
    )


@pytest.mark.parametrize("pfad", MOEGLICHE_ABLAGEN)
def test_eine_datenbank_im_arbeitsbaum_wird_ignoriert(pfad: str):
    _ohne_git_ueberspringen()
    ignoriert = subprocess.run(
        ["git", "check-ignore", "-q", pfad], cwd=REPO
    ).returncode == 0
    assert ignoriert, (
        f"{pfad} wäre versionierbar — ein `git add .` nähme den Lernfortschritt mit"
    )


def test_der_projektname_steht_in_der_compose_datei():
    """Sonst leitet Compose ihn aus dem Verzeichnisnamen ab.

    Der Name bestimmt, wie das Volume heißt. Hinge er am Ordner, zeigte jede
    Anleitung zum Sichern oder Zurücksetzen auf einen Namen, den es beim
    Nachmachenden gar nicht gibt — und ein Umbenennen des Ordners ließe den
    Fortschritt scheinbar verschwinden.
    """
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    assert "name" in compose, "docker-compose.yml setzt keinen Projektnamen"
    assert compose["name"].endswith("speaker}") or compose["name"] == "speaker", (
        f"Unerwarteter Projektname {compose['name']!r} — die Vorgabe soll `speaker` bleiben, "
        "damit vorhandene Volumes weiter gefunden werden"
    )
