"""Admin login cookie (HMAC-signed, no extra libraries) and a simple per-IP rate limiter."""
import hashlib
import hmac
import time
from collections import defaultdict, deque

COOKIE = "kin_admin"
SESSION_SECONDS = 12 * 3600


def _sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_session(secret: str, now: float | None = None) -> str:
    expires = str(int((now or time.time()) + SESSION_SECONDS))
    return f"{expires}.{_sign(secret, expires)}"


def valid_session(secret: str, value: str | None, now: float | None = None) -> bool:
    if not value or "." not in value:
        return False
    expires, sig = value.split(".", 1)
    if not hmac.compare_digest(sig, _sign(secret, expires)):
        return False
    return expires.isdigit() and int(expires) > (now or time.time())


def password_ok(given: str, expected: str) -> bool:
    """Constant-time comparison, so response timing doesn't leak how much of the password was right."""
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


class RateLimiter:
    """At most `limit` events per `window` seconds per key (e.g. client IP)."""

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self.events: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now, q = time.time(), self.events[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
