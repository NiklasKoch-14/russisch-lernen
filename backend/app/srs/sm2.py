from dataclasses import dataclass

MAX_INTERVAL_DAYS = 365.0
"""Obergrenze für den Abstand zweier Wiederholungen.

Ohne sie wächst das Intervall bei jeder richtigen Antwort um den Ease-Faktor:
nach rund 17 Treffern liegt der nächste Termin jenseits des Jahres 9999, und
`date + timedelta` bricht mit OverflowError ab — die Antwort scheitert dann mit
500, obwohl sie richtig war. Ein Jahr ist auch fachlich genug: was man ein Jahr
lang nicht vergisst, braucht diese Planung nicht mehr.
"""


@dataclass
class SM2Result:
    repetitions: int
    ease_factor: float
    interval_days: float


def sm2_update(*, correct: bool, repetitions: int, ease_factor: float, interval_days: float) -> SM2Result:
    quality = 4 if correct else 2

    if quality >= 3:
        if repetitions == 0:
            new_interval = 1.0
        elif repetitions == 1:
            new_interval = 6.0
        else:
            new_interval = min(round(interval_days * ease_factor, 2), MAX_INTERVAL_DAYS)
        new_repetitions = repetitions + 1
    else:
        new_repetitions = 0
        new_interval = 1.0

    new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease_factor = max(1.3, round(new_ease_factor, 3))

    return SM2Result(repetitions=new_repetitions, ease_factor=new_ease_factor, interval_days=new_interval)
