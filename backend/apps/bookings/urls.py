from django.urls import path

from .views import (
    BookingApproveView,
    BookingCancelView,
    BookingDeclineView,
    BookingDetailView,
    DriverBookingRequestListView,
    PassengerBookingCreateView,
    PassengerBookingListView,
)

urlpatterns = [
    path("", PassengerBookingCreateView.as_view(), name="booking-create"),
    path("mine/", PassengerBookingListView.as_view(), name="my-bookings"),
    path("driver/requests/", DriverBookingRequestListView.as_view(), name="driver-booking-requests"),
    path("<int:pk>/", BookingDetailView.as_view(), name="booking-detail"),
    path("<int:pk>/approve/", BookingApproveView.as_view(), name="booking-approve"),
    path("<int:pk>/decline/", BookingDeclineView.as_view(), name="booking-decline"),
    path("<int:pk>/cancel/", BookingCancelView.as_view(), name="booking-cancel"),
]
