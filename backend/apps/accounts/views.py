from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.drivers.permissions import IsPlatformAdmin

from .models import PassengerVerification, VerificationCode
from .serializers import (
    RegisterSerializer,
    UserPublicSerializer,
    WayTogetherTokenSerializer,
)
from .services import issue_verification_code, verify_code
from .passenger_verification_serializers import (
    AdminPassengerVerificationSerializer,
    PassengerVerificationReviewSerializer,
    PassengerVerificationStatusSerializer,
    PassengerVerificationUploadSerializer,
    safe_original_name,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        delivery = {"email": "not_sent"}
        errors = {}

        try:
            issue_verification_code(user, VerificationCode.Channel.EMAIL)
            delivery["email"] = "sent"
        except ValueError as exc:
            errors["email"] = str(exc)
        except Exception:
            errors["email"] = "Your account was created, but the email could not be sent. Use Resend code after email delivery is configured."

        return Response(
            {
                "detail": "Your account has been created. Verify your email address to sign in.",
                "user": UserPublicSerializer(user).data,
                "verification": delivery,
                "delivery_notes": errors,
            },
            status=status.HTTP_201_CREATED,
        )


class VerificationRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        channel = request.data.get("channel", VerificationCode.Channel.EMAIL)
        if not email or channel != VerificationCode.Channel.EMAIL:
            return Response(
                {"detail": "Provide a valid email address. Only email verification is supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        # Keep unknown and already-verified accounts indistinguishable.
        if not user:
            return Response({"detail": "If the account needs verification, a code will be sent."})

        if user.is_email_verified:
            return Response({"detail": "If the account needs verification, a code will be sent."})

        try:
            issue_verification_code(user, channel)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception:
            return Response(
                {"detail": "We could not send a verification code. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"detail": "If the account needs verification, a code will be sent."})


class VerificationConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        channel = request.data.get("channel", VerificationCode.Channel.EMAIL)
        code = str(request.data.get("code", "")).strip()
        if not email or channel != VerificationCode.Channel.EMAIL or len(code) != 6 or not code.isdigit():
            return Response(
                {"detail": "Provide an email address and six-digit email verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"detail": "The verification code is invalid or expired."}, status=status.HTTP_400_BAD_REQUEST)

        valid, message = verify_code(user, channel, code)
        if not valid:
            return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "detail": message,
                "user": UserPublicSerializer(user).data,
                "can_sign_in": user.is_email_verified,
            }
        )


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = WayTogetherTokenSerializer
    throttle_scope = "login"


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_scope = "login"


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserPublicSerializer(request.user).data)



class PassengerVerificationView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _ensure_passenger(self, request):
        if request.user.role != User.Role.PASSENGER:
            return Response({"detail": "Passenger identity verification is only available to passenger accounts."}, status=403)
        return None

    def get(self, request):
        denied = self._ensure_passenger(request)
        if denied:
            return denied
        verification = PassengerVerification.objects.filter(user=request.user).first()
        if not verification:
            return Response({"status": "not_submitted", "review_note": ""})
        return Response(PassengerVerificationStatusSerializer(verification).data)

    def post(self, request):
        denied = self._ensure_passenger(request)
        if denied:
            return denied
        serializer = PassengerVerificationUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        aadhaar_file = serializer.validated_data["masked_aadhaar_document"]
        photo_file = serializer.validated_data["passenger_photo"]
        now = timezone.now()

        with transaction.atomic():
            verification = (
                PassengerVerification.objects.select_for_update()
                .filter(user=request.user)
                .first()
            )
            is_new = verification is None
            if is_new:
                verification = PassengerVerification(user=request.user, consent_at=now)

            old_files = []
            if verification.pk:
                if verification.masked_aadhaar_document:
                    old_files.append((verification.masked_aadhaar_document.storage, verification.masked_aadhaar_document.name))
                if verification.passenger_photo:
                    old_files.append((verification.passenger_photo.storage, verification.passenger_photo.name))

            verification.masked_aadhaar_document = aadhaar_file
            verification.passenger_photo = photo_file
            verification.masked_aadhaar_file_name = safe_original_name(aadhaar_file)
            verification.passenger_photo_file_name = safe_original_name(photo_file)
            verification.consent_at = now
            verification.status = PassengerVerification.Status.PENDING
            verification.review_note = ""
            verification.reviewed_by = None
            verification.reviewed_at = None
            verification.save()

            new_paths = {
                verification.masked_aadhaar_document.name,
                verification.passenger_photo.name,
            }
            for storage, old_path in old_files:
                if old_path not in new_paths:
                    transaction.on_commit(lambda storage=storage, path=old_path: storage.delete(path))

        return Response(
            {
                "detail": "Your masked Aadhaar proof and passenger photo have been submitted for manual review.",
                "verification": PassengerVerificationStatusSerializer(verification).data,
            },
            status=status.HTTP_201_CREATED if is_new else status.HTTP_200_OK,
        )


class PassengerVerificationDocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, verification_id, document_type):
        verification = get_object_or_404(PassengerVerification, pk=verification_id)
        if verification.user_id != request.user.id and not request.user.is_staff:
            raise Http404

        if document_type == "aadhaar":
            stored_file = verification.masked_aadhaar_document
            filename = verification.masked_aadhaar_file_name
        elif document_type == "photo":
            stored_file = verification.passenger_photo
            filename = verification.passenger_photo_file_name
        else:
            raise Http404

        try:
            opened = stored_file.open("rb")
        except (FileNotFoundError, OSError, ValueError):
            raise Http404("The private verification file is not available.")

        response = FileResponse(opened, as_attachment=True, filename=filename, content_type="application/octet-stream")
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class AdminPassengerVerificationQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = AdminPassengerVerificationSerializer

    def get_queryset(self):
        return (
            PassengerVerification.objects.filter(status=PassengerVerification.Status.PENDING)
            .select_related("user")
            .order_by("submitted_at")
        )


class AdminPassengerVerificationReviewView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, verification_id):
        serializer = PassengerVerificationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            verification = get_object_or_404(
                PassengerVerification.objects.select_for_update().select_related("user"),
                pk=verification_id,
            )
            if verification.status != PassengerVerification.Status.PENDING:
                return Response({"detail": "This passenger submission has already been reviewed."}, status=409)

            decision = serializer.validated_data["decision"]
            verification.status = decision
            verification.review_note = serializer.validated_data.get("review_note", "").strip()
            verification.reviewed_by = request.user
            verification.reviewed_at = timezone.now()
            verification.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "submitted_at"])

        return Response({
            "detail": f"Passenger identity verification {decision}.",
            "verification_id": verification.pk,
            "status": verification.status,
        })
