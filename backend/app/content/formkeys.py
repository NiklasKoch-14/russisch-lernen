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
