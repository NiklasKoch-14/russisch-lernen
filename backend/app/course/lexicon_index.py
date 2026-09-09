"""Rueckwaerts-Index ueber alle Wortformen des Kurses.

Das Lexikon kennt zu jedem Wort das vollstaendige Paradigma. Dreht man diese
Abbildung um, laesst sich zu einem getippten Wort sagen, *welche* Form es ist —
und damit eine falsche Endung benennen, ohne dass ein Sprachmodell einen
einzigen russischen Buchstaben erzeugt.

Mehrdeutigkeit ist der Normalfall (рабо́те ist Dativ und Praepositiv), deshalb
steht hinter jedem Eintrag eine Liste.
"""

from app.content.models import Course, TokenRef
from app.course.normalize import normalize

LexiconIndex = dict[str, list[TokenRef]]


def build_index(course: Course) -> LexiconIndex:
    index: LexiconIndex = {}
    for lexeme_id, lexeme in course.lexemes.items():
        for form_key, form in lexeme.forms.items():
            index.setdefault(normalize(form.text), []).append((lexeme_id, form_key))
    return index


_cached: tuple[Course, LexiconIndex] | None = None


def index_for(course: Course) -> LexiconIndex:
    """Der Index zu diesem Kurs, einmal gebaut.

    Ein Eintrag genuegt: der Prozess laedt genau einen Kurs. Verglichen wird
    ueber die Identitaet des Kursobjekts, damit ein anderer Kurs — in den Tests
    der Normalfall — nie den fremden Index bekommt.
    """
    global _cached
    if _cached is None or _cached[0] is not course:
        _cached = (course, build_index(course))
    return _cached[1]


def lookup(course: Course, word: str) -> list[TokenRef]:
    """Alle Formen, die zu diesem getippten Wort passen."""
    return index_for(course).get(normalize(word), [])
