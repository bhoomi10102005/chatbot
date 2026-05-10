# TalentScout Hiring Assistant

## Project Overview

TalentScout Hiring Assistant is a local AI-powered screening chatbot built for the TalentScout assignment. The application guides candidates through a structured screening flow, collects essential hiring information, captures their tech stack, and generates tailored technical interview questions using a local LM Studio model.

The project is designed for local execution with Streamlit for the UI and LM Studio as the LLM runtime. Candidate data is stored in a local JSON file for simulation purposes.

## Features

- Guided one-question-at-a-time screening flow
- Candidate data collection for name, email, phone, experience, desired role, and location
- Structured tech stack capture for languages, frameworks, databases, and tools/platforms
- Technical interview question generation using a local LLM
- Conversation context tracking across the full screening session
- Validation for email, phone, experience, and required fields
- Fallback handling for empty, abusive, unclear, and unrelated input
- Exit handling with a professional closing response
- Local JSON-backed candidate data storage
- Enhanced Streamlit UI with branding, progress tracking, avatars, and custom styling
- Automated test coverage for core screening scenarios

## Tech Stack

- Frontend: Streamlit
- Backend: Python
- LLM Runtime: LM Studio Local Server
- Model: Llama 3 Instruct family, tested with `meta-llama-3-8b-instruct`
- Storage: Local JSON file in `data/candidates.json`

## Project Structure

```txt
talentscout-chatbot/
|-- app.py
|-- requirements.txt
|-- README.md
|-- .env
|-- prompts/
|   |-- system_prompt.py
|   |-- info_prompt.py
|   `-- technical_prompt.py
|-- services/
|   |-- llm_service.py
|   |-- candidate_service.py
|   `-- validation_service.py
|-- utils/
|   |-- helpers.py
|   `-- constants.py
|-- data/
|   `-- candidates.json
|-- screenshots/
|-- tests/
|   `-- test_app_flow.py
`-- docs/
```

## Installation

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install the project dependencies.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file in the project root with the following values:

```env
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio
MODEL_NAME=meta-llama-3-8b-instruct
LM_STUDIO_TEMPERATURE=0.7
LM_STUDIO_TIMEOUT=60
LM_STUDIO_MAX_TOKENS=512
```

## LM Studio Setup

1. Install LM Studio from `https://lmstudio.ai/`.
2. Download a compatible instruct model such as Llama 3 8B Instruct.
3. Open the `Local Server` section in LM Studio.
4. Load the installed model.
5. Start the local server.
6. Verify the server by opening:

```txt
http://localhost:1234/v1/models
```

If the endpoint responds with available model ids, the local API is ready.

## Running the Application

Start the Streamlit app from the project root:

```powershell
streamlit run app.py
```

If port `8501` is already in use:

```powershell
streamlit run app.py --server.port 8502
```

## Usage Guide

1. Launch the app in Streamlit.
2. Reply to the assistant step by step.
3. Provide your:
   - Full name
   - Email
   - Phone number
   - Experience
   - Desired role
   - Current location
4. Share your tech stack in a format such as:

```txt
Languages: Python, JavaScript; Frameworks: Flask; Databases: PostgreSQL; Tools/Platforms: Docker
```

5. Review the generated technical interview questions.
6. Use `Reset conversation` to start a new candidate session.

## Prompt Engineering

The project uses separate prompt modules for different responsibilities:

- `prompts/system_prompt.py`
  - Defines the assistant persona, fallback behavior, and exit behavior.
- `prompts/info_prompt.py`
  - Controls the one-question-at-a-time information collection experience.
- `prompts/technical_prompt.py`
  - Builds the LLM prompt for technical question generation using:
    - candidate profile summary
    - stored conversation history
    - declared technologies
    - strict JSON-only output instructions

Prompt design principles used in this project:

- Ask one question at a time
- Stay recruitment-focused
- Preserve context across the session
- Generate concise, practical, intermediate-level questions
- Redirect unrelated input instead of answering it

## Architecture

```txt
User
  ->
Streamlit UI
  ->
Conversation Manager in app.py
  ->
Prompt Builder
  ->
LM Studio OpenAI-compatible API
  ->
Local LLM response
```

Main modules:

- `app.py`: conversation flow, UI rendering, session state, fallback handling, and response formatting
- `services/llm_service.py`: LM Studio API client wrapper
- `services/candidate_service.py`: candidate data persistence
- `services/validation_service.py`: field validation logic
- `prompts/`: prompt definitions and prompt builders

## Testing

Run the automated test suite with:

```powershell
python -m unittest discover -s tests -v
```

Covered scenarios include:

- Valid email is accepted
- Invalid email returns an error
- Empty input triggers retry/fallback
- Random unrelated questions are redirected
- Exit commands end the conversation
- Multiple technologies generate questions and complete the flow
- Initial Streamlit UI renders correctly

## Technical Details

- Python is used for the full application stack.
- Streamlit powers the interactive chat interface.
- The OpenAI Python client is used against LM Studio's OpenAI-compatible local API.
- Candidate data is stored in `data/candidates.json`.
- The technical question generation flow uses the local LLM, while the candidate intake flow is stage-driven and validated in application logic.

## Challenges

- Maintaining a clean conversational flow while still validating user input strictly.
- Handling tech stack input in both structured and loose formats.
- Making the UI feel guided and polished without breaking Streamlit's rerun model.
- Keeping question generation robust even when the local model returns imperfect JSON.

## Solutions

- Used explicit conversation stages stored in `st.session_state`.
- Added reusable validation helpers for each candidate field.
- Added JSON extraction plus deterministic fallback questions for technical generation.
- Introduced progress indicators, summary metrics, and rerun-safe chat rendering to improve usability.

## Data Privacy Notes

- This project is intended for local development and simulated assignment use.
- Candidate data is stored locally in `data/candidates.json`.
- Do not use real sensitive candidate information in a public demo or repository.
- For a public submission, prefer anonymized sample records or an empty JSON array.

## Future Improvements

- Use the LLM for more of the live screening dialogue while preserving guardrails
- Add downloadable interview summaries for recruiters
- Add a dedicated admin view for stored candidate records
- Support multilingual screening flows
- Improve storage with SQLite or PostgreSQL instead of local JSON
- Add deployment and demo assets for submission packaging
