CASES = ("nom", "gen", "dat", "acc", "ins", "prp")
NUMBERS = ("sg", "pl")
GENDERS = ("m", "f", "n", "pl")
PERSONS = ("1sg", "2sg", "3sg", "1pl", "2pl", "3pl")

_VERB = frozenset(
    ["inf"]
    + [f"prs.{p}" for p in PERSONS]
    + [f"fut.{p}" for p in PERSONS]
    + [f"pst.{g}" for g in ("m", "f", "n", "pl")]
    + ["imp.sg", "imp.pl"]
)
_NOUN = frozenset(f"{c}.{n}" for c in CASES for n in NUMBERS)
_ADJ = frozenset(f"{c}.{g}" for c in CASES for g in GENDERS)
_CASE_ONLY = frozenset(CASES)
_BASE = frozenset({"base"})

FORM_KEYS: dict[str, frozenset[str]] = {
    "verb": _VERB,
    "noun": _NOUN,
    "adj": _ADJ,
    "pron": _CASE_ONLY,
    # Zahlwoerter: die niedrigen richten sich nach dem Geschlecht (оди́н/одна́, два/две),
    # die hoeheren nicht — deshalb sind beide Schluesselformen erlaubt.
    "num": _CASE_ONLY | _ADJ,
    "adv": _BASE,
    "prep": _BASE,
    "part": _BASE,
    "conj": _BASE,
    "interj": _BASE,
    "letter": _BASE,
}

POS_VALUES = frozenset(FORM_KEYS)


def allowed_form_keys(pos: str) -> frozenset[str]:
    """Return the form keys a lexeme of this part of speech may declare."""
    return FORM_KEYS[pos]


_CASE_DE = {
    "nom": "Nominativ",
    "gen": "Genitiv",
    "dat": "Dativ",
    "acc": "Akkusativ",
    "ins": "Instrumental",
    "prp": "Präpositiv",
}
_NUMBER_DE = {"sg": "Einzahl", "pl": "Mehrzahl"}
_GENDER_DE = {"m": "männlich", "f": "weiblich", "n": "sächlich", "pl": "Mehrzahl"}
_PERSON_DE = {
    "1sg": "ich",
    "2sg": "du",
    "3sg": "er/sie",
    "1pl": "wir",
    "2pl": "ihr",
    "3pl": "sie",
}


def form_label_de(form_key: str) -> str:
    """Die Form auf Deutsch benennen, so wie der Kurs selbst spricht.

    Faelle heissen bei ihrem Namen — `primers.json` fuehrt sie ohnehin ein.
    Verbformen dagegen umgangssprachlich („die du-Form"), weil „2. Person
    Singular" niemandem hilft, der Grammatik nie in der Schule hatte.

    Ein unbekannter Schluessel gibt sich selbst zurueck: eine Fehlermeldung
    darf nie daran scheitern, dass sie den Fehler benennen will.
    """
    if form_key in ("base", "inf"):
        return "Grundform"

    head, _, tail = form_key.partition(".")
    if head in _CASE_DE:
        suffix = _NUMBER_DE.get(tail) or _GENDER_DE.get(tail) or ""
        return f"{_CASE_DE[head]} {suffix}".strip()
    if head == "prs" and tail in _PERSON_DE:
        return f"{_PERSON_DE[tail]}-Form"
    if head == "fut" and tail in _PERSON_DE:
        return f"{_PERSON_DE[tail]}-Form Zukunft"
    if head == "pst" and tail in _GENDER_DE:
        return f"Vergangenheit {_GENDER_DE[tail]}"
    if head == "imp" and tail in _NUMBER_DE:
        return f"Befehlsform {_NUMBER_DE[tail]}"
    return form_key


def contrast_labels_de(typed_key: str, wanted_key: str) -> tuple[str, str]:
    """Zwei Formbezeichnungen, um das Gemeinsame gekuerzt.

    „Nominativ Einzahl gegen Präpositiv Einzahl" nennt die Einzahl zweimal,
    obwohl sie nicht der Fehler ist. Uebrig bleibt, was die beiden Formen
    wirklich trennt — es sei denn, dann bliebe nichts uebrig.
    """
    typed = form_label_de(typed_key).split()
    wanted = form_label_de(wanted_key).split()
    if len(typed) == len(wanted):
        kept = [(a, b) for a, b in zip(typed, wanted) if a != b]
        if kept:
            return (
                " ".join(part for part, _ in kept),
                " ".join(part for _, part in kept),
            )
    return " ".join(typed), " ".join(wanted)
