from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import VerificationCode
from .serializers import (
    RegisterSerializer,
    UserPublicSerializer,
    WayTogetherTokenSerializer,
)
from .services import (
    OTPDeliveryUnavailable,
    issue_verification_code,
    verify_code,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        delivery = {"email": "pending", "phone": "pending"}
        errors = {}

        for channel in (VerificationCode.Channel.EMAIL, VerificationCode.Channel.PHONE):
            try:
                issue_verification_code(user, channel)
                delivery[channel] = "sent"
            except (OTPDeliveryUnavailable, ValueError) as exc:
                delivery[channel] = "not_configured" if isinstance(exc, OTPDeliveryUnavailable) else "not_sent"
                errors[channel] = str(exc)
            except Exception:
                delivery[channel] = "not_sent"
                errors[channel] = "We could not send this verification code. Please try again."

        return Response(
            {
                "detail": "Your account has been created. Verify your email and mobile number to sign in.",
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
        channel = request.data.get("channel")
        if not email or channel not in VerificationCode.Channel.values:
            return Response(
                {"detail": "Provide a valid email address and channel (email or phone)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        # Keep unknown and already-verified accounts indistinguishable.
        if not user:
            return Response({"detail": "If the account needs verification, a code will be sent."})

        verified = user.is_email_verified if channel == "email" else user.is_phone_verified
        if verified:
            return Response({"detail": "If the account needs verification, a code will be sent."})

        try:
            issue_verification_code(user, channel)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except OTPDeliveryUnavailable as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
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
        channel = request.data.get("channel")
        code = str(request.data.get("code", "")).strip()
        if not email or channel not in VerificationCode.Channel.values or len(code) != 6 or not code.isdigit():
            return Response(
                {"detail": "Provide an email, channel and six-digit verification code."},
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
                "can_sign_in": user.is_email_verified and user.is_phone_verified,
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
