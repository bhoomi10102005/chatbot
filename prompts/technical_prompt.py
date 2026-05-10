"""Prompt builders for technical interview question generation."""

from __future__ import annotations

TECHNICAL_QUESTION_SYSTEM_PROMPT = """
You are a technical interviewer preparing screening questions for a hiring process.

Rules:
- Generate exactly 3 interview questions for each technology provided.
- Keep every question concise, practical, and intermediate-level.
- Avoid duplicate or overly similar questions.
- Focus on technical understanding, real-world usage, and problem solving.
- Return valid JSON only.
- Each top-level key must match a technology name from the provided list.
- Each value must be an array of exactly 3 question strings.
""".strip()

TECHNICAL_QUESTION_RESPONSE_EXAMPLE = (
    '{"Python": ["Question 1?", "Question 2?", "Question 3?"]}'
)


def build_technical_question_messages(technologies: list[str]) -> list[dict[str, str]]:
    """Build the LM Studio prompt payload for technical question generation."""
    technology_list = ", ".join(technologies)
    return [
        {
            "role": "system",
            "content": TECHNICAL_QUESTION_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"Candidate Tech Stack: {technology_list}\n"
                "Generate 3 intermediate-level interview questions for each technology.\n"
                "Rules:\n"
                "- Questions must be practical.\n"
                "- Avoid repeated questions.\n"
                "- Keep questions concise.\n"
                "Return JSON only in this format:\n"
                f"{TECHNICAL_QUESTION_RESPONSE_EXAMPLE}"
            ),
        },
    ]
