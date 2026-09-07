import json
from pathlib import Path

from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    DialogReplyExercise,
    Exercise,
    Form,
    GrammarFocus,
    Lexeme,
    MatchPairsExercise,
    ReplyOption,
    ScreeningProbe,
    TokenRef,
    Unit,
)

BLANK = "___"


class ContentError(Exception):
    """Raised when the content package cannot be read or is structurally invalid."""


def _read_json(path: Path) -> dict | list:
    if not path.exists():
        raise ContentError(f"Datei fehlt: {path.name} ({path})")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"Ungültiges JSON in {path.name}: {exc}") from exc


def _token(raw: object, where: str) -> TokenRef:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ContentError(f"Token in {where} muss [lexeme_id, form_key] sein, war: {raw!r}")
    return (str(raw[0]), str(raw[1]))


def _tokens(raw: object, where: str) -> list[TokenRef]:
    if not isinstance(raw, list):
        raise ContentError(f"Tokenliste in {where} muss eine Liste sein, war: {raw!r}")
    return [_token(item, where) for item in raw]


def _lexeme(raw: dict) -> Lexeme:
    try:
        forms = {
            key: Form(
                text=value["text"],
                translit=value["translit"],
                speak_as=value.get("speak_as"),
            )
            for key, value in raw["forms"].items()
        }
        return Lexeme(
            id=raw["id"],
            lemma=raw["lemma"],
            pos=raw["pos"],
            gloss_de=raw["gloss_de"],
            forms=forms,
            aspect=raw.get("aspect"),
            aspect_pair=raw.get("aspect_pair"),
        )
    except (KeyError, TypeError) as exc:
        raise ContentError(f"Lexem unvollständig: {raw.get('id', raw)!r} ({exc})") from exc


def _exercise(raw: dict, unit_id: int) -> Exercise:
    kind = raw.get("type")
    where = f"Einheit {unit_id}, Aufgabe {raw.get('id')}"
    try:
        if kind == "build_sentence":
            return BuildSentenceExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                solution=_tokens(raw["solution"], where),
                distractors=_tokens(raw.get("distractors", []), where),
            )
        if kind == "choose_form":
            sentence: list[TokenRef | None] = [
                None if item == BLANK else _token(item, where) for item in raw["sentence"]
            ]
            return ChooseFormExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                sentence=sentence,
                answer=_token(raw["answer"], where),
                distractor_forms=list(raw["distractor_forms"]),
            )
        if kind == "match_pairs":
            return MatchPairsExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                pairs=_tokens(raw["pairs"], where),
            )
        if kind == "dialog_reply":
            options = [
                ReplyOption(tokens=_tokens(option["tokens"], where), why_de=option.get("why_de", ""))
                for option in raw["options"]
            ]
            return DialogReplyExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                tutor_line=_tokens(raw["tutor_line"], where),
                options=options,
                correct_index=int(raw["correct_index"]),
            )
    except KeyError as exc:
        raise ContentError(f"{where}: Feld fehlt {exc}") from exc
    raise ContentError(f"{where}: unbekannter Aufgabentyp {kind!r}")


def _unit(raw: dict, source: Path) -> Unit:
    try:
        focus = raw["grammar_focus"]
        return Unit(
            id=int(raw["id"]),
            stage=int(raw["stage"]),
            title_de=raw["title_de"],
            scenario_de=raw["scenario_de"],
            grammar_focus=GrammarFocus(
                id=focus["id"],
                title_de=focus["title_de"],
                explanation_de=focus["explanation_de"],
            ),
            new_lexemes=list(raw["new_lexemes"]),
            exercises=[_exercise(item, int(raw["id"])) for item in raw["exercises"]],
        )
    except KeyError as exc:
        raise ContentError(f"{source.name}: Feld fehlt {exc}") from exc


def load_course(content_dir: str | Path, language: str = "russian") -> Course:
    """Load the whole content package from disk into an immutable Course."""
    root = Path(content_dir)
    raw_lexicon = _read_json(root / "lexicon.json")
    lexemes = {item["id"]: _lexeme(item) for item in raw_lexicon["lexemes"]}

    units: dict[int, Unit] = {}
    for path in sorted((root / "units").glob("*.json")):
        unit = _unit(_read_json(path), path)
        if unit.id in units:
            raise ContentError(f"Einheiten-ID {unit.id} kommt doppelt vor ({path.name})")
        units[unit.id] = unit

    raw_screening = _read_json(root / "screening.json")
    screening = [
        ScreeningProbe(
            id=probe["id"],
            prompt_de=probe["prompt_de"],
            options=list(probe["options"]),
            correct_index=int(probe["correct_index"]),
            maps_to_unit=int(probe["maps_to_unit"]),
        )
        for probe in raw_screening["probes"]
    ]

    return Course(language=language, lexemes=lexemes, units=units, screening=screening)
