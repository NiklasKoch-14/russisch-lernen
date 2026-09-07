import json
from pathlib import Path

MINIMAL_LEXICON = {
    "version": 1,
    "lexemes": [
        {
            "id": "ja",
            "lemma": "я",
            "pos": "pron",
            "gloss_de": "ich",
            "forms": {"nom": {"text": "я", "translit": "ja"}},
        },
        {
            "id": "delat",
            "lemma": "де́лать",
            "pos": "verb",
            "gloss_de": "machen, tun",
            "aspect": "impf",
            "forms": {
                "inf": {"text": "де́лать", "translit": "délat'"},
                "prs.1sg": {"text": "де́лаю", "translit": "délaju"},
                "prs.2sg": {"text": "де́лаешь", "translit": "délaješ'"},
                "prs.3sg": {"text": "де́лает", "translit": "délajet"},
            },
        },
    ],
}

MINIMAL_UNIT = {
    "id": 1,
    "stage": 0,
    "title_de": "Was machst du?",
    "scenario_de": "Du fragst jemanden nach seiner Tätigkeit.",
    "grammar_focus": {
        "id": "prs-conj",
        "title_de": "Verbendungen im Präsens",
        "explanation_de": "Die Endung zeigt, wer handelt.",
    },
    "new_lexemes": ["ja", "delat"],
    "exercises": [
        {
            "id": "1-1",
            "type": "build_sentence",
            "prompt_de": "Ich mache das.",
            "solution": [["ja", "nom"], ["delat", "prs.1sg"]],
            "distractors": [["delat", "prs.3sg"]],
        },
        {
            "id": "1-2",
            "type": "choose_form",
            "prompt_de": "Was macht er?",
            "sentence": [["ja", "nom"], "___"],
            "answer": ["delat", "prs.1sg"],
            "distractor_forms": ["prs.2sg", "prs.3sg"],
        },
        {
            "id": "1-3",
            "type": "match_pairs",
            "prompt_de": "Ordne zu.",
            "pairs": [["ja", "nom"], ["delat", "prs.1sg"]],
        },
        {
            "id": "1-4",
            "type": "dialog_reply",
            "prompt_de": "Wie antwortest du?",
            "tutor_line": [["delat", "prs.2sg"]],
            "correct_index": 0,
            "options": [
                {"tokens": [["ja", "nom"], ["delat", "prs.1sg"]], "why_de": ""},
                {"tokens": [["delat", "prs.3sg"]], "why_de": "Das ist die Form für er/sie."},
            ],
        },
    ],
}

MINIMAL_SCREENING = [
    {
        "id": "s1",
        "prompt_de": "Welcher Buchstabe klingt wie ein r?",
        "options": ["Р", "П", "Н"],
        "correct_index": 0,
        "maps_to_unit": 1,
    }
]


def write_course(root, *, lexicon=None, units=None, screening=None) -> Path:
    """Write a course tree under root and return the content directory."""
    content = Path(root) / "ru"
    (content / "units").mkdir(parents=True, exist_ok=True)
    (content / "lexicon.json").write_text(
        json.dumps(lexicon if lexicon is not None else MINIMAL_LEXICON), encoding="utf-8"
    )
    (content / "screening.json").write_text(
        json.dumps({"probes": screening if screening is not None else MINIMAL_SCREENING}),
        encoding="utf-8",
    )
    for unit in units if units is not None else [MINIMAL_UNIT]:
        (content / "units" / f"{unit['id']:03d}.json").write_text(
            json.dumps(unit), encoding="utf-8"
        )
    return content
