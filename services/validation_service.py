"""Validation helpers for candidate screening inputs."""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
EXPERIENCE_PATTERN = re.compile(r"^(?P<years>\d+(?:\.\d+)?)\s*(?:years?|yrs?)?$", re.IGNORECASE)

EMAIL_ERROR_MESSAGE = "Please enter a valid email address, for example `name@example.com`."
PHONE_ERROR_MESSAGE = "Please enter a valid phone number with 10 to 15 digits."
EXPERIENCE_ERROR_MESSAGE = (
    "Please enter your experience as a number, for example `3` or `3.5 years`."
)
FULL_NAME_ERROR_MESSAGE = "Please enter your full name to continue."
DESIRED_ROLE_ERROR_MESSAGE = "Please share the role you are targeting."
CURRENT_LOCATION_ERROR_MESSAGE = "Please share your current location."


@dataclass(frozen=True)
class ValidationResult:
    """Return value for field validation."""

    is_valid: bool
    normalized_value: str
    error_message: str = ""


def build_valid_result(value: str) -> ValidationResult:
    """Create a successful validation result."""
    return ValidationResult(is_valid=True, normalized_value=value)


def build_invalid_result(message: str) -> ValidationResult:
    """Create a failed validation result."""
    return ValidationResult(is_valid=False, normalized_value="", error_message=message)


def validate_full_name(value: str) -> ValidationResult:
    """Validate a candidate full name."""
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) < 2 or not re.search(r"[A-Za-z]", normalized):
        return build_invalid_result(FULL_NAME_ERROR_MESSAGE)

    return build_valid_result(normalized)


def validate_email(value: str) -> ValidationResult:
    """Validate and normalize an email address."""
    normalized = value.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized):
        return build_invalid_result(EMAIL_ERROR_MESSAGE)

    return build_valid_result(normalized)


def validate_phone(value: str) -> ValidationResult:
    """Validate and normalize a phone number."""
    normalized = re.sub(r"[()\s-]+", "", value).strip()
    if normalized.startswith("+"):
        digits_only = normalized[1:]
    else:
        digits_only = normalized

    if not digits_only.isdigit() or not 10 <= len(digits_only) <= 15:
        return build_invalid_result(PHONE_ERROR_MESSAGE)

    return build_valid_result(normalized)


def validate_experience(value: str) -> ValidationResult:
    """Validate and normalize years of experience."""
    normalized = value.strip()
    match = EXPERIENCE_PATTERN.fullmatch(normalized)
    if match is None:
        return build_invalid_result(EXPERIENCE_ERROR_MESSAGE)

    years = match.group("years")
    suffix = "year" if years == "1" else "years"
    return build_valid_result(f"{years} {suffix}")


def validate_desired_role(value: str) -> ValidationResult:
    """Validate the desired role field."""
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        return build_invalid_result(DESIRED_ROLE_ERROR_MESSAGE)

    return build_valid_result(normalized)


def validate_current_location(value: str) -> ValidationResult:
    """Validate the current location field."""
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        return build_invalid_result(CURRENT_LOCATION_ERROR_MESSAGE)

    return build_valid_result(normalized)


def validate_candidate_field(field_name: str, value: str) -> ValidationResult:
    """Validate one candidate field by name."""
    validators = {
        "full_name": validate_full_name,
        "email": validate_email,
        "phone": validate_phone,
        "experience": validate_experience,
        "desired_role": validate_desired_role,
        "current_location": validate_current_location,
    }

    validator = validators.get(field_name)
    if validator is None:
        return build_valid_result(value.strip())

    return validator(value)
