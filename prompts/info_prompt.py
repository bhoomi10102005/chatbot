"""Prompt helpers for one-question-at-a-time candidate information collection."""

from __future__ import annotations

DEFAULT_INPUT_PLACEHOLDER = "Share your response here"
COMPLETED_INPUT_PLACEHOLDER = "Conversation complete. Reset to start again."

WELCOME_MESSAGE = (
    "Welcome to TalentScout. I will guide you through a short screening conversation "
    "and collect one detail at a time. To get started, please share your full name."
)

STAGE_INPUT_PLACEHOLDERS = {
    "greeting": "Enter your full name",
    "collect_email": "Enter your email address",
    "collect_phone": "Enter your phone number",
    "collect_experience": "Enter your years of experience",
    "collect_desired_role": "Enter your desired role",
    "collect_current_location": "Enter your current location",
    "collect_tech_stack": (
        "Example: Languages: Python, JavaScript; Frameworks: Flask; "
        "Databases: PostgreSQL; Tools/Platforms: Docker"
    ),
    "completed": COMPLETED_INPUT_PLACEHOLDER,
}

STAGE_PROMPTS = {
    "collect_email": "Could you please share your email address?",
    "collect_phone": "Great. What is the best phone number to reach you?",
    "collect_experience": "How many years of professional experience do you have?",
    "collect_desired_role": "Which role are you currently targeting or applying for?",
    "collect_current_location": "What is your current location?",
    "collect_tech_stack": (
        "Please share your tech stack, including programming languages, frameworks, "
        "databases, and tools or platforms. You can use a format like: "
        "Languages: Python, JavaScript; Frameworks: Flask; Databases: PostgreSQL; "
        "Tools/Platforms: Docker."
    ),
}


def get_welcome_message() -> str:
    """Return the opening prompt for the candidate conversation."""
    return WELCOME_MESSAGE


def get_chat_input_placeholder(stage: str) -> str:
    """Return a stage-aware chat input placeholder."""
    return STAGE_INPUT_PLACEHOLDERS.get(stage, DEFAULT_INPUT_PLACEHOLDER)


def get_next_stage_prompt(stage: str) -> str:
    """Return the next single question for the given collection stage."""
    return STAGE_PROMPTS[stage]


def get_first_name_acknowledgement(first_name: str) -> str:
    """Return a short acknowledgement before asking the next single question."""
    return f"Nice to meet you, {first_name}."
