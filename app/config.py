"""Settings, read once from the environment (and a local .env file if present)."""
import logging
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("uvicorn.error.restaurant")


def _load_dotenv(path: Path) -> None:
    """Tiny .env reader (KEY=value lines), so we don't need python-dotenv."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


def _clean_db_url(value: str) -> str:
    """Accept common copy-paste slips (the whole `DATABASE_URL=...` line, quotes) and the old
    `postgres://` scheme some hosts hand out, which SQLAlchemy no longer accepts."""
    value = value.strip().strip('"').strip("'")
    if value.upper().startswith("DATABASE_URL="):
        value = value.split("=", 1)[1].strip().strip('"').strip("'")
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]
    return value


# Local development uses a SQLite file; on Render set DATABASE_URL to a Postgres database
# (Render's disk is wiped on every deploy, so SQLite there would lose bookings).
DATA_DIR = Path(os.getenv("RESTAURANT_DATA_DIR", ROOT / "data"))
DATABASE_URL = _clean_db_url(os.getenv("DATABASE_URL", "")) or f"sqlite:///{(DATA_DIR / 'restaurant.db').as_posix()}"

# The admin page is off until a password is set.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Signs the admin login cookie. If unset, a random key is used, which logs admins out on every restart.
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    log.warning("SECRET_KEY not set: using a temporary one (admin logins won't survive a restart)")

TIMEZONE = os.getenv("RESTAURANT_TIMEZONE", "Europe/London")

# How far ahead people may book, in days.
BOOKING_DAYS_AHEAD = int(os.getenv("BOOKING_DAYS_AHEAD", "60"))
