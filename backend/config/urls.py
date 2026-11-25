from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/drivers/", include("apps.drivers.urls")),
    path("api/v1/journeys/", include("apps.journeys.urls")),
    path("api/v1/bookings/", include("apps.bookings.urls")),
    path("api/v1/finance/", include("apps.finance.urls")),
    path("api/v1/", include("apps.core.urls")),
]
