"""Prompt builders for technical interview question generation."""

from __future__ import annotations

from typing import Any

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


def build_candidate_profile_summary(candidate_data: dict[str, str]) -> str:
    """Build a short candidate profile summary for prompt context."""
    summary_lines = [
        f"Full Name: {candidate_data.get('full_name', '')}",
        f"Email: {candidate_data.get('email', '')}",
        f"Phone: {candidate_data.get('phone', '')}",
        f"Experience: {candidate_data.get('experience', '')}",
        f"Desired Role: {candidate_data.get('desired_role', '')}",
        f"Current Location: {candidate_data.get('current_location', '')}",
    ]
    return "\n".join(summary_lines)


def normalize_conversation_history(
    conversation_history: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """Keep only valid chat-completion message entries from the conversation history."""
    if not conversation_history:
        return []

    normalized_messages: list[dict[str, str]] = []
    for message in conversation_history:
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()
        if role in {"system", "user", "assistant"} and content:
            normalized_messages.append({"role": role, "content": content})

    return normalized_messages


def build_technical_question_messages(
    technologies: list[str],
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    candidate_data: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Build the LM Studio prompt payload for technical question generation."""
    technology_list = ", ".join(technologies)
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": TECHNICAL_QUESTION_SYSTEM_PROMPT,
        }
    ]
    messages.extend(normalize_conversation_history(conversation_history))
    messages.append(
        {
            "role": "user",
            "content": (
                "Use the full conversation history above as context for the candidate.\n"
                f"Candidate Profile:\n{build_candidate_profile_summary(candidate_data or {})}\n\n"
                f"Candidate Tech Stack: {technology_list}\n"
                "Generate 3 intermediate-level interview questions for each technology.\n"
                "Rules:\n"
                "- Questions must be practical.\n"
                "- Avoid repeated questions.\n"
                "- Keep questions concise.\n"
                "Return JSON only in this format:\n"
                f"{TECHNICAL_QUESTION_RESPONSE_EXAMPLE}"
            ),
        }
    )
    return messages
