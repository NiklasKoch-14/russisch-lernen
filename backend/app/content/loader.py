from pathlib import Path

from app.content.jsonio import ContentError, _read_json, _token, _tokens
from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    Dialog,
    DialogLine,
    DialogReplyExercise,
    DialogSpeaker,
    Exercise,
    Form,
    GrammarFocus,
    Lexeme,
    ListenMeaningExercise,
    MatchPairsExercise,
    Primer,
    ReplyOption,
    ScreeningProbe,
    TokenRef,
    Unit,
)

BLANK = "___"


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
        morph_check = raw.get("morph_check", True)
        if not isinstance(morph_check, bool):
            raise ContentError(
                f"Lexem {raw['id']!r}: morph_check muss true oder false sein, nicht {morph_check!r}"
            )
        return Lexeme(
            id=raw["id"],
            lemma=raw["lemma"],
            pos=raw["pos"],
            gloss_de=raw["gloss_de"],
            forms=forms,
            aspect=raw.get("aspect"),
            aspect_pair=raw.get("aspect_pair"),
            morph_check=morph_check,
        )
    except (KeyError, TypeError) as exc:
        raise ContentError(f"Lexem unvollständig: {raw.get('id', raw)!r} ({exc})") from exc


def _exercise(raw: dict, unit_id: int) -> Exercise:
    kind = raw.get("type")
    where = f"Einheit {unit_id}, Aufgabe {raw.get('id')}"
    if "audio_prompt" in raw and kind not in ("build_sentence", "choose_form"):
        raise ContentError(
            f"{where}: audio_prompt gibt es nur bei build_sentence und choose_form,"
            f" nicht bei {kind!r}"
        )
    try:
        if kind == "build_sentence":
            return BuildSentenceExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                solution=_tokens(raw["solution"], where),
                distractors=_tokens(raw.get("distractors", []), where),
                audio_prompt=bool(raw.get("audio_prompt", False)),
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
                audio_prompt=bool(raw.get("audio_prompt", False)),
            )
        if kind == "match_pairs":
            return MatchPairsExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                pairs=_tokens(raw["pairs"], where),
            )
        if kind == "listen_meaning":
            return ListenMeaningExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                sentence=_tokens(raw["sentence"], where),
                options_de=[str(option) for option in raw["options_de"]],
                correct_index=int(raw["correct_index"]),
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
                primer=focus.get("primer"),
            ),
            new_lexemes=list(raw["new_lexemes"]),
            exercises=[_exercise(item, int(raw["id"])) for item in raw["exercises"]],
        )
    except KeyError as exc:
        raise ContentError(f"{source.name}: Feld fehlt {exc}") from exc


def _dialog(raw: dict, source: Path) -> Dialog:
    try:
        return Dialog(
            id=int(raw["id"]),
            min_unit=int(raw["min_unit"]),
            title_de=raw["title_de"],
            speakers=[
                DialogSpeaker(
                    name_ru=item["name_ru"], name_de=item["name_de"], voice=item["voice"]
                )
                for item in raw["speakers"]
            ],
            lines=[
                DialogLine(
                    speaker=int(item["speaker"]),
                    tokens=_tokens(item["tokens"], f"{source.name}, Zeile {index}"),
                    translation_de=item["translation_de"],
                )
                for index, item in enumerate(raw["lines"], start=1)
            ],
            question_de=raw["question_de"],
            options_de=list(raw["options_de"]),
            correct_index=int(raw["correct_index"]),
        )
    except (KeyError, TypeError) as exc:
        raise ContentError(f"{source.name}: Gespräch unvollständig ({exc})") from exc


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

    raw_primers = _read_json(root / "primers.json")
    primers = {
        item["id"]: Primer(
            id=item["id"], title_de=item["title_de"], text_de=item["text_de"]
        )
        for item in raw_primers["primers"]
    }

    # Ohne Verzeichnis bleibt es leer: Gespräche sind eine Zugabe, kein Kurs.
    dialogs: dict[int, Dialog] = {}
    for path in sorted((root / "dialogs").glob("*.json")):
        dialog = _dialog(_read_json(path), path)
        if dialog.id in dialogs:
            raise ContentError(f"Gespräch-ID {dialog.id} kommt doppelt vor ({path.name})")
        dialogs[dialog.id] = dialog

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

    return Course(
        language=language,
        lexemes=lexemes,
        units=units,
        screening=screening,
        primers=primers,
        dialogs=dialogs,
    )
