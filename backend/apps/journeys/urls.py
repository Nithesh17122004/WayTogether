from django.urls import path

from .views import (
    JourneyCancelView,
    JourneyDetailView,
    JourneyListCreateView,
    JourneyPublishView,
    JourneyUpdateView,
    LocationSearchView,
    MyJourneyListView,
    RoutePreviewView,
)

urlpatterns = [
    path("locations/search/", LocationSearchView.as_view(), name="journey-location-search"),
    path("route-preview/", RoutePreviewView.as_view(), name="journey-route-preview"),
    path("mine/", MyJourneyListView.as_view(), name="my-journeys"),
    path("", JourneyListCreateView.as_view(), name="journey-list-create"),
    path("<int:pk>/", JourneyDetailView.as_view(), name="journey-detail"),
    path("<int:pk>/edit/", JourneyUpdateView.as_view(), name="journey-update"),
    path("<int:pk>/publish/", JourneyPublishView.as_view(), name="journey-publish"),
    path("<int:pk>/cancel/", JourneyCancelView.as_view(), name="journey-cancel"),
]
