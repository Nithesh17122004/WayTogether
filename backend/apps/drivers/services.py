from django.utils import timezone

from .models import DriverProfile, Vehicle, VerificationDocument


REQUIRED_DRIVER_DOCUMENTS = (
    VerificationDocument.DocumentType.DRIVER_LICENSE,
    VerificationDocument.DocumentType.DRIVER_PHOTO,
)

# Vehicle photograph and pollution certificate are optional supporting items.
# RC and active insurance are the mandatory per-vehicle documents.
REQUIRED_VEHICLE_DOCUMENTS = (
    VerificationDocument.DocumentType.VEHICLE_REGISTRATION,
    VerificationDocument.DocumentType.INSURANCE,
)


def current_document(owner, document_type, vehicle=None):
    queryset = VerificationDocument.objects.filter(
        owner=owner,
        document_type=document_type,
        is_current=True,
    )
    if vehicle is None:
        queryset = queryset.filter(vehicle__isnull=True)
    else:
        queryset = queryset.filter(vehicle=vehicle)
    return queryset.order_by("-uploaded_at").first()


def recompute_vehicle_status(vehicle):
    if vehicle.verification_status == Vehicle.VerificationStatus.SUSPENDED:
        return vehicle.verification_status

    documents = {
        document_type: current_document(vehicle.owner, document_type, vehicle)
        for document_type in REQUIRED_VEHICLE_DOCUMENTS
    }
    has_any_document = VerificationDocument.objects.filter(
        owner=vehicle.owner,
        vehicle=vehicle,
        is_current=True,
    ).exists()

    if not has_any_document:
        next_status = Vehicle.VerificationStatus.DRAFT
    elif any(
        document and (
            document.review_status == VerificationDocument.ReviewStatus.REJECTED
            or document.is_expired
        )
        for document in documents.values()
    ):
        next_status = Vehicle.VerificationStatus.NEEDS_RESUBMISSION
    elif all(
        document
        and document.review_status == VerificationDocument.ReviewStatus.APPROVED
        and not document.is_expired
        for document in documents.values()
    ):
        next_status = Vehicle.VerificationStatus.APPROVED
    else:
        next_status = Vehicle.VerificationStatus.PENDING

    if vehicle.verification_status != next_status:
        vehicle.verification_status = next_status
        vehicle.save(update_fields=["verification_status", "updated_at"])
    return vehicle.verification_status


def recompute_driver_status(owner):
    profile = DriverProfile.objects.filter(user=owner).first()
    if not profile or profile.verification_status == DriverProfile.VerificationStatus.SUSPENDED:
        return profile.verification_status if profile else None

    driver_documents = {
        document_type: current_document(owner, document_type)
        for document_type in REQUIRED_DRIVER_DOCUMENTS
    }
    has_driver_documents = VerificationDocument.objects.filter(
        owner=owner,
        vehicle__isnull=True,
        is_current=True,
    ).exists()
    approved_vehicle = Vehicle.objects.filter(
        owner=owner,
        verification_status=Vehicle.VerificationStatus.APPROVED,
    ).exists()
    vehicle_needs_resubmission = Vehicle.objects.filter(
        owner=owner,
        verification_status=Vehicle.VerificationStatus.NEEDS_RESUBMISSION,
    ).exists()
    has_vehicle_documents = VerificationDocument.objects.filter(
        owner=owner,
        vehicle__isnull=False,
        is_current=True,
    ).exists()

    driver_document_rejected = any(
        document and (
            document.review_status == VerificationDocument.ReviewStatus.REJECTED
            or document.is_expired
        )
        for document in driver_documents.values()
    )
    driver_documents_approved = all(
        document
        and document.review_status == VerificationDocument.ReviewStatus.APPROVED
        and not document.is_expired
        for document in driver_documents.values()
    )

    if driver_document_rejected:
        next_status = DriverProfile.VerificationStatus.NEEDS_RESUBMISSION
    elif driver_documents_approved and approved_vehicle:
        # One fully approved vehicle is enough to verify the driver account.
        # Each additional vehicle keeps its own independent review status.
        next_status = DriverProfile.VerificationStatus.APPROVED
    elif vehicle_needs_resubmission and not approved_vehicle:
        next_status = DriverProfile.VerificationStatus.NEEDS_RESUBMISSION
    elif profile.submitted_at or has_driver_documents or has_vehicle_documents:
        next_status = DriverProfile.VerificationStatus.PENDING
    else:
        next_status = DriverProfile.VerificationStatus.DRAFT

    if profile.verification_status != next_status:
        profile.verification_status = next_status
        profile.save(update_fields=["verification_status", "updated_at"])
    return profile.verification_status


def refresh_verification_status(owner, vehicle=None):
    if vehicle:
        recompute_vehicle_status(vehicle)
    return recompute_driver_status(owner)


def submit_vehicle_for_review(owner, vehicle):
    """Legacy explicit submit endpoint; uploaded documents are already queued individually."""
    profile, _ = DriverProfile.objects.get_or_create(user=owner)

    missing = []
    driver_labels = {
        VerificationDocument.DocumentType.DRIVER_LICENSE: "Driving licence",
        VerificationDocument.DocumentType.DRIVER_PHOTO: "Driver face photo",
    }
    for document_type, label in driver_labels.items():
        document = current_document(owner, document_type)
        if not document:
            missing.append(label)
        elif document.is_expired:
            missing.append(f"A current {label.lower()}")
        elif document.review_status == VerificationDocument.ReviewStatus.REJECTED:
            missing.append(f"Resubmit the rejected {label.lower()}")

    vehicle_documents = {
        document_type: current_document(owner, document_type, vehicle)
        for document_type in REQUIRED_VEHICLE_DOCUMENTS
    }
    labels = {
        VerificationDocument.DocumentType.VEHICLE_REGISTRATION: "Vehicle registration certificate",
        VerificationDocument.DocumentType.INSURANCE: "Insurance certificate",
    }
    for document_type, document in vehicle_documents.items():
        if not document:
            missing.append(labels[document_type])
        elif document.is_expired:
            missing.append(f"Current {labels[document_type].lower()}")
        elif document.review_status == VerificationDocument.ReviewStatus.REJECTED:
            missing.append(f"Resubmit the rejected {labels[document_type].lower()}")

    if profile.submitted_at is None and VerificationDocument.objects.filter(
        owner=owner, is_current=True
    ).exists():
        profile.submitted_at = timezone.now()
        profile.save(update_fields=["submitted_at", "updated_at"])

    recompute_vehicle_status(vehicle)
    recompute_driver_status(owner)
    profile.refresh_from_db()
    vehicle.refresh_from_db()
    return profile, missing
