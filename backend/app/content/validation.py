"""Gemeinsame Prüfhilfen für die Kurs- und Dorf-Validatoren.

Beide Validatoren prüfen `[lexeme_id, form_key]`-Verweise auf dieselbe Weise
gegen das Lexikon. Damit diese Logik nicht zweimal gepflegt werden muss, liegt
sie hier zentral.
"""

from app.content.models import Course, TokenRef


def check_token(course: Course, token: TokenRef, where: str) -> list[str]:
    lexeme_id, form_key = token
    lexeme = course.lexemes.get(lexeme_id)
    if lexeme is None:
        return [f"{where}: Lexem {lexeme_id!r} existiert nicht im Lexikon"]
    if form_key not in lexeme.forms:
        return [f"{where}: Lexem {lexeme_id!r} hat keine Form {form_key!r}"]
    return []
