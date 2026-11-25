from django.urls import path

from .views import (
    CurrentUserView,
    LoginView,
    RefreshView,
    RegisterView,
    VerificationConfirmView,
    VerificationRequestView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("verification/request/", VerificationRequestView.as_view(), name="verification-request"),
    path("verification/confirm/", VerificationConfirmView.as_view(), name="verification-confirm"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
]
