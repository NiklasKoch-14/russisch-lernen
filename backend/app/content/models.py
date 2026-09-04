from dataclasses import dataclass, field

TokenRef = tuple[str, str]
"""A (lexeme_id, form_key) pair — how every sentence token is written in content."""


@dataclass(frozen=True)
class Form:
    text: str
    translit: str


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
class GrammarFocus:
    id: str
    title_de: str
    explanation_de: str


@dataclass(frozen=True)
class BuildSentenceExercise:
    id: str
    prompt_de: str
    solution: list[TokenRef]
    distractors: list[TokenRef]
    type: str = "build_sentence"


@dataclass(frozen=True)
class ChooseFormExercise:
    id: str
    prompt_de: str
    sentence: list[TokenRef | None]
    answer: TokenRef
    distractor_forms: list[str]
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


Exercise = (
    BuildSentenceExercise | ChooseFormExercise | MatchPairsExercise | DialogReplyExercise
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

    def form(self, ref: TokenRef) -> Form:
        """Resolve a token reference to its concrete word form."""
        lexeme_id, form_key = ref
        lexeme = self.lexemes[lexeme_id]
        return lexeme.forms[form_key]

    def gloss(self, ref: TokenRef) -> str:
        return self.lexemes[ref[0]].gloss_de

    def ordered_units(self) -> list[Unit]:
        return [self.units[key] for key in sorted(self.units)]
