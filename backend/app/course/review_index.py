from dataclasses import dataclass, field

from app.content.models import BuildSentenceExercise, ChooseFormExercise, Course, TokenRef
from app.course.shuffle import shuffled_order

Location = tuple[int, str]
"""(unit_id, exercise_id) — so viel braucht der Client, um die Aufgabe zu benennen."""


@dataclass(frozen=True)
class ReviewIndex:
    """Welche Aufgaben trainieren eine Wortform im Satz?

    Zwei Abbildungen, weil sie unterschiedlich gut treffen: bei `choose_form`
    *ist* die Form die Loesung, bei `build_sentence` kommt sie unter anderen vor.
    """

    exact: dict[TokenRef, list[Location]] = field(default_factory=dict)
    broad: dict[TokenRef, list[Location]] = field(default_factory=dict)

    def pick(self, ref: TokenRef, *, allowed_units: set[int], seed: str) -> Location | None:
        """Eine Aufgabe zu dieser Form — genau vor weit, und nur aus bearbeiteten Einheiten."""
        for table in (self.exact, self.broad):
            candidates = [
                location for location in table.get(ref, []) if location[0] in allowed_units
            ]
            if not candidates:
                continue
            # Los statt „immer die erste": sonst sieht man ewig denselben Satz.
            order = shuffled_order(f"{seed}:{ref[0]}:{ref[1]}", len(candidates))
            return candidates[order[0]]
        return None


def build_index(course: Course) -> ReviewIndex:
    exact: dict[TokenRef, list[Location]] = {}
    broad: dict[TokenRef, list[Location]] = {}
    for unit in course.ordered_units():
        for exercise in unit.exercises:
            where = (unit.id, exercise.id)
            if isinstance(exercise, ChooseFormExercise):
                exact.setdefault(exercise.answer, []).append(where)
            elif isinstance(exercise, BuildSentenceExercise):
                for ref in exercise.solution:
                    broad.setdefault(ref, []).append(where)
    return ReviewIndex(exact=exact, broad=broad)
