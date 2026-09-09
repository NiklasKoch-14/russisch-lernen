"""Normalisierung getippter russischer Eingaben.

Diese Datei legt den gesamten Toleranzbereich der Tippaufgabe fest: was hier
verschwindet, darf falsch sein, alles andere zaehlt. Verglichen wird immer
normalisiert gegen normalisiert — nie eine rohe Eingabe gegen eine Kursform.
"""

import re

_NOISE = re.compile(r"[^а-я0-9\s]")
"""Alles ausser Kleinbuchstaben, Ziffern und Leerraum faellt weg.

Damit sind drei Dinge auf einmal erledigt: Satzzeichen, lateinische Buchstaben
(wer die Tastatur nicht umgestellt hat, soll das merken) und das
Betonungszeichen U+0301, das als eigenes Zeichen hinter dem Vokal steht und auf
keiner Tastatur zu finden ist.
"""


def normalize(text: str) -> str:
    # ё liegt ausserhalb von а-я und muesste sonst dem Rauschen zum Opfer
    # fallen. Es wird zu е, weil es im Alltag auch von Russen so getippt wird —
    # der Kurs schreibt es nur, weil es beim Lesen hilft.
    lowered = text.lower().replace("ё", "е")
    return " ".join(_NOISE.sub("", lowered).split())


def words(text: str) -> list[str]:
    return normalize(text).split()
