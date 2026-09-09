from dataclasses import dataclass, field

TokenRef = tuple[str, str]
"""A (lexeme_id, form_key) pair — how every sentence token is written in content."""


@dataclass(frozen=True)
class Form:
    text: str
    translit: str
    speak_as: str | None = None
    """Was statt `text` vorgelesen wird — Buchstaben nennen sonst ihren Namen, nicht ihren Laut."""


@dataclass(frozen=True)
class Lexeme:
    id: str
    lemma: str
    pos: str
    gloss_de: str
    forms: dict[str, Form]
    aspect: str | None = None
    aspect_pair: str | None = None


@dataclass(frozen=True)
class Primer:
    """Ein deutscher Grundbegriff — was ein Fall oder eine Form überhaupt ist."""

    id: str
    title_de: str
    text_de: str


@dataclass(frozen=True)
class GrammarFocus:
    id: str
    title_de: str
    explanation_de: str
    primer: str | None = None
    """Id des Primers, der vor der Regel steht — None, wenn die Einheit keinen braucht."""


@dataclass(frozen=True)
class BuildSentenceExercise:
    id: str
    prompt_de: str
    solution: list[TokenRef]
    distractors: list[TokenRef]
    audio_prompt: bool = False
    type: str = "build_sentence"


@dataclass(frozen=True)
class ChooseFormExercise:
    id: str
    prompt_de: str
    sentence: list[TokenRef | None]
    answer: TokenRef
    distractor_forms: list[str]
    audio_prompt: bool = False
    type: str = "choose_form"


@dataclass(frozen=True)
class MatchPairsExercise:
    id: str
    prompt_de: str
    pairs: list[TokenRef]
    type: str = "match_pairs"


@dataclass(frozen=True)
class ReplyOption:
    tokens: list[TokenRef]
    why_de: str


@dataclass(frozen=True)
class DialogReplyExercise:
    id: str
    prompt_de: str
    tutor_line: list[TokenRef]
    options: list[ReplyOption]
    correct_index: int
    type: str = "dialog_reply"


@dataclass(frozen=True)
class ListenMeaningExercise:
    """Hear a sentence, pick its German meaning from near-miss options."""

    id: str
    prompt_de: str
    sentence: list[TokenRef]
    options_de: list[str]
    correct_index: int
    type: str = "listen_meaning"


@dataclass(frozen=True)
class TypeSentenceExercise:
    """Der Satz wird getippt — keine Kacheln, keine Ablenker.

    Kommt nicht aus `units/NNN.json`, sondern entsteht zur Laufzeit aus einem
    Zug im Dorf. Der Lader kennt den Typ deshalb nicht; er steht hier, damit
    Presenter und Checker ihn typsicher behandeln.
    """

    id: str
    prompt_de: str
    solution: list[TokenRef]
    type: str = "type_sentence"


Exercise = (
    BuildSentenceExercise
    | ChooseFormExercise
    | MatchPairsExercise
    | DialogReplyExercise
    | ListenMeaningExercise
    | TypeSentenceExercise
)


@dataclass(frozen=True)
class Unit:
    id: int
    stage: int
    title_de: str
    scenario_de: str
    grammar_focus: GrammarFocus
    new_lexemes: list[str]
    exercises: list[Exercise]


@dataclass(frozen=True)
class ScreeningProbe:
    id: str
    prompt_de: str
    options: list[str]
    correct_index: int
    maps_to_unit: int


@dataclass(frozen=True)
class Course:
    language: str
    lexemes: dict[str, Lexeme]
    units: dict[int, Unit]
    screening: list[ScreeningProbe] = field(default_factory=list)
    primers: dict[str, Primer] = field(default_factory=dict)

    def form(self, ref: TokenRef) -> Form:
        """Resolve a token reference to its concrete word form."""
        lexeme_id, form_key = ref
        lexeme = self.lexemes[lexeme_id]
        return lexeme.forms[form_key]

    def gloss(self, ref: TokenRef) -> str:
        return self.lexemes[ref[0]].gloss_de

    def ordered_units(self) -> list[Unit]:
        return [self.units[key] for key in sorted(self.units)]
