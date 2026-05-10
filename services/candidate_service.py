"""JSON-backed storage for completed candidate screening records."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CANDIDATES_FILE = Path(__file__).resolve().parents[1] / "data" / "candidates.json"


class CandidateService:
    """Persist completed candidate screening records to a local JSON file."""

    def __init__(self, file_path: str | Path | None = None) -> None:
        self.file_path = Path(file_path) if file_path is not None else DEFAULT_CANDIDATES_FILE

    def load_candidates(self) -> list[dict[str, Any]]:
        """Load all stored candidate records from disk."""
        if not self.file_path.exists():
            return []

        raw_content = self.file_path.read_text(encoding="utf-8").strip()
        if not raw_content:
            return []

        parsed_content = json.loads(raw_content)
        if not isinstance(parsed_content, list):
            raise ValueError("Candidate storage file must contain a JSON array.")

        return parsed_content

    def save_candidates(self, candidates: list[dict[str, Any]]) -> None:
        """Write the full candidate record list to disk."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(candidates, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def build_candidate_record(
        self,
        candidate_data: dict[str, str],
        tech_stack: dict[str, list[str]],
        generated_questions: dict[str, list[str]],
    ) -> dict[str, Any]:
        """Create the candidate record structure stored in the JSON file."""
        flat_tech_stack: list[str] = []
        seen: set[str] = set()

        for values in tech_stack.values():
            for value in values:
                cleaned_value = value.strip()
                key = cleaned_value.lower()
                if cleaned_value and key not in seen:
                    seen.add(key)
                    flat_tech_stack.append(cleaned_value)

        return {
            "name": candidate_data.get("full_name", ""),
            "email": candidate_data.get("email", ""),
            "phone": candidate_data.get("phone", ""),
            "experience": candidate_data.get("experience", ""),
            "desired_role": candidate_data.get("desired_role", ""),
            "current_location": candidate_data.get("current_location", ""),
            "tech_stack": flat_tech_stack,
            "tech_stack_details": tech_stack,
            "generated_questions": generated_questions,
            "submitted_at": datetime.now().isoformat(timespec="seconds"),
        }

    def store_candidate(
        self,
        candidate_data: dict[str, str],
        tech_stack: dict[str, list[str]],
        generated_questions: dict[str, list[str]],
    ) -> dict[str, Any]:
        """Append one completed candidate record to the JSON store."""
        candidates = self.load_candidates()
        record = self.build_candidate_record(candidate_data, tech_stack, generated_questions)
        candidates.append(record)
        self.save_candidates(candidates)
        return record
