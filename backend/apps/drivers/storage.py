"""Private storage resolver for driver verification documents and photos."""
from django.core.files.storage import storages


def get_private_driver_storage():
    """Return the dedicated private driver file storage backend."""
    return storages["driver_private"]
