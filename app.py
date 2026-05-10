"""Streamlit interface for the TalentScout hiring assistant."""

from __future__ import annotations

import json
import re

import streamlit as st

from prompts.info_prompt import (
    get_chat_input_placeholder as get_stage_input_placeholder,
    get_first_name_acknowledgement,
    get_next_stage_prompt,
    get_welcome_message,
)
from prompts.system_prompt import EXIT_RESPONSE, FALLBACK_RESPONSE
from prompts.technical_prompt import build_technical_question_messages
from services.candidate_service import CandidateService
from services.llm_service import LLMService
from services.validation_service import validate_candidate_field

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
COMPLETED_CONVERSATION_NOTICE = "Conversation closed. Use Reset conversation to start again."
PROGRESS_STEPS = (
    (INITIAL_CONVERSATION_STAGE, "Greeting"),
    (EMAIL_COLLECTION_STAGE, "Email"),
    (PHONE_COLLECTION_STAGE, "Phone"),
    (EXPERIENCE_COLLECTION_STAGE, "Experience"),
    (ROLE_COLLECTION_STAGE, "Role"),
    (LOCATION_COLLECTION_STAGE, "Location"),
    (TECH_STACK_COLLECTION_STAGE, "Tech Stack"),
    (COMPLETED_CONVERSATION_STAGE, "Questions"),
)
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
LOW_SIGNAL_INPUTS = {
    "hmm",
    "hmmm",
    "idk",
    "i don't know",
    "i dont know",
    "na",
    "n/a",
    "none",
    "not sure",
    "ok",
    "okay",
    "skip",
}
ABUSIVE_TERMS = (
    "asshole",
    "bitch",
    "dumb",
    "fuck",
    "fucking",
    "idiot",
    "moron",
    "shut up",
    "stupid",
)
UNRELATED_KEYWORDS = (
    "bitcoin",
    "capital of",
    "celebrity",
    "cricket",
    "crypto",
    "football",
    "joke",
    "movie",
    "music",
    "news",
    "president",
    "prime minister",
    "recipe",
    "song",
    "sports",
    "stock market",
    "tell me a joke",
    "time now",
    "translate",
    "weather",
)
GENERAL_QUERY_PREFIXES = (
    "can you explain",
    "how do i",
    "how to",
    "tell me about",
    "what is",
    "when is",
    "where is",
    "who is",
    "why is",
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
    get_welcome_message()
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
        "conversation_history": create_initial_messages(),
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


def normalize_intent_text(text: str) -> str:
    """Normalize text for intent matching by removing punctuation noise."""
    normalized = normalize_user_text(text).lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def is_exit_intent(text: str) -> bool:
    """Return True when the user is trying to end the conversation."""
    normalized = normalize_intent_text(text)
    return normalized in EXIT_KEYWORDS


def is_low_signal_input(text: str) -> bool:
    """Return True when the input is too vague to be useful."""
    normalized = normalize_user_text(text).lower()
    return normalized in LOW_SIGNAL_INPUTS


def is_abusive_input(text: str) -> bool:
    """Return True when the input contains abusive or hostile language."""
    normalized = normalize_user_text(text).lower()
    return any(term in normalized for term in ABUSIVE_TERMS)


def is_unrelated_input(text: str) -> bool:
    """Return True when the input is clearly unrelated to the hiring flow."""
    normalized = normalize_user_text(text).lower()
    if any(keyword in normalized for keyword in UNRELATED_KEYWORDS):
        return True

    if "?" in normalized and normalized.startswith(GENERAL_QUERY_PREFIXES):
        return True

    return False


def should_return_fallback_response(text: str) -> bool:
    """Return True when the fallback response should be used."""
    return (
        not text
        or is_low_signal_input(text)
        or is_abusive_input(text)
        or is_unrelated_input(text)
    )


def get_stage_label(stage: str) -> str:
    """Return a human-friendly label for the current conversation stage."""
    return STAGE_LABELS.get(stage, stage.replace("_", " ").title())


def get_collected_candidate_fields_count() -> int:
    """Return how many candidate fields currently have values."""
    return sum(1 for value in st.session_state.candidate_data.values() if value)


def append_conversation_message(role: str, content: str) -> None:
    """Append a message to both the UI messages and the stored conversation history."""
    message = {"role": role, "content": content}
    st.session_state.messages.append(message)
    st.session_state.conversation_history.append(message)


def get_conversation_turn_count() -> int:
    """Return the number of stored user and assistant turns in conversation history."""
    return sum(
        1
        for message in st.session_state.conversation_history
        if message.get("role") in {"user", "assistant"}
    )


def get_progress_step_index(stage: str | None = None) -> int:
    """Return the current progress-step index for the conversation stage."""
    current_stage = stage or st.session_state.conversation_stage
    for index, (step_stage, _) in enumerate(PROGRESS_STEPS):
        if current_stage == step_stage:
            return index
    return 0


def get_progress_percentage() -> int:
    """Return completion percentage for the guided screening flow."""
    return int(((get_progress_step_index() + 1) / len(PROGRESS_STEPS)) * 100)


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
    return get_stage_input_placeholder(st.session_state.conversation_stage)


def get_chat_avatar(role: str) -> str:
    """Return the avatar icon used for each chat role."""
    if role == "assistant":
        return ":material/smart_toy:"
    return ":material/person:"


def inject_custom_css() -> None:
    """Apply custom styling for the TalentScout interface."""
    st.markdown(
        """
        <style>
        :root {
            --ts-ink: #1f2933;
            --ts-muted: #5f6c7b;
            --ts-surface: rgba(255, 252, 246, 0.92);
            --ts-line: rgba(175, 122, 57, 0.18);
            --ts-accent: #bf6b2c;
            --ts-accent-deep: #8d4f1f;
            --ts-success: #23655b;
            --ts-shadow: 0 18px 48px rgba(68, 47, 30, 0.10);
            --ts-heading: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
            --ts-body: "Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif;
        }

        html, body, [class*="css"] {
            font-family: var(--ts-body);
            color: var(--ts-ink);
        }

        div[data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(255, 210, 158, 0.24), transparent 30%),
                radial-gradient(circle at top right, rgba(120, 183, 172, 0.20), transparent 28%),
                linear-gradient(180deg, #fffdf8 0%, #f8f2e9 52%, #f4ece2 100%);
        }

        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(255, 250, 242, 0.97) 0%, rgba(246, 238, 227, 0.97) 100%);
            border-right: 1px solid var(--ts-line);
        }

        div[data-testid="stHeader"] {
            background: rgba(255, 255, 255, 0);
        }

        div[data-testid="stMainBlockContainer"] {
            max-width: 1080px;
            padding-top: 2.2rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            font-family: var(--ts-heading);
            letter-spacing: -0.02em;
            color: #1f2a33;
        }

        div[data-testid="stMetric"] {
            background: var(--ts-surface);
            border: 1px solid var(--ts-line);
            border-radius: 20px;
            padding: 0.85rem 1rem;
            box-shadow: var(--ts-shadow);
        }

        div[data-testid="stMetric"] label {
            color: var(--ts-muted);
        }

        div[data-testid="stChatMessage"] {
            background: rgba(255, 255, 255, 0.58);
            border: 1px solid rgba(191, 107, 44, 0.10);
            border-radius: 24px;
            box-shadow: 0 8px 28px rgba(67, 52, 39, 0.06);
            padding: 0.35rem 0.45rem;
            backdrop-filter: blur(2px);
        }

        div[data-testid="stChatInput"] {
            background: rgba(255, 251, 245, 0.94);
            border: 1px solid rgba(191, 107, 44, 0.16);
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            box-shadow: 0 14px 30px rgba(77, 55, 36, 0.10);
        }

        div[data-testid="stButton"] button {
            border-radius: 999px;
            border: 1px solid rgba(191, 107, 44, 0.18);
            background: linear-gradient(135deg, #fff7ee 0%, #f6debe 100%);
            color: var(--ts-accent-deep);
        }

        .ts-hero-card {
            position: relative;
            overflow: hidden;
            border-radius: 28px;
            border: 1px solid var(--ts-line);
            background: linear-gradient(135deg, rgba(255, 250, 243, 0.97) 0%, rgba(245, 234, 219, 0.95) 100%);
            box-shadow: var(--ts-shadow);
            padding: 1.35rem 1.45rem;
            margin-bottom: 1rem;
        }

        .ts-hero-card::after {
            content: "";
            position: absolute;
            inset: auto -3rem -4rem auto;
            width: 12rem;
            height: 12rem;
            background: radial-gradient(circle, rgba(191, 107, 44, 0.17), transparent 70%);
        }

        .ts-kicker {
            display: inline-block;
            font-size: 0.76rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--ts-accent-deep);
            background: rgba(191, 107, 44, 0.10);
            border: 1px solid rgba(191, 107, 44, 0.14);
            border-radius: 999px;
            padding: 0.28rem 0.7rem;
            margin-bottom: 0.9rem;
        }

        .ts-hero-layout {
            display: grid;
            grid-template-columns: minmax(0, 1.7fr) minmax(220px, 0.9fr);
            gap: 1rem;
            align-items: start;
        }

        .ts-hero-copy h3 {
            margin: 0 0 0.35rem 0;
            font-size: 1.55rem;
        }

        .ts-hero-copy p, .ts-sidebar-card p {
            margin: 0;
            color: var(--ts-muted);
            line-height: 1.55;
        }

        .ts-stage-summary {
            display: grid;
            gap: 0.65rem;
        }

        .ts-stage-box {
            background: var(--ts-surface);
            border: 1px solid var(--ts-line);
            border-radius: 18px;
            padding: 0.85rem 0.95rem;
        }

        .ts-stage-box span {
            display: block;
            font-size: 0.74rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--ts-muted);
            margin-bottom: 0.18rem;
        }

        .ts-stage-box strong {
            font-size: 1.02rem;
            color: #22313b;
        }

        .ts-progress-strip {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-bottom: 1rem;
        }

        .ts-progress-step {
            border-radius: 999px;
            border: 1px solid var(--ts-line);
            padding: 0.42rem 0.72rem;
            background: rgba(255, 255, 255, 0.62);
            color: var(--ts-muted);
            font-size: 0.86rem;
        }

        .ts-progress-step.is-complete {
            background: rgba(35, 101, 91, 0.10);
            border-color: rgba(35, 101, 91, 0.22);
            color: var(--ts-success);
        }

        .ts-progress-step.is-active {
            background: linear-gradient(135deg, #f7d7b7 0%, #f0ba87 100%);
            border-color: rgba(191, 107, 44, 0.28);
            color: #663818;
            font-weight: 600;
        }

        .ts-sidebar-card {
            border-radius: 22px;
            border: 1px solid var(--ts-line);
            background: linear-gradient(180deg, rgba(255, 250, 243, 0.96) 0%, rgba(249, 239, 226, 0.96) 100%);
            padding: 1rem;
            box-shadow: 0 12px 28px rgba(77, 55, 36, 0.08);
            margin-bottom: 1rem;
        }

        .ts-sidebar-card h3 {
            margin: 0.2rem 0 0.3rem 0;
            font-size: 1.3rem;
        }

        @media (max-width: 900px) {
            .ts-hero-layout {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero_panel() -> None:
    """Render the branded hero card at the top of the page."""
    st.markdown(
        f"""
        <div class="ts-hero-card">
            <div class="ts-kicker">TalentScout Hiring Desk</div>
            <div class="ts-hero-layout">
                <div class="ts-hero-copy">
                    <h3>Structured screening with local AI support.</h3>
                    <p>
                        Move through the candidate journey one prompt at a time, preserve
                        conversation context, and generate targeted technical questions from the
                        declared stack.
                    </p>
                </div>
                <div class="ts-stage-summary">
                    <div class="ts-stage-box">
                        <span>Current Stage</span>
                        <strong>{get_stage_label(st.session_state.conversation_stage)}</strong>
                    </div>
                    <div class="ts-stage-box">
                        <span>Flow Progress</span>
                        <strong>{get_progress_percentage()}% complete</strong>
                    </div>
                    <div class="ts-stage-box">
                        <span>Captured Signals</span>
                        <strong>{get_collected_candidate_fields_count()} fields, {len(get_flat_technologies(st.session_state.tech_stack))} technologies</strong>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_progress_strip() -> None:
    """Render a visual stage-by-stage progress indicator."""
    current_index = get_progress_step_index()
    steps_markup: list[str] = []

    for index, (_, label) in enumerate(PROGRESS_STEPS):
        css_class = "ts-progress-step"
        if index < current_index:
            css_class += " is-complete"
        elif index == current_index:
            css_class += " is-active"
        steps_markup.append(f'<span class="{css_class}">{label}</span>')

    st.markdown(
        f'<div class="ts-progress-strip">{"".join(steps_markup)}</div>',
        unsafe_allow_html=True,
    )


def render_summary_metrics() -> None:
    """Render compact summary metrics for the current screening session."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Progress", f"{get_progress_percentage()}%")
    with col2:
        st.metric("Fields Captured", f"{get_collected_candidate_fields_count()}/{len(CANDIDATE_FIELDS)}")
    with col3:
        st.metric("Conversation Turns", str(get_conversation_turn_count()))


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
            build_technical_question_messages(
                technologies,
                conversation_history=st.session_state.conversation_history,
                candidate_data=st.session_state.candidate_data,
            ),
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
    validation_result = validate_candidate_field(field_name, user_message)
    if not validation_result.is_valid:
        return validation_result.error_message

    st.session_state.candidate_data[field_name] = validation_result.normalized_value

    next_stage = NEXT_STAGE_BY_STAGE[current_stage]
    st.session_state.conversation_stage = next_stage

    if current_stage == INITIAL_CONVERSATION_STAGE:
        first_name = validation_result.normalized_value.split()[0]
        return f"{get_first_name_acknowledgement(first_name)} {get_next_stage_prompt(next_stage)}"

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

    if should_return_fallback_response(cleaned_message):
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
        st.markdown(
            """
            <div class="ts-sidebar-card">
                <div class="ts-kicker">TalentScout</div>
                <h3>Screening Console</h3>
                <p>Track candidate progress, preserve context, and drive a guided hiring conversation from one workspace.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.subheader("Session")
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
        st.caption(f"Conversation turns stored: {get_conversation_turn_count()}")
        if st.session_state.conversation_stage == COMPLETED_CONVERSATION_STAGE:
            st.info(COMPLETED_CONVERSATION_NOTICE)

        if st.button("Reset conversation", use_container_width=True):
            reset_conversation()
            st.rerun()


def render_chat_history() -> None:
    """Render all visible chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=get_chat_avatar(message["role"])):
            st.markdown(message["content"])


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(page_title=APP_TITLE, layout="centered")
    inject_custom_css()
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    initialize_session_state()

    service: LLMService | None = None
    service_error: str | None = None
    try:
        service = LLMService()
    except Exception as exc:
        service_error = str(exc)

    render_hero_panel()
    render_progress_strip()
    render_summary_metrics()
    render_sidebar(service, service_error)
    render_chat_history()

    prompt = st.chat_input(
        get_chat_input_placeholder(),
        disabled=service is None or st.session_state.conversation_stage == COMPLETED_CONVERSATION_STAGE,
        key="candidate_response_input",
    )

    if prompt is None:
        return

    append_conversation_message("user", prompt)

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

    append_conversation_message("assistant", assistant_response)
    st.rerun()


if __name__ == "__main__":
    main()
