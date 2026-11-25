from django.urls import path

from .views import (
    AdminSafetyReportQueueView,
    AdminSafetyReportUpdateView,
    BookingMessageThreadView,
    EmergencyContactDetailView,
    EmergencyContactListCreateView,
    MyJourneyReviewsView,
    MySafetyReportsView,
    NotificationInboxView,
    NotificationReadAllView,
    NotificationReadView,
    SafetyReportCreateView,
    SubmitJourneyReviewView,
)

urlpatterns = [
    path("notifications/", NotificationInboxView.as_view(), name="notification-inbox"),
    path("notifications/read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("bookings/<int:booking_id>/messages/", BookingMessageThreadView.as_view(), name="booking-message-thread"),
    path("safety/contacts/", EmergencyContactListCreateView.as_view(), name="emergency-contact-list-create"),
    path("safety/contacts/<int:pk>/", EmergencyContactDetailView.as_view(), name="emergency-contact-detail"),
    path("safety/reports/", SafetyReportCreateView.as_view(), name="safety-report-create"),
    path("safety/reports/mine/", MySafetyReportsView.as_view(), name="my-safety-reports"),
    path("safety/admin/reports/", AdminSafetyReportQueueView.as_view(), name="admin-safety-report-queue"),
    path("safety/admin/reports/<int:pk>/", AdminSafetyReportUpdateView.as_view(), name="admin-safety-report-update"),
    path("reviews/mine/", MyJourneyReviewsView.as_view(), name="my-journey-reviews"),
    path("reviews/<int:booking_id>/", SubmitJourneyReviewView.as_view(), name="submit-journey-review"),
]
