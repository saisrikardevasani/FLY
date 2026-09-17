"""Redis, pinged once at startup so a missing cache is noticed now rather than in week 5.

Nothing caches anything yet. A PING is two bytes of the Redis wire protocol, so this asks the
socket directly instead of adding a client library for one round trip; the real client arrives
with the first thing that actually stores a value.
"""

import logging
import os
import socket
from urllib.parse import urlparse

log = logging.getLogger("uvicorn.error")


def ping(url: str | None = None, timeout: float = 2.0) -> str:
    """Send PING and return Redis's reply, normally "+PONG"."""
    parts = urlparse(url or os.environ.get("REDIS_URL", "redis://localhost:6379"))
    with socket.create_connection((parts.hostname, parts.port or 6379), timeout) as sock:
        sock.sendall(b"PING\r\n")
        return sock.recv(64).decode(errors="replace").strip()


def ping_at_startup() -> str | None:
    """Log the reply and carry on. Redis is not on the request path, so it cannot stop the app."""
    try:
        reply = ping()
    except OSError as exc:
        log.warning("redis: no answer (%s)", exc)
        return None
    log.info("redis: %s", reply)
    return reply
