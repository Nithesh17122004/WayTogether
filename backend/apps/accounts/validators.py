from pathlib import Path

from django.core.exceptions import ValidationError

MAX_AADHAAR_FILE_SIZE = 8 * 1024 * 1024
MAX_PHOTO_FILE_SIZE = 5 * 1024 * 1024

DOCUMENT_SIGNATURES = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
}
PHOTO_SIGNATURES = {
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
}


def _validate_signature(uploaded_file, allowed, max_size, label):
    suffix = Path(uploaded_file.name).suffix.lower()
    expected = allowed.get(suffix)
    if not expected:
        raise ValidationError(f"Upload a valid {label} as PDF, JPG or PNG.")
    if uploaded_file.size > max_size:
        raise ValidationError(f"The {label} must be {max_size // (1024 * 1024)} MB or smaller.")

    expected_mime, signature = expected
    if getattr(uploaded_file, "content_type", None) not in (None, "", expected_mime):
        raise ValidationError("The uploaded file content type does not match its extension.")

    position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    header = uploaded_file.read(len(signature))
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(position)
    if not header.startswith(signature):
        raise ValidationError("The uploaded file signature is invalid.")


def validate_masked_aadhaar_file(uploaded_file):
    """Validate an Aadhaar proof upload; the caller must collect a masked copy only."""
    _validate_signature(
        uploaded_file,
        DOCUMENT_SIGNATURES,
        MAX_AADHAAR_FILE_SIZE,
        "masked Aadhaar document",
    )


def validate_passenger_photo(uploaded_file):
    """Validate a raster passenger photo; PDFs are not accepted for profile photos."""
    _validate_signature(
        uploaded_file,
        PHOTO_SIGNATURES,
        MAX_PHOTO_FILE_SIZE,
        "passenger photo",
    )
