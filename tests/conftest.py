from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

PASSWORD = "test-password"


@pytest.fixture
def app(tmp_path):
    return create_app(database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
                      admin_password=PASSWORD, secret_key="test-secret")


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def admin(app):
    c = TestClient(app)
    r = c.post("/admin/login", data={"password": PASSWORD}, follow_redirects=False)
    assert r.status_code == 303
    return c


def next_open_day(weekday_key: str = "sat") -> date:
    """The next given weekday at least 2 days away (so 'today' time cut-offs never interfere)."""
    keys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    d = datetime.now(ZoneInfo("Europe/London")).date() + timedelta(days=2)
    while keys[d.weekday()] != weekday_key:
        d += timedelta(days=1)
    return d


def booking_data(**over) -> dict:
    data = {"kind": "table", "day": next_open_day().isoformat(), "at": "19:00", "party_size": "4",
            "name": "Ada Lovelace", "phone": "07700 900123", "email": "ada@example.com",
            "notes": "Window seat please", "consent": "1"}
    data.update(over)
    return data
