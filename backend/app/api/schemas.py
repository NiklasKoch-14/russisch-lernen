from pydantic import BaseModel


class ProfileResponse(BaseModel):
    language: str
    cefr_level: str
    show_transliteration: bool = True
    placement_unit: int | None = None
    audio_autoplay: bool = True


class PracticeTurnRequest(BaseModel):
    message: str


class PracticeTurnResponse(BaseModel):
    reply: str


class PlacementStartResponse(BaseModel):
    session_id: int
    question: str


class PlacementAnswerRequest(BaseModel):
    session_id: int
    answer: str


class PlacementAnswerResponse(BaseModel):
    finished: bool
    question: str | None = None
    level: str | None = None


class LearningPlanResponse(BaseModel):
    topics: list[str]


class VocabCardResponse(BaseModel):
    id: int
    term: str
    translation: str
    example_sentence: str
    due_date: str


class VocabAnswerRequest(BaseModel):
    card_id: int
    answer: str


class VocabAnswerResponse(BaseModel):
    correct: bool


class AnalyzeSessionResponse(BaseModel):
    updated_level: str | None = None
    notable_errors: list[str] = []
    vocab_suggestions: list[dict] = []
    next_topics: list[str] = []


class ProfilePatchRequest(BaseModel):
    show_transliteration: bool | None = None
    placement_unit: int | None = None
    audio_autoplay: bool | None = None


class AnswerRequest(BaseModel):
    exercise_id: str
    submission: dict


class AnswerResponse(BaseModel):
    correct: bool
    solution_text: str
    solution_translit: str
    solution_audio: list[str] = []
    explanation_de: str
    unit_completed: bool
    correct_count: int
    total_count: int


class ScreeningAnswerRequest(BaseModel):
    answers: list[int]


class ReviewAnswerRequest(BaseModel):
    pairs: list[list[int]]


class ReviewExerciseRequest(BaseModel):
    unit_id: int
    exercise_id: str
    submission: dict


class ExplainRequest(BaseModel):
    unit_id: int
    exercise_id: str
    chosen_text: str


class ExplainResponse(BaseModel):
    explanation_de: str
    source: str
