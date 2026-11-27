from pathlib import Path

from django.core.exceptions import ValidationError

MAX_DOCUMENT_SIZE = 8 * 1024 * 1024
ALLOWED_DOCUMENTS = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
}


def validate_document_file(uploaded_file):
    """Allow small PDF/JPEG/PNG documents and reject spoofed extensions."""
    suffix = Path(uploaded_file.name).suffix.lower()
    expected = ALLOWED_DOCUMENTS.get(suffix)
    if not expected:
        raise ValidationError("Only PDF, JPG, JPEG and PNG documents are accepted.")

    if uploaded_file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError("Each document must be 8 MB or smaller.")

    expected_mime, signature = expected
    if getattr(uploaded_file, "content_type", None) not in (None, "", expected_mime):
        raise ValidationError("The file content type does not match its extension.")

    position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    header = uploaded_file.read(len(signature))
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(position)
    if not header.startswith(signature):
        raise ValidationError("The file content could not be verified. Upload a valid PDF, JPG or PNG.")


MAX_DRIVER_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024
DRIVER_PROFILE_PHOTO_SIGNATURES = {
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
}


def validate_driver_profile_photo(uploaded_file):
    """Accept only small JPEG/PNG headshots with matching file signatures."""
    suffix = Path(uploaded_file.name).suffix.lower()
    expected = DRIVER_PROFILE_PHOTO_SIGNATURES.get(suffix)
    if not expected:
        raise ValidationError("The driver profile photo must be JPG or PNG.")
    if uploaded_file.size > MAX_DRIVER_PROFILE_PHOTO_SIZE:
        raise ValidationError("The driver profile photo must be 5 MB or smaller.")
    expected_mime, signature = expected
    if getattr(uploaded_file, "content_type", None) not in (None, "", expected_mime):
        raise ValidationError("The profile photo content type does not match its extension.")
    position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    header = uploaded_file.read(len(signature))
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(position)
    if not header.startswith(signature):
        raise ValidationError("The profile photo file signature is invalid.")
