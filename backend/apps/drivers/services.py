from django.utils import timezone

from .models import DriverProfile, Vehicle, VerificationDocument


REQUIRED_DRIVER_DOCUMENTS = (
    VerificationDocument.DocumentType.DRIVER_LICENSE,
    VerificationDocument.DocumentType.DRIVER_PHOTO,
)

REQUIRED_VEHICLE_DOCUMENTS = (
    VerificationDocument.DocumentType.VEHICLE_REGISTRATION,
    VerificationDocument.DocumentType.INSURANCE,
    VerificationDocument.DocumentType.VEHICLE_PHOTO,
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
    if vehicle.verification_status in (
        Vehicle.VerificationStatus.DRAFT,
        Vehicle.VerificationStatus.SUSPENDED,
    ):
        return vehicle.verification_status

    documents = {
        document_type: current_document(vehicle.owner, document_type, vehicle)
        for document_type in REQUIRED_VEHICLE_DOCUMENTS
    }

    if any(
        document and (
            document.review_status == VerificationDocument.ReviewStatus.REJECTED
            or document.is_expired
        )
        for document in documents.values()
    ):
        vehicle.verification_status = Vehicle.VerificationStatus.NEEDS_RESUBMISSION
    elif all(
        document and document.review_status == VerificationDocument.ReviewStatus.APPROVED
        and not document.is_expired
        for document in documents.values()
    ):
        vehicle.verification_status = Vehicle.VerificationStatus.APPROVED
    else:
        vehicle.verification_status = Vehicle.VerificationStatus.PENDING

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
    approved_vehicle = Vehicle.objects.filter(
        owner=owner,
        verification_status=Vehicle.VerificationStatus.APPROVED,
    ).exists()

    if any(
        document and (
            document.review_status == VerificationDocument.ReviewStatus.REJECTED
            or document.is_expired
        )
        for document in driver_documents.values()
    ):
        profile.verification_status = DriverProfile.VerificationStatus.NEEDS_RESUBMISSION
    elif (
        all(
            document
            and document.review_status == VerificationDocument.ReviewStatus.APPROVED
            and not document.is_expired
            for document in driver_documents.values()
        )
        and approved_vehicle
    ):
        profile.verification_status = DriverProfile.VerificationStatus.APPROVED
    else:
        vehicle_needs_resubmission = Vehicle.objects.filter(
            owner=owner,
            verification_status=Vehicle.VerificationStatus.NEEDS_RESUBMISSION,
        ).exists()
        if vehicle_needs_resubmission:
            profile.verification_status = DriverProfile.VerificationStatus.NEEDS_RESUBMISSION
        elif profile.submitted_at:
            profile.verification_status = DriverProfile.VerificationStatus.PENDING
        else:
            profile.verification_status = DriverProfile.VerificationStatus.DRAFT

    profile.save(update_fields=["verification_status", "updated_at"])
    return profile.verification_status


def refresh_verification_status(owner, vehicle=None):
    if vehicle:
        recompute_vehicle_status(vehicle)
    return recompute_driver_status(owner)


def submit_vehicle_for_review(owner, vehicle):
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
            missing.append(f"Resubmit the rejected {label.toLowerCase()}")

    vehicle_documents = {
        document_type: current_document(owner, document_type, vehicle)
        for document_type in REQUIRED_VEHICLE_DOCUMENTS
    }
    labels = {
        VerificationDocument.DocumentType.VEHICLE_REGISTRATION: "Vehicle registration certificate",
        VerificationDocument.DocumentType.INSURANCE: "Insurance certificate",
        VerificationDocument.DocumentType.VEHICLE_PHOTO: "Vehicle photograph",
    }
    for document_type, document in vehicle_documents.items():
        if not document:
            missing.append(labels[document_type])
        elif document.is_expired:
            missing.append(f"Current {labels[document_type].lower()}")
        elif document.review_status == VerificationDocument.ReviewStatus.REJECTED:
            missing.append(f"Resubmit the rejected {labels[document_type].lower()}")

    if missing:
        return profile, missing

    now = timezone.now()
    profile.verification_status = DriverProfile.VerificationStatus.PENDING
    profile.submitted_at = now
    profile.save(update_fields=["verification_status", "submitted_at", "updated_at"])

    vehicle.verification_status = Vehicle.VerificationStatus.PENDING
    vehicle.save(update_fields=["verification_status", "updated_at"])

    # Documents may already have been reviewed while the driver was preparing
    # the submission. Recalculate immediately so an already-complete file set
    # does not remain stuck in Pending Review.
    recompute_vehicle_status(vehicle)
    recompute_driver_status(owner)
    profile.refresh_from_db()
    return profile, []
