"""Opening hours -> bookable time slots, and booking form validation."""
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .db import DAYS

SLOT_MINUTES = 15
LAST_SEATING_BEFORE_CLOSE = 60   # no new tables in the last hour before closing
PARTY_LIMITS = {"table": (1, 10), "private": (8, 60)}
PHONE_RE = re.compile(r"^\+?[0-9][0-9 ()-]{5,18}[0-9]$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def parse_hours(raw: str) -> dict[str, list[list[str]]]:
    """Stored as JSON: {"mon": [], "tue": [["12:00", "14:30"], ["17:30", "22:00"]], ...}."""
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        data = {}
    return {d: [list(p) for p in data.get(d, []) if len(p) == 2] for d in DAYS}


def hours_to_text(hours: dict) -> dict[str, str]:
    """For the admin form: {"tue": "12:00-14:30, 17:30-22:00", "mon": ""}."""
    return {d: ", ".join(f"{a}-{b}" for a, b in hours.get(d, [])) for d in DAYS}


def text_to_hours(texts: dict[str, str]) -> dict[str, list[list[str]]]:
    """Parse the admin form back. Empty or "closed" means closed. Raises ValueError on bad input."""
    out = {}
    for d in DAYS:
        raw = (texts.get(d) or "").strip().lower()
        periods = []
        if raw and raw not in ("closed", "休息"):
            for part in raw.split(","):
                m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})\s*", part)
                if not m:
                    raise ValueError(f"{d}: write times like 12:00-14:30, 17:30-22:00")
                h1, m1, h2, m2 = map(int, m.groups())
                if not (0 <= h1 < 24 and 0 <= h2 < 24 and m1 < 60 and m2 < 60) or (h2, m2) <= (h1, m1):
                    raise ValueError(f"{d}: {part.strip()} isn't a valid opening period")
                periods.append([f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}"])
        out[d] = sorted(periods)
    return out


def slots_for(day: date, hours: dict, now: datetime | None = None) -> list[str]:
    """Bookable start times on `day`, every 15 minutes from opening until an hour before closing.
    On today's date, times that have already passed (plus 30 minutes' notice) are left out."""
    out = []
    for start, end in hours.get(DAYS[day.weekday()], []):
        t = datetime.combine(day, time.fromisoformat(start))
        last = datetime.combine(day, time.fromisoformat(end)) - timedelta(minutes=LAST_SEATING_BEFORE_CLOSE)
        while t <= last:
            if now is None or t >= now.replace(tzinfo=None) + timedelta(minutes=30):
                out.append(t.strftime("%H:%M"))
            t += timedelta(minutes=SLOT_MINUTES)
    return out


def all_slots(hours: dict) -> dict[str, list[str]]:
    """Weekday -> slots, for the booking page's time picker (same rule as `slots_for`)."""
    monday = date(2024, 1, 1)  # any Monday
    return {d: slots_for(monday + timedelta(days=i), hours) for i, d in enumerate(DAYS)}


@dataclass
class BookingForm:
    kind: str = "table"
    day: str = ""
    at: str = ""
    party_size: str = "2"
    name: str = ""
    phone: str = ""
    email: str = ""
    notes: str = ""
    consent: bool = False
    errors: list[str] = field(default_factory=list)

    def validate(self, hours: dict, tz: str, days_ahead: int, t) -> dict | None:
        """Return clean values, or None with `self.errors` filled (messages via translator `t`)."""
        self.errors = []
        now = datetime.now(ZoneInfo(tz))
        if self.kind not in PARTY_LIMITS:
            self.errors.append(t("err_kind"))
        name = " ".join(self.name.split())[:80]
        if len(name) < 2:
            self.errors.append(t("err_name"))
        phone = self.phone.strip()
        if not PHONE_RE.match(phone):
            self.errors.append(t("err_phone"))
        email = self.email.strip()
        if email and (len(email) > 120 or not EMAIL_RE.match(email)):
            self.errors.append(t("err_email"))
        try:
            d = date.fromisoformat(self.day)
            if not (now.date() <= d <= now.date() + timedelta(days=days_ahead)):
                raise ValueError
        except ValueError:
            d = None
            self.errors.append(t("err_date", days=days_ahead))
        if d and self.at not in slots_for(d, hours, now if d == now.date() else None):
            self.errors.append(t("err_time"))
        lo, hi = PARTY_LIMITS.get(self.kind, PARTY_LIMITS["table"])
        try:
            party = int(self.party_size)
            if not lo <= party <= hi:
                raise ValueError
        except ValueError:
            party = None
            self.errors.append(t("err_party", lo=lo, hi=hi))
        if not self.consent:
            self.errors.append(t("err_consent"))
        if self.errors:
            return None
        return {"kind": self.kind, "name": name, "phone": phone, "email": email, "day": d,
                "at": time.fromisoformat(self.at), "party_size": party, "notes": self.notes.strip()[:1000]}
