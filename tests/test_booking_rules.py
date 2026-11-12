from datetime import date, datetime

import pytest

from app import booking as bk
from app.db import DEFAULT_HOURS
from app.i18n import STRINGS, translator

HOURS = {k: [list(p) for p in v] for k, v in DEFAULT_HOURS.items()}
T = translator("en")


def test_slots_run_every_15_minutes_until_an_hour_before_closing():
    tuesday = date(2026, 11, 17)
    slots = bk.slots_for(tuesday, HOURS)
    assert slots[:3] == ["12:00", "12:15", "12:30"]
    assert "13:30" in slots and "13:45" not in slots      # lunch closes 14:30
    assert "17:30" in slots and slots[-1] == "21:00"      # dinner closes 22:00


def test_closed_day_has_no_slots():
    assert bk.slots_for(date(2026, 11, 16), HOURS) == []   # Monday


def test_today_leaves_out_times_with_less_than_30_minutes_notice():
    tuesday = date(2026, 11, 17)
    slots = bk.slots_for(tuesday, HOURS, now=datetime(2026, 11, 17, 18, 50))
    assert slots[0] == "19:30"


def test_all_slots_is_keyed_by_weekday():
    s = bk.all_slots(HOURS)
    assert s["mon"] == [] and s["sat"][0] == "12:00"


def test_hours_text_round_trip():
    text = bk.hours_to_text(HOURS)
    assert text["mon"] == "" and text["tue"] == "12:00-14:30, 17:30-22:00"
    assert bk.text_to_hours(text) == HOURS


@pytest.mark.parametrize("bad", ["noon-3", "14:00-12:00", "25:00-26:00", "12:00"])
def test_bad_hours_text_is_rejected(bad):
    with pytest.raises(ValueError):
        bk.text_to_hours({"tue": bad})


def test_closed_word_and_spaces_are_accepted():
    hours = bk.text_to_hours({"mon": " Closed ", "tue": "9:00 - 11:30,18:00–21:00"})
    assert hours["mon"] == [] and hours["tue"] == [["09:00", "11:30"], ["18:00", "21:00"]]


def test_parse_hours_survives_garbage():
    assert bk.parse_hours("not json")["tue"] == []


def _form(**over):
    from tests.conftest import booking_data
    data = booking_data(**over)
    data["consent"] = bool(data.pop("consent"))
    return bk.BookingForm(**data)


def test_valid_form_is_cleaned():
    f = _form(name="  Ada   Lovelace ")
    clean = f.validate(HOURS, "Europe/London", 60, T)
    assert f.errors == [] and clean["name"] == "Ada Lovelace" and clean["party_size"] == 4


@pytest.mark.parametrize("field,value,error", [
    ("name", "A", "err_name"), ("phone", "call me", "err_phone"), ("email", "nope@", "err_email"),
    ("day", "2001-01-01", "err_date"), ("at", "03:00", "err_time"), ("party_size", "99", "err_party"),
    ("consent", "", "err_consent"), ("kind", "party-bus", "err_kind"),
])
def test_each_rule_reports_its_error(field, value, error):
    f = _form(**{field: value})
    assert f.validate(HOURS, "Europe/London", 60, T) is None
    expected_start = STRINGS["en"][error].split("{")[0]   # text before any {placeholder}
    assert any(e.startswith(expected_start) for e in f.errors), f.errors


def test_closed_day_is_rejected():
    from tests.conftest import next_open_day
    f = _form(day=next_open_day("mon").isoformat())
    assert f.validate(HOURS, "Europe/London", 60, T) is None and T("err_time") in f.errors


def test_private_events_need_at_least_8_guests():
    assert _form(kind="private", party_size="4").validate(HOURS, "Europe/London", 60, T) is None
    assert _form(kind="private", party_size="20").validate(HOURS, "Europe/London", 60, T) is not None


def test_both_languages_have_the_same_keys_and_placeholders():
    import re
    for key, en in STRINGS["en"].items():
        assert set(re.findall(r"{(\w+)}", en)) == set(re.findall(r"{(\w+)}", STRINGS["zh"][key])), key
