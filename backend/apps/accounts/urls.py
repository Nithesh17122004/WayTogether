from django.urls import path

from .views import (
    CurrentUserView,
    LoginView,
    RefreshView,
    RegisterView,
    VerificationConfirmView,
    VerificationRequestView,
    PassengerVerificationView,
    PassengerVerificationDocumentDownloadView,
    AdminPassengerVerificationQueueView,
    AdminPassengerVerificationReviewView,
)
from rest_framework_simplejwt.views import TokenBlacklistView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token-blacklist"),
    path("verification/request/", VerificationRequestView.as_view(), name="verification-request"),
    path("verification/confirm/", VerificationConfirmView.as_view(), name="verification-confirm"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("passenger-verification/", PassengerVerificationView.as_view(), name="passenger-verification"),
    path("passenger-verification/<int:verification_id>/download/<str:document_type>/", PassengerVerificationDocumentDownloadView.as_view(), name="passenger-verification-download"),
    path("admin/passenger-verification/queue/", AdminPassengerVerificationQueueView.as_view(), name="admin-passenger-verification-queue"),
    path("admin/passenger-verification/<int:verification_id>/review/", AdminPassengerVerificationReviewView.as_view(), name="admin-passenger-verification-review"),
]
