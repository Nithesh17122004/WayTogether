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
from .services import issue_verification_code, verify_code

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
