"""Die Formen des Lexikons gegen ein russisches Wörterbuch prüfen.

Der Validator sichert Struktur und Betonung, aber nicht, ob unter
`(де́лать, prs.3sg)` wirklich де́лает steht. Das übernimmt hier pymorphy3 mit
dem OpenCorpora-Wörterbuch: eine Form gilt als richtig, wenn das Wörterbuch
sie mit den Merkmalen ihres Schlüssels kennt und sie zum selben Wort gehört
wie die Grundform des Lexems.

„Zum selben Wort" statt „dieselbe Grundform", weil das Wörterbuch Mehrzahlwörter
anders einordnet: де́ньги steht dort unter деньга́, де́ти unter ребёнок.

Betonung kennt das Wörterbuch nicht — die bleibt beim Validator. Die Prüfung
läuft nur in `make validate` und den Tests, nicht beim Start: der Dienst
braucht das Wörterbuch nicht.
"""

from functools import cache

from app.content.formkeys import allowed_form_keys, form_label_de, with_article_de
from app.content.models import Course, Lexeme

STRESS = "́"

CHECKED_POS = frozenset({"noun", "verb", "adj", "pron", "num"})
"""Wortarten mit Formen. Adverbien, Partikeln und Buchstaben haben nur `base`."""

# Je Merkmal die Grammeme, von denen eines zutreffen muss. Das erste ist das
# übliche und wird für den Vorschlag benutzt: gen2 und loc2 sind die
# Nebenformen (ча́ю, в лесу́), die das Wörterbuch getrennt führt.
_CASE = {
    "nom": ("nomn",),
    "gen": ("gent", "gen2"),
    "dat": ("datv",),
    "acc": ("accs",),
    "ins": ("ablt",),
    "prp": ("loct", "loc2"),
}
_NUMBER = {"sg": "sing", "pl": "plur"}
_GENDER = {"m": "masc", "f": "femn", "n": "neut", "pl": "plur"}
_PERSON = {"1": "1per", "2": "2per", "3": "3per"}
_TENSE = {"prs": "pres", "fut": "futr"}

# Welche Lesarten der Grundform zur Wortart passen — nur aus denen kommt ein
# Vorschlag, sonst schlüge das Wörterbuch für стекло́ das Verb vor.
_POS_TAGS = {
    "noun": {"NOUN"},
    "verb": {"INFN", "VERB"},
    "adj": {"ADJF"},
    "pron": {"NPRO", "ADJF"},
    "num": {"NUMR", "ADJF"},
}

Groups = list[tuple[str, ...]]


def grammemes(pos: str, form_key: str) -> Groups | None:
    """Was das Wörterbuch an einer Form sehen muss; None, wo es nichts zu prüfen gibt."""
    head, _, tail = form_key.partition(".")
    if form_key == "inf":
        return [("INFN",)]
    if head in _TENSE and len(tail) == 3 and tail[0] in _PERSON and tail[1:] in _NUMBER:
        return [(_TENSE[head],), (_PERSON[tail[0]],), (_NUMBER[tail[1:]],)]
    if head == "pst" and tail in _GENDER:
        return [("past",), (_GENDER[tail],)]
    if head == "imp" and tail in _NUMBER:
        return [("impr",), (_NUMBER[tail],)]
    if head in _CASE:
        if not tail:
            return [_CASE[head]]
        # Beim Substantiv heißt `.pl` Mehrzahl, beim Adjektiv steht es in der
        # Reihe der Geschlechter — gemeint ist beide Male plur.
        if pos == "noun" and tail in _NUMBER:
            return [_CASE[head], (_NUMBER[tail],)]
        if tail in _GENDER:
            return [_CASE[head], (_GENDER[tail],)]
    return None


@cache
def _analyzer():
    # Erst hier importiert: wer nur den Kurs ausliefert, braucht das Wörterbuch nicht.
    import pymorphy3

    return pymorphy3.MorphAnalyzer()


def _plain(text: str) -> str:
    return text.replace(STRESS, "").lower().replace("ё", "е")


def _reads_as(parse, groups: Groups) -> bool:
    tags = parse.tag.grammemes
    return all(tags & set(group) for group in groups)


def _same_word(parse, lemma: str) -> bool:
    return lemma in {_plain(entry.word) for entry in parse.lexeme}


def _suggest(morph, lexeme: Lexeme, groups: Groups) -> str | None:
    """Die Form, die das Wörterbuch an dieser Stelle bilden würde — ohne Betonung."""
    wanted = {group[0] for group in groups}
    for parse in morph.parse(_plain(lexeme.lemma)):
        if parse.tag.POS not in _POS_TAGS[lexeme.pos]:
            continue
        inflected = parse.inflect(wanted)
        if inflected is not None:
            return inflected.word
    return None


def _check_form(morph, lexeme: Lexeme, form_key: str, text: str, groups: Groups) -> str | None:
    parses = morph.parse(_plain(text))
    own = [parse for parse in parses if _same_word(parse, _plain(lexeme.lemma))]
    if any(_reads_as(parse, groups) for parse in own):
        return None

    where = f"Lexem {lexeme.id}, Form {form_key}"
    if not any(parse.is_known for parse in parses):
        return (
            f"{where}: {text} steht nicht im Wörterbuch — vertippt? Ist das Wort richtig, "
            'bekommt das Lexem "morph_check": false.'
        )

    wanted_label = with_article_de(form_label_de(form_key))
    actual = [
        key
        for key in sorted(allowed_form_keys(lexeme.pos))
        if (other := grammemes(lexeme.pos, key)) and any(_reads_as(p, other) for p in own)
    ]
    if actual:
        message = (
            f"{where}: {text} ist laut Wörterbuch {with_article_de(form_label_de(actual[0]))}, "
            f"gesucht ist {wanted_label}"
        )
    elif own:
        message = f"{where}: {text} passt laut Wörterbuch nicht zu {wanted_label}"
    else:
        message = f"{where}: {text} ist laut Wörterbuch keine Form von {lexeme.lemma}"

    suggestion = _suggest(morph, lexeme, groups)
    return f"{message} — erwartet wäre {suggestion}." if suggestion else f"{message}."


def check_morphology(course: Course) -> list[str]:
    """Alle Formen, die das Wörterbuch anders bilden würde, als deutsche Meldungen."""
    morph = _analyzer()
    errors: list[str] = []
    for lexeme in course.lexemes.values():
        if lexeme.pos not in CHECKED_POS or not lexeme.morph_check:
            continue
        if " " in lexeme.lemma.strip():
            continue
        for form_key, form in lexeme.forms.items():
            groups = grammemes(lexeme.pos, form_key)
            # Mehrwortformen wie „бу́ду де́лать" kennt das Wörterbuch nicht als Ganzes.
            if groups is None or " " in form.text.strip():
                continue
            error = _check_form(morph, lexeme, form_key, form.text, groups)
            if error:
                errors.append(error)
    return errors
