from app.repositories.session_repo import ConversationTurn

TUTOR_PERSONA = (
    "You are a friendly, encouraging personal language tutor. You always respond "
    "only in {language}, adapting your vocabulary and grammar complexity to a "
    "{cefr_level} (CEFR) learner. When the learner makes a mistake, gently correct "
    "it within your reply and keep the conversation going. Keep replies short "
    "(2-4 sentences)."
)

PLAN_FOCUS_ADDENDUM = "Try to steer the conversation towards this topic/scenario: {topic}."


def tutor_system_prompt(*, language: str, cefr_level: str, plan_topic: str | None) -> str:
    prompt = TUTOR_PERSONA.format(language=language, cefr_level=cefr_level)
    if plan_topic:
        prompt += " " + PLAN_FOCUS_ADDENDUM.format(topic=plan_topic)
    return prompt


PLACEMENT_PERSONA = (
    "You are a language placement examiner for {language}. Ask the learner one "
    "question at a time, starting easy and increasing difficulty based on their "
    "answers, to estimate their CEFR level (A1-C2). Ask a maximum of 5 questions "
    "total. After the final question, once you have enough information, respond "
    'ONLY with a JSON object: {{"level": "A1"}} (use the estimated level, no '
    "other text). Otherwise, just ask the next question in {language}."
)


def placement_system_prompt(*, language: str) -> str:
    return PLACEMENT_PERSONA.format(language=language)


def build_chat_messages(
    *, system_prompt: str, history: list[ConversationTurn], user_message: str
) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": turn.role, "content": turn.content} for turn in history)
    messages.append({"role": "user", "content": user_message})
    return messages


ANALYSIS_PERSONA = (
    "You are analyzing a {language} learner's practice conversation transcript "
    "below to update their profile. The learner's current level is {cefr_level}. "
    'Respond ONLY with a JSON object with these keys: '
    '"updated_level" (CEFR level string or null if unchanged), '
    '"notable_errors" (array of short strings), '
    '"vocab_suggestions" (array of objects with "term", "translation", '
    '"example_sentence"), "next_topics" (array of short topic strings).\n\n'
    "Transcript:\n{transcript}"
)


def analysis_prompt(*, language: str, cefr_level: str, transcript: str) -> str:
    return ANALYSIS_PERSONA.format(language=language, cefr_level=cefr_level, transcript=transcript)


LEARNING_PLAN_PERSONA = (
    "Create a short {language} learning plan for a {cefr_level} learner. "
    "Consider these recent notes: {notes}. Respond ONLY with a JSON object with "
    'key "topics": an array of 3-5 short dialog topic/scenario strings suited '
    "to their level."
)


def learning_plan_prompt(*, language: str, cefr_level: str, notes: str) -> str:
    return LEARNING_PLAN_PERSONA.format(language=language, cefr_level=cefr_level, notes=notes)
