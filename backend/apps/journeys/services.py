import logging
import os

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
OSRM_ROUTE_URL = os.getenv("OSRM_ROUTE_URL", "https://router.project-osrm.org/route/v1/driving")
MAPS_USER_AGENT = os.getenv(
    "MAPS_USER_AGENT",
    "WayTogether/1.0 (journey search; configure a monitored production provider)",
)


class MapsProviderError(Exception):
    pass


def search_locations(query):
    query = " ".join(query.split())[:160]
    key = "waytogether:geocode:" + query.casefold()
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 6, "countrycodes": "in"},
            headers={"User-Agent": MAPS_USER_AGENT},
            timeout=(3.05, 8),
        )
        response.raise_for_status()
        raw_results = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Geocoding provider unavailable: %s", exc)
        raise MapsProviderError("Location search is temporarily unavailable. Please try again.") from exc

    results = []
    for item in raw_results:
        address = item.get("address", {})
        locality = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("suburb")
            or item.get("name")
            or item.get("display_name", "").split(",")[0]
        )
        results.append({
            "display_name": item.get("display_name", ""),
            "name": locality,
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
            "state": address.get("state", ""),
            "postcode": address.get("postcode", ""),
        })
    cache.set(key, results, timeout=60 * 60 * 24)
    return results


def get_route_preview(origin_lat, origin_lon, destination_lat, destination_lon):
    coordinates = f"{origin_lon},{origin_lat};{destination_lon},{destination_lat}"
    try:
        response = requests.get(
            f"{OSRM_ROUTE_URL}/{coordinates}",
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            headers={"User-Agent": MAPS_USER_AGENT},
            timeout=(3.05, 12),
        )
        response.raise_for_status()
        payload = response.json()
        route = (payload.get("routes") or [None])[0]
        if not route:
            raise MapsProviderError("No route was found for these locations.")
        return {
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_minutes": round(route["duration"] / 60),
            "geometry": route.get("geometry", {}).get("coordinates", []),
        }
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        logger.warning("Route provider unavailable: %s", exc)
        raise MapsProviderError("Route preview is temporarily unavailable. Please try again.") from exc
