import logging
import os

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
PHOTON_URL = os.getenv("PHOTON_URL", "https://photon.komoot.io/api/")
OSRM_ROUTE_URL = os.getenv("OSRM_ROUTE_URL", "")
MAPS_USER_AGENT = os.getenv(
    "MAPS_USER_AGENT",
    "WayTogether/1.0 (https://waytogether.aclclouds.online)",
)
INDIA_BBOX = "68.1,6.5,97.4,35.5"


class MapsProviderError(Exception):
    pass


class MapsRateLimitError(MapsProviderError):
    pass


def _format_nominatim_results(items):
    results = []
    for item in items:
        address = item.get("address") or {}
        display_name = item.get("display_name", "")
        locality = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("suburb")
            or item.get("name")
            or display_name.split(",")[0]
        )
        try:
            latitude = float(item["lat"])
            longitude = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        results.append({
            "display_name": display_name,
            "name": locality,
            "latitude": latitude,
            "longitude": longitude,
            "state": address.get("state", ""),
            "postcode": address.get("postcode", ""),
        })
    return results


def _format_photon_results(payload):
    results = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        country = str(properties.get("country") or "").casefold()
        if country not in {"india", "भारत", "in"}:
            continue
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) < 2:
            continue
        name = (
            properties.get("name")
            or properties.get("city")
            or properties.get("district")
            or properties.get("county")
            or "Selected location"
        )
        display_parts = [
            properties.get("name"),
            properties.get("street"),
            properties.get("city") or properties.get("district") or properties.get("county"),
            properties.get("state"),
            properties.get("country"),
        ]
        display_name = ", ".join(dict.fromkeys(
            str(part).strip() for part in display_parts if part and str(part).strip()
        ))
        results.append({
            "display_name": display_name or str(name),
            "name": str(name),
            "latitude": float(coordinates[1]),
            "longitude": float(coordinates[0]),
            "state": properties.get("state", ""),
            "postcode": properties.get("postcode", ""),
        })
    return results


def search_locations(query):
    query = " ".join(query.split())[:160]
    key = "waytogether:geocode:" + query.casefold()
    cached = cache.get(key)
    if cached is not None:
        return cached

    # Public Nominatim is limited to one request per second for the whole app.
    # Cache completed searches and use Photon only when Nominatim is unavailable
    # or returns no usable Indian matches.
    if not cache.add("waytogether:nominatim:global-rate-limit", True, timeout=1):
        raise MapsRateLimitError("Please wait a moment before searching for another location.")

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 6,
                "countrycodes": "in",
            },
            headers={
                "User-Agent": MAPS_USER_AGENT,
                "Accept": "application/json",
            },
            timeout=(3.05, 8),
        )
        response.raise_for_status()
        raw_results = response.json()
        if not isinstance(raw_results, list):
            raise ValueError("Geocoding provider returned an unexpected response.")
        results = _format_nominatim_results(raw_results)
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("Primary geocoding provider unavailable; trying fallback: %s", exc)
        results = []

    if not results:
        try:
            response = requests.get(
                PHOTON_URL,
                params={
                    "q": query,
                    "limit": 8,
                    "lang": "en",
                    "bbox": INDIA_BBOX,
                },
                headers={
                    "User-Agent": MAPS_USER_AGENT,
                    "Accept": "application/geo+json, application/json",
                },
                timeout=(3.05, 8),
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Fallback geocoding provider returned an unexpected response.")
            results = _format_photon_results(payload)
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            logger.warning("Fallback geocoding provider unavailable: %s", exc)
            raise MapsProviderError(
                "Location search is temporarily unavailable. Please try again in a moment."
            ) from exc

    cache.set(key, results, timeout=60 * 60 * 24)
    return results


def get_route_preview(origin_lat, origin_lon, destination_lat, destination_lon):
    if not OSRM_ROUTE_URL:
        raise MapsProviderError("Road route preview is not configured on the server.")
    coordinates = f"{origin_lon},{origin_lat};{destination_lon},{destination_lat}"
    try:
        response = requests.get(
            f"{OSRM_ROUTE_URL.rstrip('/')}/{coordinates}",
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            headers={
                "User-Agent": MAPS_USER_AGENT,
                "Accept": "application/json",
            },
            timeout=(3.05, 12),
        )
        response.raise_for_status()
        payload = response.json()
        route = (payload.get("routes") or [None])[0]
        if not route:
            raise MapsProviderError("No road route was found for these locations.")
        geometry = (route.get("geometry") or {}).get("coordinates") or []
        if len(geometry) < 2:
            raise MapsProviderError("The routing provider returned an incomplete route.")
        return {
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_minutes": round(route["duration"] / 60),
            "geometry": geometry,
        }
    except MapsProviderError:
        raise
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
        logger.warning("Route provider unavailable: %s", exc)
        raise MapsProviderError("Route preview is temporarily unavailable. Please try again.") from exc
