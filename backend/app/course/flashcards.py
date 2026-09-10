"""Karteikarten: die nackte Vokabel, drei Optionen, beide Richtungen.

Getrennt von der Wiederholung in `srs/`: dort geht es um Wortformen im Satz
(де́лаю gegen де́лает), hier um das Wort im Wörterbuch. Ein Fehlklick auf einer
Karte soll den Wiederholungsplan des Kurses nicht verstellen — deshalb eine
eigene Tabelle und keine Berührung mit SM-2.

Wie überall im Projekt bleibt die Lösung beim Server: die Optionen werden aus
dem Seed gemischt, der Client schickt nur den Index zurück.
"""

from sqlite3 import Connection

from app.config import settings
from app.content.models import Course, Lexeme
from app.course.presenter import citation_form
from app.course.shuffle import shuffled_order
from app.repositories import flashcard_repo, progress_repo
from app.repositories.profile_repo import get_or_create_profile

CARDS_PER_ROUND = 12
OPTIONS = 3
DIRECTIONS = ("ru_de", "de_ru", "mixed")


def reached_unit(conn: Connection) -> int:
    """Bis wohin der Lernende kommt — abgeschlossen oder eingestuft.

    Dieselbe Regel wie bei den Hörgesprächen: wer sich einstufen ließ, hat die
    Einheiten davor nie angefasst und kann sie trotzdem.
    """
    completed = [
        progress.unit_id
        for progress in progress_repo.all_progress(conn).values()
        if progress.status == "completed"
    ]
    profile = get_or_create_profile(conn, settings.default_language)
    placed = (profile.placement_unit or 1) - 1
    return max([*completed, placed, 0])


def known_lexemes(course: Course, reached: int) -> list[Lexeme]:
    """Die Vokabeln, die der Kurs bis zu dieser Einheit eingeführt hat.

    Buchstaben zählen nicht mit: sie haben keine Bedeutung, die man abfragen
    könnte, und stehen in Stufe 0 nur zum Lesenlernen.
    """
    lexemes: list[Lexeme] = []
    for unit in course.ordered_units():
        if unit.id > reached:
            break
        for lexeme_id in unit.new_lexemes:
            lexeme = course.lexemes.get(lexeme_id)
            if lexeme is not None and lexeme.pos != "letter":
                lexemes.append(lexeme)
    return lexemes


def _rank(lexeme: Lexeme, answers: dict[str, tuple[str, bool]]) -> tuple[int, str, str]:
    """Sortierschlüssel: erst die zuletzt falschen, dann die neuen, dann die alten."""
    answer = answers.get(lexeme.id)
    if answer is None:
        return (1, "", lexeme.id)
    answered_at, correct = answer
    return (0 if not correct else 2, answered_at, lexeme.id)


def _card_direction(direction: str, lexeme_id: str, seed: str) -> str:
    if direction != "mixed":
        return direction
    # Aus dem Seed, nicht zufällig: dieselbe Runde muss sich zweimal gleich bauen
    # lassen, sonst stimmt die Prüfung nicht mehr mit der gezeigten Karte überein.
    return "ru_de" if shuffled_order(f"{seed}:dir:{lexeme_id}", 2)[0] == 0 else "de_ru"


def _text(course: Course, lexeme: Lexeme) -> dict:
    ref = citation_form(course, lexeme.id)
    form = course.form(ref) if ref else None
    return {
        "text": form.text if form else lexeme.lemma,
        "translit": form.translit if form else "",
    }


def _distractors(pool: list[Lexeme], lexeme: Lexeme, seed: str) -> list[Lexeme]:
    """Zwei Ablenker — bevorzugt aus derselben Wortart.

    Gleiche Bedeutungen fallen raus: zwei Optionen, die dasselbe heißen, hätten
    keine eindeutige Antwort.
    """

    def passt(other: Lexeme) -> bool:
        return other.id != lexeme.id and other.gloss_de != lexeme.gloss_de

    gleiche = [other for other in pool if passt(other) and other.pos == lexeme.pos]
    andere = [other for other in pool if passt(other) and other.pos != lexeme.pos]

    gewaehlt: list[Lexeme] = []
    for kandidaten, marke in ((gleiche, "same"), (andere, "other")):
        if len(gewaehlt) >= OPTIONS - 1 or not kandidaten:
            continue
        order = shuffled_order(f"{seed}:{marke}:{lexeme.id}", len(kandidaten))
        for position in order:
            kandidat = kandidaten[position]
            if any(kandidat.gloss_de == genommen.gloss_de for genommen in gewaehlt):
                continue
            gewaehlt.append(kandidat)
            if len(gewaehlt) == OPTIONS - 1:
                break
    return gewaehlt


def _option_order(lexeme_id: str, seed: str, count: int) -> list[int]:
    return shuffled_order(f"{seed}:options:{lexeme_id}", count)


def _card(course: Course, lexeme: Lexeme, pool: list[Lexeme], *, direction: str, seed: str) -> dict:
    kandidaten = [lexeme, *_distractors(pool, lexeme, seed)]
    order = _option_order(lexeme.id, seed, len(kandidaten))
    optionen = [kandidaten[position] for position in order]

    if direction == "ru_de":
        return {
            "lexeme_id": lexeme.id,
            "direction": direction,
            "prompt_ru": _text(course, lexeme),
            "prompt_de": None,
            "options_de": [option.gloss_de for option in optionen],
            "options_ru": [],
        }
    return {
        "lexeme_id": lexeme.id,
        "direction": direction,
        "prompt_ru": None,
        "prompt_de": lexeme.gloss_de,
        "options_de": [],
        "options_ru": [_text(course, option) for option in optionen],
    }


def build_round(
    course: Course,
    conn: Connection,
    *,
    direction: str,
    seed: str,
    count: int = CARDS_PER_ROUND,
) -> list[dict]:
    """Eine Runde Karten — ohne die Lösungen."""
    pool = known_lexemes(course, reached_unit(conn))
    if len(pool) < OPTIONS:
        # Mit zwei bekannten Wörtern gäbe es keine drei Optionen.
        return []

    # Die Reihenfolge ist die Aussage: zuletzt falsche zuerst, dann die neuen.
    # Nachträglich zu mischen würde genau das wieder zunichtemachen — gemischt
    # werden nur die Optionen auf der Karte.
    answers = flashcard_repo.last_answers(conn)
    gereiht = sorted(pool, key=lambda lexeme: _rank(lexeme, answers))[:count]

    return [
        _card(
            course,
            lexeme,
            pool,
            direction=_card_direction(direction, lexeme.id, seed),
            seed=seed,
        )
        for lexeme in gereiht
    ]


def check_answer(
    course: Course, conn: Connection, lexeme_id: str, *, seed: str, option_index: int
) -> tuple[bool, int]:
    """(richtig?, Index der richtigen Option) — dieselbe Mischung wie beim Bauen.

    Der Stapel muss derselbe sein wie beim Zeigen: die Ablenker werden daraus
    gezogen, und mit einem anderen Stapel läge die richtige Option woanders.
    Die Richtung spielt dagegen keine Rolle — sie dreht nur, was auf den
    Optionen steht, nicht ihre Reihenfolge.
    """
    lexeme = course.lexemes[lexeme_id]
    pool = known_lexemes(course, reached_unit(conn))
    kandidaten = [lexeme, *_distractors(pool, lexeme, seed)]
    order = _option_order(lexeme_id, seed, len(kandidaten))
    correct_index = order.index(0)
    return option_index == correct_index, correct_index


def solution(course: Course, lexeme_id: str) -> dict:
    """Was nach der Antwort gezeigt wird."""
    lexeme = course.lexemes[lexeme_id]
    return {**_text(course, lexeme), "gloss_de": lexeme.gloss_de}
