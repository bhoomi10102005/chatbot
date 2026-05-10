"""Streamlit interface for the TalentScout hiring assistant."""

from __future__ import annotations

import json
import re

import streamlit as st

from prompts.system_prompt import EXIT_RESPONSE, FALLBACK_RESPONSE
from services.candidate_service import CandidateService
from services.llm_service import LLMService

APP_TITLE = "TalentScout Hiring Assistant"
APP_SUBTITLE = "AI-powered candidate screening and technical evaluation"
INITIAL_CONVERSATION_STAGE = "greeting"
EMAIL_COLLECTION_STAGE = "collect_email"
PHONE_COLLECTION_STAGE = "collect_phone"
EXPERIENCE_COLLECTION_STAGE = "collect_experience"
ROLE_COLLECTION_STAGE = "collect_desired_role"
LOCATION_COLLECTION_STAGE = "collect_current_location"
TECH_STACK_COLLECTION_STAGE = "collect_tech_stack"
COMPLETED_CONVERSATION_STAGE = "completed"
CANDIDATE_FIELDS = (
    "full_name",
    "email",
    "phone",
    "experience",
    "desired_role",
    "current_location",
)
TECH_STACK_FIELDS = (
    "programming_languages",
    "frameworks",
    "databases",
    "tools_platforms",
)
EXIT_KEYWORDS = ("exit", "quit", "bye", "thanks", "thank you")
STAGE_LABELS = {
    INITIAL_CONVERSATION_STAGE: "Greeting",
    EMAIL_COLLECTION_STAGE: "Collect Email",
    PHONE_COLLECTION_STAGE: "Collect Phone",
    EXPERIENCE_COLLECTION_STAGE: "Collect Experience",
    ROLE_COLLECTION_STAGE: "Collect Desired Role",
    LOCATION_COLLECTION_STAGE: "Collect Current Location",
    TECH_STACK_COLLECTION_STAGE: "Collect Tech Stack",
    COMPLETED_CONVERSATION_STAGE: "Completed",
}
FIELD_BY_STAGE = {
    INITIAL_CONVERSATION_STAGE: "full_name",
    EMAIL_COLLECTION_STAGE: "email",
    PHONE_COLLECTION_STAGE: "phone",
    EXPERIENCE_COLLECTION_STAGE: "experience",
    ROLE_COLLECTION_STAGE: "desired_role",
    LOCATION_COLLECTION_STAGE: "current_location",
}
NEXT_STAGE_BY_STAGE = {
    INITIAL_CONVERSATION_STAGE: EMAIL_COLLECTION_STAGE,
    EMAIL_COLLECTION_STAGE: PHONE_COLLECTION_STAGE,
    PHONE_COLLECTION_STAGE: EXPERIENCE_COLLECTION_STAGE,
    EXPERIENCE_COLLECTION_STAGE: ROLE_COLLECTION_STAGE,
    ROLE_COLLECTION_STAGE: LOCATION_COLLECTION_STAGE,
    LOCATION_COLLECTION_STAGE: TECH_STACK_COLLECTION_STAGE,
}
CATEGORY_ALIASES = {
    "programming_languages": ("programming languages", "programming language", "languages", "language"),
    "frameworks": ("frameworks", "framework"),
    "databases": ("databases", "database", "db", "dbs"),
    "tools_platforms": ("tools/platforms", "tools", "platforms", "tool", "platform"),
}
WELCOME_MESSAGE = (
    "Welcome to TalentScout. I will guide you through a short screening conversation "
    "and collect one detail at a time. To get started, please share your full name."
)


def create_initial_messages() -> list[dict[str, str]]:
    """Create the initial visible chat history."""
    return [{"role": "assistant", "content": WELCOME_MESSAGE}]


def create_initial_candidate_data() -> dict[str, str]:
    """Create the initial candidate data store."""
    return {field: "" for field in CANDIDATE_FIELDS}


def create_initial_tech_stack() -> dict[str, list[str]]:
    """Create the initial tech stack store."""
    return {field: [] for field in TECH_STACK_FIELDS}


def create_initial_session_values() -> dict[str, object]:
    """Create the initial session state used by the app."""
    return {
        "messages": create_initial_messages(),
        "candidate_data": create_initial_candidate_data(),
        "conversation_stage": INITIAL_CONVERSATION_STAGE,
        "tech_stack": create_initial_tech_stack(),
        "generated_questions": {},
    }


def initialize_session_state() -> None:
    """Initialize Streamlit state used by the chat interface."""
    for key, value in create_initial_session_values().items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_conversation() -> None:
    """Reset the tracked conversation state back to its defaults."""
    for key, value in create_initial_session_values().items():
        st.session_state[key] = value


def normalize_user_text(text: str) -> str:
    """Normalize user-provided text for consistent state handling."""
    return re.sub(r"\s+", " ", text).strip()


def is_exit_intent(text: str) -> bool:
    """Return True when the user is trying to end the conversation."""
    normalized = normalize_user_text(text).lower()
    return normalized in EXIT_KEYWORDS


def get_stage_label(stage: str) -> str:
    """Return a human-friendly label for the current conversation stage."""
    return STAGE_LABELS.get(stage, stage.replace("_", " ").title())


def get_collected_candidate_fields_count() -> int:
    """Return how many candidate fields currently have values."""
    return sum(1 for value in st.session_state.candidate_data.values() if value)


def get_flat_technologies(tech_stack: dict[str, list[str]]) -> list[str]:
    """Flatten the structured tech stack into a de-duplicated list."""
    seen: set[str] = set()
    flattened: list[str] = []

    for values in tech_stack.values():
        for value in values:
            normalized = value.strip()
            key = normalized.lower()
            if normalized and key not in seen:
                seen.add(key)
                flattened.append(normalized)

    return flattened


def split_tech_items(raw_values: str) -> list[str]:
    """Split comma-separated or slash-separated technology input into clean items."""
    return [item.strip() for item in re.split(r"[,/\n|]+", raw_values) if item.strip()]


def match_tech_stack_category(label: str) -> str | None:
    """Match a free-form category label to a supported tech stack category."""
    normalized = normalize_user_text(label).lower()
    for category, aliases in CATEGORY_ALIASES.items():
        if normalized in aliases:
            return category
    return None


def parse_tech_stack_input(user_input: str) -> dict[str, list[str]]:
    """Parse the user's tech stack into the structured session-state format."""
    parsed = create_initial_tech_stack()
    sections = [section.strip() for section in re.split(r"[;\n]+", user_input) if section.strip()]
    found_labeled_section = False

    for section in sections:
        if ":" not in section:
            continue

        label, values = section.split(":", 1)
        category = match_tech_stack_category(label)
        if category is None:
            continue

        parsed[category].extend(split_tech_items(values))
        found_labeled_section = True

    if not found_labeled_section:
        parsed["programming_languages"] = split_tech_items(user_input)

    for category, values in parsed.items():
        deduplicated: list[str] = []
        seen: set[str] = set()
        for value in values:
            key = value.lower()
            if value and key not in seen:
                seen.add(key)
                deduplicated.append(value)
        parsed[category] = deduplicated

    return parsed


def get_chat_input_placeholder() -> str:
    """Return a stage-aware placeholder for the chat input."""
    stage = st.session_state.conversation_stage
    placeholders = {
        INITIAL_CONVERSATION_STAGE: "Enter your full name",
        EMAIL_COLLECTION_STAGE: "Enter your email address",
        PHONE_COLLECTION_STAGE: "Enter your phone number",
        EXPERIENCE_COLLECTION_STAGE: "Enter your years of experience",
        ROLE_COLLECTION_STAGE: "Enter your desired role",
        LOCATION_COLLECTION_STAGE: "Enter your current location",
        TECH_STACK_COLLECTION_STAGE: (
            "Example: Languages: Python, JavaScript; Frameworks: Flask; "
            "Databases: PostgreSQL; Tools/Platforms: Docker"
        ),
        COMPLETED_CONVERSATION_STAGE: "Conversation complete. Reset to start again.",
    }
    return placeholders.get(stage, "Share your response here")


def get_next_stage_prompt(next_stage: str) -> str:
    """Return the next assistant prompt for the conversation flow."""
    prompts = {
        EMAIL_COLLECTION_STAGE: "Could you please share your email address?",
        PHONE_COLLECTION_STAGE: "Great. What is the best phone number to reach you?",
        EXPERIENCE_COLLECTION_STAGE: "How many years of professional experience do you have?",
        ROLE_COLLECTION_STAGE: "Which role are you currently targeting or applying for?",
        LOCATION_COLLECTION_STAGE: "What is your current location?",
        TECH_STACK_COLLECTION_STAGE: (
            "Please share your tech stack, including programming languages, frameworks, "
            "databases, and tools or platforms. You can use a format like: "
            "Languages: Python, JavaScript; Frameworks: Flask; Databases: PostgreSQL; "
            "Tools/Platforms: Docker."
        ),
    }
    return prompts[next_stage]


def get_question_generation_messages(technologies: list[str]) -> list[dict[str, str]]:
    """Build the LM Studio prompt used to generate technical interview questions."""
    technology_list = ", ".join(technologies)
    return [
        {
            "role": "system",
            "content": (
                "You are a technical interviewer. Return valid JSON only. "
                "Each top-level key must be a technology name and each value must be "
                "an array of exactly 3 concise, practical, intermediate-level interview questions."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Candidate technologies: {technology_list}\n"
                "Generate 3 unique interview questions for each technology.\n"
                "Return JSON only in this format:\n"
                '{"Python": ["Question 1?", "Question 2?", "Question 3?"]}'
            ),
        },
    ]


def extract_json_object(raw_response: str) -> dict[str, object]:
    """Extract a JSON object from a model response."""
    cleaned = raw_response.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start_index = cleaned.find("{")
    end_index = cleaned.rfind("}")
    if start_index == -1 or end_index == -1:
        raise ValueError("No JSON object found in the model response.")

    return json.loads(cleaned[start_index : end_index + 1])


def get_fallback_questions_for_technology(technology: str) -> list[str]:
    """Return deterministic fallback questions for a technology."""
    return [
        f"What problem does {technology} solve, and when would you choose to use it?",
        f"Can you describe a practical project or task where you used {technology}?",
        f"What are some common challenges or best practices when working with {technology}?",
    ]


def normalize_generated_questions(
    raw_questions: dict[str, object],
    technologies: list[str],
) -> dict[str, list[str]]:
    """Normalize generated questions into a consistent technology-to-questions mapping."""
    question_lookup = {
        key.strip().lower(): value for key, value in raw_questions.items() if isinstance(key, str)
    }
    normalized: dict[str, list[str]] = {}

    for technology in technologies:
        candidate_questions = question_lookup.get(technology.lower(), [])
        cleaned_questions = [
            str(question).strip()
            for question in candidate_questions
            if str(question).strip()
        ][:3]

        while len(cleaned_questions) < 3:
            fallback_question = get_fallback_questions_for_technology(technology)[len(cleaned_questions)]
            cleaned_questions.append(fallback_question)

        normalized[technology] = cleaned_questions

    return normalized


def generate_technical_questions(
    service: LLMService,
    technologies: list[str],
) -> dict[str, list[str]]:
    """Generate technical interview questions for the collected tech stack."""
    if not technologies:
        return {}

    try:
        raw_response = service.generate_response(
            get_question_generation_messages(technologies),
            temperature=0.2,
            max_tokens=900,
        )
        parsed_response = extract_json_object(raw_response)
    except Exception:
        parsed_response = {}

    return normalize_generated_questions(parsed_response, technologies)


def format_technical_questions_response(
    generated_questions: dict[str, list[str]],
) -> str:
    """Format the generated technical questions for chat display."""
    response_lines = [
        "Thank you for sharing your tech stack. Here are your technical interview questions:",
        "",
    ]

    for technology, questions in generated_questions.items():
        response_lines.append(f"**{technology}**")
        for index, question in enumerate(questions, start=1):
            response_lines.append(f"{index}. {question}")
        response_lines.append("")

    response_lines.append(EXIT_RESPONSE)
    return "\n".join(response_lines).strip()


def process_candidate_field_input(user_message: str) -> str:
    """Store candidate details for the current stage and return the next assistant prompt."""
    current_stage = st.session_state.conversation_stage
    field_name = FIELD_BY_STAGE[current_stage]
    st.session_state.candidate_data[field_name] = user_message

    next_stage = NEXT_STAGE_BY_STAGE[current_stage]
    st.session_state.conversation_stage = next_stage

    if current_stage == INITIAL_CONVERSATION_STAGE:
        first_name = user_message.split()[0]
        return f"Nice to meet you, {first_name}. {get_next_stage_prompt(next_stage)}"

    return get_next_stage_prompt(next_stage)


def process_tech_stack_input(user_message: str, service: LLMService) -> str:
    """Store the tech stack, generate questions, and complete the conversation."""
    parsed_tech_stack = parse_tech_stack_input(user_message)
    technologies = get_flat_technologies(parsed_tech_stack)

    if not technologies:
        return (
            "Please share at least one technology from your stack so I can generate "
            "technical interview questions for you."
        )

    st.session_state.tech_stack = parsed_tech_stack
    st.session_state.generated_questions = generate_technical_questions(service, technologies)
    CandidateService().store_candidate(
        st.session_state.candidate_data,
        st.session_state.tech_stack,
        st.session_state.generated_questions,
    )
    st.session_state.conversation_stage = COMPLETED_CONVERSATION_STAGE

    return format_technical_questions_response(st.session_state.generated_questions)


def process_user_message(user_message: str, service: LLMService) -> str:
    """Process a user message according to the staged conversation flow."""
    cleaned_message = normalize_user_text(user_message)

    if not cleaned_message:
        return FALLBACK_RESPONSE

    if is_exit_intent(cleaned_message):
        st.session_state.conversation_stage = COMPLETED_CONVERSATION_STAGE
        return EXIT_RESPONSE

    if st.session_state.conversation_stage == COMPLETED_CONVERSATION_STAGE:
        return EXIT_RESPONSE

    if st.session_state.conversation_stage == TECH_STACK_COLLECTION_STAGE:
        return process_tech_stack_input(cleaned_message, service)

    return process_candidate_field_input(cleaned_message)


def render_sidebar(service: LLMService | None, service_error: str | None) -> None:
    """Render the sidebar controls and configuration summary."""
    with st.sidebar:
        st.header("Session")
        st.write("Use this chat to collect candidate details and generate technical questions.")

        if service is not None:
            st.caption(f"Model: {service.model_name}")
            st.caption(f"Endpoint: {service.base_url}")
        else:
            st.warning(f"LM Studio configuration issue: {service_error}")

        st.caption(f"Conversation stage: {get_stage_label(st.session_state.conversation_stage)}")
        st.caption(
            f"Candidate fields collected: {get_collected_candidate_fields_count()}/{len(CANDIDATE_FIELDS)}"
        )
        st.caption(f"Technologies captured: {len(get_flat_technologies(st.session_state.tech_stack))}")

        if st.button("Reset conversation", use_container_width=True):
            reset_conversation()
            st.rerun()


def render_chat_history() -> None:
    """Render all visible chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(page_title=APP_TITLE, layout="centered")
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    initialize_session_state()

    service: LLMService | None = None
    service_error: str | None = None
    try:
        service = LLMService()
    except Exception as exc:
        service_error = str(exc)

    render_sidebar(service, service_error)
    render_chat_history()

    prompt = st.chat_input(
        get_chat_input_placeholder(),
        disabled=service is None or st.session_state.conversation_stage == COMPLETED_CONVERSATION_STAGE,
        key="candidate_response_input",
    )

    if prompt is None:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})

    if service is None:
        assistant_response = (
            "I couldn't connect to the LM Studio configuration for this app. "
            f"Please review the setup and try again. Details: {service_error}"
        )
    else:
        try:
            with st.spinner("Generating response..."):
                assistant_response = process_user_message(prompt, service)
        except Exception as exc:
            assistant_response = (
                "I couldn't continue the hiring flow right now because the local LM Studio "
                f"server request failed. Please try again. Details: {exc}"
            )

    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    st.rerun()


if __name__ == "__main__":
    main()
