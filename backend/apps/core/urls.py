from django.urls import path

from .views import (
    AdminBookingListView,
    AdminExpenseLedgerView,
    AdminJourneyListView,
    AdminOverviewView,
    AdminUserListView,
    HealthCheckView,
)

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("admin/overview/", AdminOverviewView.as_view(), name="admin-overview"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/journeys/", AdminJourneyListView.as_view(), name="admin-journey-list"),
    path("admin/bookings/", AdminBookingListView.as_view(), name="admin-booking-list"),
    path("admin/expense-ledger/", AdminExpenseLedgerView.as_view(), name="admin-expense-ledger"),
]
