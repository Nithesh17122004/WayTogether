from django.urls import path

from .views import (
    AdminDocumentReviewView,
    AdminVerificationQueueView,
    DocumentDownloadView,
    DriverProfileView,
    SubmitVehicleVerificationView,
    VehicleDetailView,
    VehicleListCreateView,
    VerificationDocumentListCreateView,
)

urlpatterns = [
    path("profile/", DriverProfileView.as_view(), name="driver-profile"),
    path("vehicles/", VehicleListCreateView.as_view(), name="driver-vehicles"),
    path("vehicles/<int:pk>/", VehicleDetailView.as_view(), name="driver-vehicle-detail"),
    path("documents/", VerificationDocumentListCreateView.as_view(), name="driver-documents"),
    path("documents/<int:document_id>/download/", DocumentDownloadView.as_view(), name="driver-document-download"),
    path("verification/submit/", SubmitVehicleVerificationView.as_view(), name="driver-verification-submit"),
    path("admin/verification/queue/", AdminVerificationQueueView.as_view(), name="admin-verification-queue"),
    path("admin/verification/documents/<int:document_id>/review/", AdminDocumentReviewView.as_view(), name="admin-document-review"),
]
