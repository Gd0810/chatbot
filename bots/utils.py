# bot/utils.py

from urllib.parse import urlparse

LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1"
}

def _is_local_origin(origin: str) -> bool:
    """
    Validates whether the request origin belongs to local development environments.
    Example origins:
    - http://localhost
    - http://127.0.0.1:5500
    - http://localhost:8000
    """

    if not origin:
        return False

    try:
        parsed = urlparse(origin)
        hostname = parsed.hostname

        return hostname in LOCAL_HOSTS if hostname else False

    except Exception:
        return False
