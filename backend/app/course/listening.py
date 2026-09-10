"""Hörgespräche: auswählen, anzeigen, prüfen.

Zwei Dinge trennt dieses Modul sauber: was der Client sehen darf (Ton und
Optionen) und was beim Server bleibt (die richtige Option, der Titel und die
Übersetzungen). Sonst stünde die Antwort im DOM, bevor gefragt wurde.
"""

from sqlite3 import Connection

from app.config import settings
from app.content.models import Course, Dialog
from app.course.shuffle import shuffled_order
from app.repositories import listening_repo, progress_repo
from app.repositories.profile_repo import get_or_create_profile


def reached_unit(conn: Connection) -> int:
    """Bis wohin der Lernende kommt — abgeschlossen oder eingestuft.

    Wer sich einstufen lässt, hat die Einheiten davor nie angefasst und kann
    sie trotzdem; ohne die Einstufung bliebe der Tab für ihn leer.
    """
    completed = [
        progress.unit_id
        for progress in progress_repo.all_progress(conn).values()
        if progress.status == "completed"
    ]
    profile = get_or_create_profile(conn, settings.default_language)
    placed = (profile.placement_unit or 1) - 1
    return max([*completed, placed, 0])


def unlocked(course: Course, reached: int) -> list[Dialog]:
    return [dialog for dialog in course.dialogs.values() if dialog.min_unit <= reached]


def first_locked_unit(course: Course, reached: int) -> int | None:
    """Die Einheit, die das nächste Gespräch öffnet — für den leeren Tab."""
    kommend = [d.min_unit for d in course.dialogs.values() if d.min_unit > reached]
    return min(kommend) if kommend else None


def pick_dialog(course: Course, conn: Connection, *, now: str) -> tuple[Dialog, str] | None:
    """Das am längsten nicht gehörte freigeschaltete Gespräch, dazu ein Seed."""
    candidates = unlocked(course, reached_unit(conn))
    if not candidates:
        return None
    played = listening_repo.last_played(conn)
    candidates.sort(key=lambda dialog: (played.get(dialog.id, ""), dialog.id))
    dialog = candidates[0]
    return dialog, f"{dialog.id}:{now}"


def _option_order(dialog: Dialog, seed: str) -> list[int]:
    """Die Reihenfolge der Optionen — aus dem Seed, also auf beiden Seiten gleich.

    Ohne das Mischen stünde die richtige Antwort bei jedem Durchlauf an
    derselben Stelle.
    """
    return shuffled_order(f"{seed}:options", len(dialog.options_de))


def shuffled_options(dialog: Dialog, seed: str) -> list[str]:
    return [dialog.options_de[position] for position in _option_order(dialog, seed)]


def dialog_payload(course: Course, dialog: Dialog, seed: str) -> dict:
    """Was der Client bekommt: genug zum Hören, nichts zum Antworten."""
    return {
        "dialog_id": dialog.id,
        "seed": seed,
        "speakers": [
            {"name_ru": speaker.name_ru, "name_de": speaker.name_de, "voice": speaker.voice}
            for speaker in dialog.speakers
        ],
        "lines": [
            {
                "speaker": line.speaker,
                "text": " ".join(course.form(token).text for token in line.tokens),
                "translit": " ".join(course.form(token).translit for token in line.tokens),
            }
            for line in dialog.lines
        ],
        "question_de": dialog.question_de,
        "options_de": shuffled_options(dialog, seed),
    }


def check_answer(dialog: Dialog, seed: str, option_index: int) -> tuple[bool, int]:
    """(richtig?, Index der richtigen Option in der gemischten Liste)."""
    order = _option_order(dialog, seed)
    correct_index = order.index(dialog.correct_index)
    return option_index == correct_index, correct_index
