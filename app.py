"""Streamlit interface for the TalentScout hiring assistant."""

from __future__ import annotations

import streamlit as st

from prompts.system_prompt import get_system_prompt
from services.llm_service import LLMService

APP_TITLE = "TalentScout Hiring Assistant"
APP_SUBTITLE = "AI-powered candidate screening and technical evaluation"
WELCOME_MESSAGE = (
    "Welcome to TalentScout. I will guide you through a short screening conversation "
    "and collect one detail at a time. To get started, please share your full name."
)


def create_initial_messages() -> list[dict[str, str]]:
    """Create the initial visible chat history."""
    return [{"role": "assistant", "content": WELCOME_MESSAGE}]


def initialize_session_state() -> None:
    """Initialize Streamlit state used by the chat interface."""
    if "messages" not in st.session_state:
        st.session_state.messages = create_initial_messages()


def reset_conversation() -> None:
    """Reset the conversation back to the initial welcome message."""
    st.session_state.messages = create_initial_messages()


def build_model_messages() -> list[dict[str, str]]:
    """Build the message payload sent to the language model."""
    return [{"role": "system", "content": get_system_prompt()}, *st.session_state.messages]


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

        if st.button("Reset conversation", use_container_width=True):
            reset_conversation()
            st.rerun()


def render_chat_history() -> None:
    """Render all visible chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def generate_assistant_response(service: LLMService) -> str:
    """Request the next assistant response from LM Studio."""
    return service.generate_response(build_model_messages())


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
        "Share your response here",
        disabled=service is None,
    )

    if prompt is None:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if service is None:
        assistant_response = (
            "I couldn't connect to the LM Studio configuration for this app. "
            f"Please review the setup and try again. Details: {service_error}"
        )
    else:
        try:
            with st.spinner("Generating response..."):
                assistant_response = generate_assistant_response(service)
        except Exception as exc:
            assistant_response = (
                "I couldn't reach the local LM Studio server right now. "
                f"Please make sure the server is running and try again. Details: {exc}"
            )

    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    with st.chat_message("assistant"):
        st.markdown(assistant_response)


if __name__ == "__main__":
    main()
