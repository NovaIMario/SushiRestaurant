import re

from app.db import Booking
from tests.conftest import booking_data, next_open_day


def test_root_redirects_by_cookie_then_browser_language(client):
    assert client.get("/", follow_redirects=False).headers["location"] == "/en"
    r = client.get("/", headers={"accept-language": "zh-CN,zh;q=0.9"}, follow_redirects=False)
    assert r.headers["location"] == "/zh"
    client.get("/zh")                       # visiting a language remembers it
    assert client.get("/", follow_redirects=False).headers["location"] == "/zh"


def test_home_in_both_languages(client):
    en, zh = client.get("/en"), client.get("/zh")
    assert en.status_code == zh.status_code == 200
    assert "Book a table" in en.text and 'lang="en-GB"' in en.text
    assert "预订座位" in zh.text and 'lang="zh-Hans"' in zh.text
    assert 'href="/zh"' in en.text and 'href="/en"' in zh.text   # the toggle keeps you on the same page


def test_language_toggle_points_at_the_same_page(client):
    assert 'href="/zh/menu"' in client.get("/en/menu").text
    assert 'href="/en/book"' in client.get("/zh/book").text


def test_menu_shows_dishes_prices_and_allergen_warning(client):
    en = client.get("/en/menu").text
    assert "Tonkotsu ramen" in en and "£14.50" in en and "please ask our staff" in en
    assert "Ask staff about allergens" in en          # no allergen data invented for placeholders
    assert "豚骨拉面" in client.get("/zh/menu").text


def test_unknown_pages_are_a_friendly_404(client):
    for url in ("/fr", "/en/nope", "/zh/nope/deeper"):
        r = client.get(url)
        assert r.status_code == 404, url
    assert "找不到这个页面" in client.get("/zh/nope").text


def test_health(client):
    assert client.get("/health").json() == {"ok": True, "database": "sqlite", "admin_enabled": True}


def test_booking_happy_path(client, app):
    r = client.post("/en/book", data=booking_data(), follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/en/book/thanks?ref=")
    page = client.get(r.headers["location"]).text
    assert "for 4 on" in page and "19:00" in page
    with app.state.Session() as s:
        b = s.query(Booking).one()
        assert (b.name, b.status, b.lang, b.party_size) == ("Ada Lovelace", "new", "en", 4)


def test_booking_errors_keep_what_was_typed(client, app):
    r = client.post("/zh/book", data=booking_data(phone="x", notes="生日"))
    assert r.status_code == 400 and "请填写有效的电话号码" in r.text and "生日" in r.text
    with app.state.Session() as s:
        assert s.query(Booking).count() == 0


def test_html_in_booking_is_escaped(client, admin):
    client.post("/en/book", data=booking_data(name="<script>x</script>"))
    page = admin.get("/admin").text
    assert "<script>x</script>" not in page and "&lt;script&gt;" in page


def test_honeypot_silently_drops_spam(client, app):
    r = client.post("/en/book", data=booking_data(website="http://spam"), follow_redirects=False)
    assert r.status_code == 303
    with app.state.Session() as s:
        assert s.query(Booking).count() == 0


def test_booking_rate_limit(client):
    for _ in range(5):
        assert client.post("/en/book", data=booking_data(), follow_redirects=False).status_code == 303
    r = client.post("/en/book", data=booking_data())
    assert r.status_code == 429 and "Please call us instead" in r.text


def test_thanks_page_does_not_leak_old_bookings(client, app):
    from datetime import datetime, timedelta, timezone
    client.post("/en/book", data=booking_data())
    with app.state.Session() as s:
        b = s.query(Booking).one()
        b.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        s.commit()
    assert "Ada" not in client.get("/en/book/thanks?ref=1").text and "for 4" not in client.get("/en/book/thanks?ref=1").text


def test_book_page_offers_slots_and_private_option(client):
    page = client.get("/en/book?kind=private").text
    assert 'value="private" checked' in page and '"sat": ["12:00"' in page


# ---------- admin ----------

def test_admin_pages_need_login(client):
    for url in ("/admin", "/admin/menu", "/admin/settings"):
        r = client.get(url, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/admin/login", url
    assert client.post("/admin/bookings/1/status", data={"status": "confirmed"}, follow_redirects=False).status_code == 303


def test_wrong_password_and_forged_cookie_are_rejected(client):
    r = client.post("/admin/login", data={"password": "nope"})
    assert r.status_code == 401 and "Wrong password" in r.text
    client.cookies.set("kin_admin", "9999999999.deadbeef", path="/admin")
    assert client.get("/admin", follow_redirects=False).status_code == 303


def test_login_is_rate_limited(client):
    for _ in range(8):
        client.post("/admin/login", data={"password": "nope"})
    assert client.post("/admin/login", data={"password": "test-password"}).status_code == 429


def test_admin_disabled_without_password(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    c = TestClient(create_app(database_url=f"sqlite:///{(tmp_path / 'x.db').as_posix()}", admin_password=""))
    assert "switched off" in c.get("/admin/login").text
    assert c.post("/admin/login", data={"password": ""}).status_code == 401


def test_admin_confirms_a_booking(client, admin, app):
    client.post("/en/book", data=booking_data())
    page = admin.get("/admin").text
    assert "Ada Lovelace" in page and "1 new" in page
    r = admin.post("/admin/bookings/1/status", data={"status": "confirmed"}, follow_redirects=False)
    assert r.status_code == 303
    with app.state.Session() as s:
        assert s.get(Booking, 1).status == "confirmed"


def test_cross_site_admin_post_is_blocked(client, admin):
    client.post("/en/book", data=booking_data())
    r = admin.post("/admin/bookings/1/status", data={"status": "declined"}, headers={"origin": "https://evil.example"})
    assert r.status_code == 403


def test_admin_edits_menu_and_site_updates(admin, client):
    page = admin.get("/admin/menu").text
    cat_id = re.search(r'id="cat(\d+)"', page).group(1)
    r = admin.post("/admin/menu/item", data={"category_id": cat_id, "name_en": "Matcha mochi", "name_zh": "抹茶麻糬",
                                             "price": "£5.5", "allergens": ["milk", "bogus"], "vegetarian": "1",
                                             "available": "1"}, follow_redirects=False)
    assert r.status_code == 303
    en = client.get("/en/menu").text
    assert "Matcha mochi" in en and "£5.50" in en and "Allergens:</b> Milk" in en and "bogus" not in en
    assert "抹茶麻糬" in client.get("/zh/menu").text


def test_admin_rejects_bad_price(admin):
    page = admin.get("/admin/menu").text
    cat_id = re.search(r'id="cat(\d+)"', page).group(1)
    r = admin.post("/admin/menu/item", data={"category_id": cat_id, "name_en": "X", "price": "cheap"})
    assert r.status_code == 400


def test_admin_deletes_a_section(admin, client):
    page = admin.get("/admin/menu").text
    cat_id = re.search(r'id="cat(\d+)"', page).group(1)
    admin.post(f"/admin/menu/category/{cat_id}/delete")
    assert "Salmon nigiri" not in client.get("/en/menu").text


def test_admin_edits_details_and_hours(admin, client):
    form = {"name_en": "Golden Wave", "name_zh": "金浪", "tagline_en": "Hi", "tagline_zh": "", "notice_en": "",
            "notice_zh": "", "story_en": "s", "story_zh": "", "address_en": "1 Real St", "address_zh": "",
            "phone_en": "0131 496 0001", "phone_zh": "", "email_en": "", "email_zh": "",
            **{f"hours_{d}": "" for d in ["mon", "tue", "wed", "thu", "fri", "sun"]}, "hours_sat": "10:00-12:00"}
    assert admin.post("/admin/settings", data=form, follow_redirects=False).status_code == 303
    en, zh = client.get("/en").text, client.get("/zh").text
    assert "Golden Wave" in en and "金浪" in zh and 'class="notice"' not in en
    assert "Hi" in zh   # empty Chinese falls back to English
    assert '"sat": ["10:00"' in client.get("/en/book").text
    day = next_open_day("sat").isoformat()
    assert client.post("/en/book", data=booking_data(day=day, at="19:00")).status_code == 400
    assert client.post("/en/book", data=booking_data(day=day, at="10:30"), follow_redirects=False).status_code == 303


def test_bad_hours_show_an_error_and_keep_old_hours(admin, client):
    r = admin.post("/admin/settings", data={"hours_tue": "lunchtime"}, follow_redirects=True)
    assert "write times like" in r.text
    assert '"tue": ["12:00"' in client.get("/en/book").text


def test_logout(admin):
    admin.post("/admin/logout")
    assert admin.get("/admin", follow_redirects=False).status_code == 303
