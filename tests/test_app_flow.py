"""Automated tests for the TalentScout hiring assistant flow."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

import app
from services.candidate_service import CandidateService


class FakeLLMService:
    """Simple fake service used to avoid live model calls in tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_response(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Return deterministic JSON for technical question generation."""
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return json.dumps(
            {
                "Python": [
                    "What problem does list comprehension solve in Python?",
                    "How do decorators work in Python?",
                    "How would you manage dependencies in a Python project?",
                ],
                "JavaScript": [
                    "What is the difference between let, const, and var?",
                    "How does event bubbling work in JavaScript?",
                    "When would you use async and await?",
                ],
                "Flask": [
                    "How does routing work in Flask?",
                    "What are blueprints in Flask?",
                    "How do you validate request data in Flask?",
                ],
                "PostgreSQL": [
                    "When would you create an index in PostgreSQL?",
                    "How do joins work in PostgreSQL?",
                    "What is a transaction in PostgreSQL?",
                ],
                "Docker": [
                    "Why would you use Docker for local development?",
                    "What is the difference between an image and a container?",
                    "How do volumes help in Docker workflows?",
                ],
            }
        )


class HiringFlowTests(unittest.TestCase):
    """Validate the key Step 19 screening scenarios."""

    def setUp(self) -> None:
        st.session_state.clear()
        app.initialize_session_state()
        self.fake_service = FakeLLMService()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.candidates_path = Path(self.temp_dir.name) / "candidates.json"

    def tearDown(self) -> None:
        st.session_state.clear()
        self.temp_dir.cleanup()

    def test_valid_email_is_accepted(self) -> None:
        """A valid email should be stored and advance the stage."""
        st.session_state.conversation_stage = app.EMAIL_COLLECTION_STAGE

        response = app.process_user_message("candidate@example.com", self.fake_service)

        self.assertEqual(st.session_state.candidate_data["email"], "candidate@example.com")
        self.assertEqual(st.session_state.conversation_stage, app.PHONE_COLLECTION_STAGE)
        self.assertIn("phone number", response.lower())

    def test_invalid_email_returns_error_and_keeps_stage(self) -> None:
        """An invalid email should not advance the conversation."""
        st.session_state.conversation_stage = app.EMAIL_COLLECTION_STAGE

        response = app.process_user_message("not-an-email", self.fake_service)

        self.assertEqual(st.session_state.candidate_data["email"], "")
        self.assertEqual(st.session_state.conversation_stage, app.EMAIL_COLLECTION_STAGE)
        self.assertIn("valid email address", response.lower())

    def test_empty_input_triggers_fallback_response(self) -> None:
        """Blank input should be redirected with the fallback response."""
        response = app.process_user_message("   ", self.fake_service)

        self.assertEqual(response, app.FALLBACK_RESPONSE)
        self.assertEqual(st.session_state.conversation_stage, app.INITIAL_CONVERSATION_STAGE)

    def test_random_unrelated_question_is_redirected(self) -> None:
        """Unrelated input should not derail the screening flow."""
        response = app.process_user_message("What is the weather today?", self.fake_service)

        self.assertEqual(response, app.FALLBACK_RESPONSE)
        self.assertEqual(st.session_state.conversation_stage, app.INITIAL_CONVERSATION_STAGE)

    def test_exit_command_completes_the_conversation(self) -> None:
        """Exit intent should close the conversation politely."""
        st.session_state.conversation_stage = app.ROLE_COLLECTION_STAGE

        response = app.process_user_message("Thank you!", self.fake_service)

        self.assertEqual(response, app.EXIT_RESPONSE)
        self.assertEqual(st.session_state.conversation_stage, app.COMPLETED_CONVERSATION_STAGE)

    def test_multiple_tech_stack_input_generates_questions_and_saves_record(self) -> None:
        """A structured tech stack should produce questions and persist a record."""
        st.session_state.conversation_stage = app.TECH_STACK_COLLECTION_STAGE
        st.session_state.candidate_data.update(
            {
                "full_name": "Asha Sharma",
                "email": "asha@example.com",
                "phone": "+919876543210",
                "experience": "3.5 years",
                "desired_role": "Python Developer",
                "current_location": "Ahmedabad",
            }
        )

        with patch("app.CandidateService", return_value=CandidateService(self.candidates_path)):
            response = app.process_user_message(
                (
                    "Languages: Python, JavaScript; Frameworks: Flask; "
                    "Databases: PostgreSQL; Tools/Platforms: Docker"
                ),
                self.fake_service,
            )

        self.assertEqual(st.session_state.conversation_stage, app.COMPLETED_CONVERSATION_STAGE)
        self.assertIn("technical interview questions", response.lower())
        self.assertEqual(
            sorted(st.session_state.generated_questions.keys()),
            ["Docker", "Flask", "JavaScript", "PostgreSQL", "Python"],
        )
        for questions in st.session_state.generated_questions.values():
            self.assertEqual(len(questions), 3)

        stored_records = json.loads(self.candidates_path.read_text(encoding="utf-8"))
        self.assertEqual(len(stored_records), 1)
        self.assertEqual(stored_records[0]["email"], "asha@example.com")
        self.assertIn("Python", stored_records[0]["generated_questions"])

    def test_initial_streamlit_ui_renders_core_elements(self) -> None:
        """The Streamlit UI should render the main chat shell."""
        at = AppTest.from_file("app.py")
        at.run(timeout=20)

        self.assertEqual(at.title[0].value, app.APP_TITLE)
        self.assertEqual(at.button[0].label, "Reset conversation")
        self.assertEqual(len(at.chat_message), 1)
        self.assertEqual([metric.label for metric in at.metric], ["Progress", "Fields Captured", "Conversation Turns"])


if __name__ == "__main__":
    unittest.main()
