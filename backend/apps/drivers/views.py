import mimetypes

from django.conf import settings

from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DriverProfile, Vehicle, VerificationDocument
from .permissions import IsDriverAccount, IsPlatformAdmin
from .serializers import (
    AdminVerificationDocumentSerializer,
    DocumentReviewSerializer,
    DriverProfileSerializer,
    VehicleSerializer,
    VerificationDocumentSerializer,
)
from .services import recompute_driver_status, recompute_vehicle_status, submit_vehicle_for_review


class DriverProfileView(APIView):
    permission_classes = [IsAuthenticated, IsDriverAccount]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_profile(self, request):
        profile, _ = DriverProfile.objects.get_or_create(user=request.user)
        return profile

    def get(self, request):
        return Response(DriverProfileSerializer(self.get_profile(request), context={"request": request}).data)

    def post(self, request):
        if "profile_photo" in request.data and not settings.PRIVATE_MEDIA_STORAGE_READY:
            return Response(
                {"detail": "Driver photo upload is disabled until private persistent file storage is configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        profile = self.get_profile(request)
        serializer = DriverProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DriverProfileSerializer(profile, context={"request": request}).data)

    def patch(self, request):
        if "profile_photo" in request.data and not settings.PRIVATE_MEDIA_STORAGE_READY:
            return Response(
                {"detail": "Driver photo upload is disabled until private persistent file storage is configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        profile = self.get_profile(request)
        serializer = DriverProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DriverProfileSerializer(profile, context={"request": request}).data)


class VehicleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsDriverAccount]
    serializer_class = VehicleSerializer

    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        DriverProfile.objects.get_or_create(user=self.request.user)
        serializer.save()


class VehicleDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsDriverAccount]
    serializer_class = VehicleSerializer

    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user)


class VerificationDocumentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsDriverAccount]
    serializer_class = VerificationDocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        if not settings.PRIVATE_MEDIA_STORAGE_READY:
            return Response(
                {"detail": "Driver document uploads are disabled until private persistent file storage is configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        return (
            VerificationDocument.objects
            .filter(owner=self.request.user)
            .select_related("vehicle", "reviewed_by")
            .order_by("-uploaded_at")
        )

    def perform_create(self, serializer):
        DriverProfile.objects.get_or_create(user=self.request.user)
        serializer.save()


class SubmitVehicleVerificationView(APIView):
    permission_classes = [IsAuthenticated, IsDriverAccount]

    def post(self, request):
        vehicle_id = request.data.get("vehicle_id")
        if not vehicle_id:
            return Response({"detail": "vehicle_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        vehicle = get_object_or_404(Vehicle, pk=vehicle_id, owner=request.user)
        profile, missing = submit_vehicle_for_review(request.user, vehicle)
        if missing:
            return Response(
                {
                    "detail": "Upload the required documents before submitting for review.",
                    "missing_documents": missing,
                    "driver_status": profile.verification_status,
                    "vehicle_status": vehicle.verification_status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "detail": "Your driver and vehicle documents have been submitted for review.",
                "driver_status": profile.verification_status,
                "vehicle_status": vehicle.verification_status,
            },
            status=status.HTTP_200_OK,
        )


class DocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        document = get_object_or_404(VerificationDocument, pk=document_id)
        if document.owner_id != request.user.id and not request.user.is_staff:
            # Do not reveal whether another user's private document exists.
            raise Http404

        try:
            stored_file = document.file.open("rb")
        except (FileNotFoundError, OSError, ValueError):
            raise Http404("The document file is not available.")

        response = FileResponse(
            stored_file,
            as_attachment=True,
            filename=document.original_file_name,
            content_type="application/octet-stream",
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Pragma"] = "no-cache"
        return response


class AdminVerificationQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = AdminVerificationDocumentSerializer

    def get_queryset(self):
        return (
            VerificationDocument.objects
            .filter(is_current=True, review_status=VerificationDocument.ReviewStatus.PENDING)
            .select_related("owner", "vehicle")
            .order_by("uploaded_at")
        )


class AdminDocumentReviewView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, document_id):
        serializer = DocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            document = get_object_or_404(
                VerificationDocument.objects.select_for_update().select_related("owner", "vehicle"),
                pk=document_id,
                is_current=True,
            )
            if document.review_status != VerificationDocument.ReviewStatus.PENDING:
                return Response(
                    {"detail": "This document has already been reviewed or is no longer current."},
                    status=status.HTTP_409_CONFLICT,
                )

            decision = serializer.validated_data["decision"]
            document.review_status = decision
            document.review_note = serializer.validated_data.get("review_note", "").strip()
            document.reviewed_by = request.user
            from django.utils import timezone
            document.reviewed_at = timezone.now()
            document.save(
                update_fields=["review_status", "review_note", "reviewed_by", "reviewed_at"]
            )

            if document.vehicle_id:
                recompute_vehicle_status(document.vehicle)
            driver_status = recompute_driver_status(document.owner)

        return Response(
            {
                "detail": f"Document {decision}.",
                "document_id": document.pk,
                "document_status": document.review_status,
                "vehicle_status": document.vehicle.verification_status if document.vehicle_id else None,
                "driver_status": driver_status,
            }
        )



class PublicDriverPhotoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, driver_id):
        profile = get_object_or_404(
            DriverProfile.objects.select_related("user"),
            user_id=driver_id,
            verification_status=DriverProfile.VerificationStatus.APPROVED,
            user__is_active=True,
            user__is_email_verified=True,
        )
        photo = VerificationDocument.objects.filter(
            owner_id=driver_id,
            document_type=VerificationDocument.DocumentType.DRIVER_PHOTO,
            review_status=VerificationDocument.ReviewStatus.APPROVED,
            is_current=True,
        ).first()
        if not photo or not photo.file:
            raise Http404

        # Only serve a verified driver's face photo while they have a published journey.
        from apps.journeys.models import Journey
        if not Journey.objects.filter(
            driver_id=driver_id,
            status=Journey.Status.PUBLISHED,
            travel_date__gte=timezone.localdate(),
        ).exists():
            raise Http404

        try:
            opened = photo.file.open("rb")
        except (FileNotFoundError, OSError, ValueError):
            raise Http404("The driver photo is unavailable.")

        content_type = mimetypes.guess_type(photo.file.name)[0] or "application/octet-stream"
        response = FileResponse(opened, as_attachment=False, content_type=content_type)
        response["Cache-Control"] = "public, max-age=300"
        response["X-Content-Type-Options"] = "nosniff"
        return response
