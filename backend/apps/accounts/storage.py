"""Storage routing for passenger identity documents.

The backend is resolved from the passenger_private alias so provider credentials
remain in environment settings and never enter migration files.
"""
from django.core.files.storage import storages


def get_private_passenger_storage():
    """Return the configured private passenger document storage backend."""
    return storages["passenger_private"]
