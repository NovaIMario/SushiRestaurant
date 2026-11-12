"""Restaurant website: bilingual public pages (/en/..., /zh/...), booking requests, and an admin
area where the owners edit the menu, details and opening hours and handle bookings."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from zoneinfo import ZoneInfo

from fastapi import APIRouter, FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from starlette.exceptions import HTTPException

from . import booking as bk
from . import config
from .db import (ALLERGENS, BOOKING_STATUSES, DAYS, Booking, Category, Item, Setting, init_db, make_engine)
from .i18n import DAY_NAMES, LANGS, pick, translator
from .security import COOKIE, SESSION_SECONDS, RateLimiter, make_session, password_ok, valid_session

HERE = Path(__file__).resolve().parent


def create_app(database_url: str | None = None, admin_password: str | None = None,
               secret_key: str | None = None) -> FastAPI:
    engine = make_engine(database_url or config.DATABASE_URL)
    Session = init_db(engine)
    admin_pw = config.ADMIN_PASSWORD if admin_password is None else admin_password
    secret = secret_key or config.SECRET_KEY
    booking_limiter = RateLimiter(limit=5, window=600)
    login_limiter = RateLimiter(limit=8, window=600)

    app = FastAPI(title="Restaurant", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.Session = Session
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.filters["money"] = lambda pence: f"£{pence / 100:.2f}"
    templates.env.globals["v"] = max(int(f.stat().st_mtime) for f in (HERE / "static").rglob("*") if f.is_file())

    # ---------- helpers ----------

    def settings(s) -> dict[str, Setting]:
        return {row.key: row for row in s.scalars(select(Setting))}

    def client_ip(request: Request) -> str:
        return request.client.host if request.client else "?"

    def other_lang_url(request: Request, lang: str) -> str:
        other = "zh" if lang == "en" else "en"
        parts = request.url.path.split("/")
        if len(parts) > 1 and parts[1] in LANGS:
            parts[1] = other
        return "/".join(parts) or f"/{other}"

    def render(request: Request, name: str, lang: str = "en", status_code: int = 200, **ctx):
        with Session() as s:
            st = settings(s)
        hours = bk.parse_hours(st["hours"].value_en if "hours" in st else "{}")
        site = {k: pick(v, "value", lang) for k, v in st.items() if k != "hours"}
        address = st["address"].value_en if "address" in st else ""
        response = templates.TemplateResponse(request, name, {
            "lang": lang, "t": translator(lang), "pick": lambda o, f: pick(o, f, lang), "site": site,
            "hours": hours, "days": DAYS, "day_names": DAY_NAMES[lang], "switch_url": other_lang_url(request, lang),
            "phone_href": "tel:" + "".join(c for c in site.get("phone", "") if c.isdigit() or c == "+"),
            "maps_url": "https://www.google.com/maps/search/?api=1&query=" + quote_plus(address),
            "year": datetime.now(ZoneInfo(config.TIMEZONE)).year,
            "today_key": DAYS[datetime.now(ZoneInfo(config.TIMEZONE)).weekday()], **ctx,
        }, status_code=status_code)
        if lang in LANGS and not request.url.path.startswith("/admin"):
            response.set_cookie("lang", lang, max_age=365 * 86400, samesite="lax")
        return response

    def check_lang(lang: str) -> str:
        if lang not in LANGS:
            raise HTTPException(404)
        return lang

    # ---------- public pages (included last: "/{lang}" would otherwise swallow "/admin", "/health") ----------

    public = APIRouter()

    @app.get("/", include_in_schema=False)
    def root(request: Request):
        lang = request.cookies.get("lang")
        if lang not in LANGS:
            lang = "zh" if "zh" in request.headers.get("accept-language", "").lower()[:5] else "en"
        return RedirectResponse(f"/{lang}", status_code=302)

    @public.get("/{lang}", response_class=HTMLResponse)
    def home(request: Request, lang: str):
        return render(request, "home.html", check_lang(lang), page="home")

    @public.get("/{lang}/menu", response_class=HTMLResponse)
    def menu(request: Request, lang: str):
        with Session() as s:
            cats = s.scalars(select(Category).order_by(Category.sort, Category.id)).unique().all()
            for c in cats:
                _ = c.items  # load while the session is open
        any_allergens = any(i.allergen_list for c in cats for i in c.items)
        return render(request, "menu.html", check_lang(lang), page="menu", categories=cats,
                      allergen_names={k: v[0 if lang == "en" else 1] for k, v in ALLERGENS.items()},
                      any_allergens=any_allergens)

    def booking_page(request: Request, lang: str, form: bk.BookingForm, status_code: int = 200):
        with Session() as s:
            hours = bk.parse_hours(settings(s)["hours"].value_en)
        today = datetime.now(ZoneInfo(config.TIMEZONE)).date()
        return render(request, "book.html", lang, status_code=status_code, page="book", form=form,
                      slots_json=json.dumps(bk.all_slots(hours)), min_date=today.isoformat(),
                      max_date=(today + timedelta(days=config.BOOKING_DAYS_AHEAD)).isoformat(),
                      party_limits=bk.PARTY_LIMITS)

    @public.get("/{lang}/book", response_class=HTMLResponse)
    def book_form(request: Request, lang: str, kind: str = "table"):
        return booking_page(request, check_lang(lang), bk.BookingForm(kind=kind if kind in bk.PARTY_LIMITS else "table"))

    @public.post("/{lang}/book", response_class=HTMLResponse)
    def book_submit(request: Request, lang: str, kind: str = Form("table"), day: str = Form(""), at: str = Form(""),
                    party_size: str = Form("2"), name: str = Form(""), phone: str = Form(""), email: str = Form(""),
                    notes: str = Form(""), consent: str = Form(""), website: str = Form("")):
        lang = check_lang(lang)
        t = translator(lang)
        form = bk.BookingForm(kind=kind, day=day, at=at, party_size=party_size, name=name, phone=phone,
                              email=email, notes=notes, consent=bool(consent))
        if website:  # honeypot: a hidden field people never see, but spam bots fill in
            return RedirectResponse(f"/{lang}/book/thanks", status_code=303)
        if not booking_limiter.allow(client_ip(request)):
            form.errors = [t("err_rate")]
            return booking_page(request, lang, form, status_code=429)
        with Session() as s:
            hours = bk.parse_hours(settings(s)["hours"].value_en)
            clean = form.validate(hours, config.TIMEZONE, config.BOOKING_DAYS_AHEAD, t)
            if clean is None:
                return booking_page(request, lang, form, status_code=400)
            b = Booking(**clean, lang=lang)
            s.add(b)
            s.commit()
            ref = b.id
        return RedirectResponse(f"/{lang}/book/thanks?ref={ref}", status_code=303)

    @public.get("/{lang}/book/thanks", response_class=HTMLResponse)
    def book_thanks(request: Request, lang: str, ref: int = 0):
        lang = check_lang(lang)
        with Session() as s:
            b = s.get(Booking, ref) if ref else None
            # Only show details for a booking made in the last hour, so the ref number can't be used
            # to read other people's bookings.
            if b:
                created = b.created_at if b.created_at.tzinfo else b.created_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - created > timedelta(hours=1):
                    b = None
        return render(request, "thanks.html", lang, page="book", booking=b)

    @public.get("/{lang}/privacy", response_class=HTMLResponse)
    def privacy(request: Request, lang: str):
        return render(request, "privacy.html", check_lang(lang), page="privacy")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return FileResponse(HERE / "static" / "favicon.ico", media_type="image/x-icon")

    @app.get("/health")
    def health():
        with Session() as s:
            ok = s.scalar(select(Setting.key).limit(1)) is not None
        return {"ok": ok, "database": engine.dialect.name, "admin_enabled": bool(admin_pw)}

    # ---------- admin ----------

    def is_admin(request: Request) -> bool:
        return bool(admin_pw) and valid_session(secret, request.cookies.get(COOKIE))

    def same_origin(request: Request) -> bool:
        """Admin forms only accept posts from this site (with SameSite=Lax cookies, a second guard
        against cross-site request forgery)."""
        origin = request.headers.get("origin") or request.headers.get("referer")
        return not origin or urlparse(origin).netloc == request.url.netloc

    def admin_guard(request: Request, post: bool = False):
        if not is_admin(request):
            raise HTTPException(303, headers={"Location": "/admin/login"})
        if post and not same_origin(request):
            raise HTTPException(403, "Cross-site request blocked")

    def admin_render(request: Request, name: str, **ctx):
        return render(request, name, "en", **ctx, allergens=ALLERGENS, statuses=BOOKING_STATUSES)

    @app.get("/admin/login", response_class=HTMLResponse)
    def admin_login_page(request: Request):
        return admin_render(request, "admin/login.html", error=None, enabled=bool(admin_pw))

    @app.post("/admin/login")
    def admin_login(request: Request, password: str = Form("")):
        if not login_limiter.allow(client_ip(request)):
            return admin_render(request, "admin/login.html", error="Too many attempts. Wait 10 minutes. 尝试次数过多，请等 10 分钟。",
                                enabled=True, status_code=429)
        if not password_ok(password, admin_pw):
            return admin_render(request, "admin/login.html", error="Wrong password. 密码错误。", enabled=bool(admin_pw),
                                status_code=401)
        r = RedirectResponse("/admin", status_code=303)
        r.set_cookie(COOKIE, make_session(secret), max_age=SESSION_SECONDS, httponly=True, samesite="lax",
                     secure=request.url.scheme == "https", path="/admin")
        return r

    @app.post("/admin/logout")
    def admin_logout(request: Request):
        r = RedirectResponse("/admin/login", status_code=303)
        r.delete_cookie(COOKIE, path="/admin")
        return r

    @app.get("/admin", response_class=HTMLResponse)
    def admin_bookings(request: Request, show: str = "upcoming"):
        admin_guard(request)
        today = datetime.now(ZoneInfo(config.TIMEZONE)).date()
        with Session() as s:
            q = select(Booking)
            if show == "past":
                q = q.where(Booking.day < today).order_by(Booking.day.desc(), Booking.at.desc()).limit(200)
            else:
                q = q.where(Booking.day >= today).order_by(Booking.day, Booking.at)
            rows = s.scalars(q).all()
        return admin_render(request, "admin/bookings.html", bookings=rows, show=show, today=today,
                            new_count=sum(1 for b in rows if b.status == "new"))

    @app.post("/admin/bookings/{booking_id}/status")
    def admin_booking_status(request: Request, booking_id: int, status: str = Form(...), show: str = Form("upcoming")):
        admin_guard(request, post=True)
        if status not in BOOKING_STATUSES:
            raise HTTPException(400, "Unknown status")
        with Session() as s:
            b = s.get(Booking, booking_id)
            if not b:
                raise HTTPException(404)
            b.status = status
            s.commit()
        return RedirectResponse(f"/admin?show={'past' if show == 'past' else 'upcoming'}#b{booking_id}", status_code=303)

    @app.get("/admin/menu", response_class=HTMLResponse)
    def admin_menu(request: Request, saved: str = ""):
        admin_guard(request)
        with Session() as s:
            cats = s.scalars(select(Category).order_by(Category.sort, Category.id)).unique().all()
            for c in cats:
                _ = c.items
        return admin_render(request, "admin/menu.html", categories=cats, saved=saved)

    @app.post("/admin/menu/category")
    def admin_save_category(request: Request, id: int = Form(0), name_en: str = Form(...), name_zh: str = Form(""),
                            sort: int = Form(0)):
        admin_guard(request, post=True)
        with Session() as s:
            c = s.get(Category, id) if id else Category()
            if c is None:
                raise HTTPException(404)
            c.name_en, c.name_zh, c.sort = name_en.strip()[:80] or "Untitled", name_zh.strip()[:80], sort
            s.add(c)
            s.commit()
        return RedirectResponse("/admin/menu?saved=1", status_code=303)

    @app.post("/admin/menu/category/{cat_id}/delete")
    def admin_delete_category(request: Request, cat_id: int):
        admin_guard(request, post=True)
        with Session() as s:
            c = s.get(Category, cat_id)
            if c:
                s.delete(c)
                s.commit()
        return RedirectResponse("/admin/menu?saved=1", status_code=303)

    @app.post("/admin/menu/item")
    async def admin_save_item(request: Request):
        admin_guard(request, post=True)
        f = await request.form()
        with Session() as s:
            item_id = int(f.get("id") or 0)
            item = s.get(Item, item_id) if item_id else Item()
            cat = s.get(Category, int(f.get("category_id") or 0))
            if item is None or cat is None:
                raise HTTPException(404)
            try:
                price = round(float(str(f.get("price", "0")).replace("£", "").strip() or 0) * 100)
            except ValueError:
                raise HTTPException(400, "Price must be a number like 12.50")
            item.category_id = cat.id
            item.name_en = str(f.get("name_en", "")).strip()[:120] or "Untitled"
            item.name_zh = str(f.get("name_zh", "")).strip()[:120]
            item.desc_en = str(f.get("desc_en", "")).strip()[:500]
            item.desc_zh = str(f.get("desc_zh", "")).strip()[:500]
            item.price_pence = max(0, price)
            item.allergens = ",".join(a for a in f.getlist("allergens") if a in ALLERGENS)
            item.vegetarian = bool(f.get("vegetarian"))
            item.spicy = min(3, max(0, int(f.get("spicy") or 0)))
            item.available = bool(f.get("available"))
            item.sort = int(f.get("sort") or 0)
            s.add(item)
            s.commit()
            anchor = item.id
        return RedirectResponse(f"/admin/menu?saved=1#item{anchor}", status_code=303)

    @app.post("/admin/menu/item/{item_id}/delete")
    def admin_delete_item(request: Request, item_id: int):
        admin_guard(request, post=True)
        with Session() as s:
            item = s.get(Item, item_id)
            if item:
                s.delete(item)
                s.commit()
        return RedirectResponse("/admin/menu?saved=1", status_code=303)

    @app.get("/admin/settings", response_class=HTMLResponse)
    def admin_settings(request: Request, saved: str = "", error: str = ""):
        admin_guard(request)
        with Session() as s:
            st = settings(s)
        return admin_render(request, "admin/settings.html", st=st, saved=saved, error=error,
                            hours_text=bk.hours_to_text(bk.parse_hours(st["hours"].value_en)))

    @app.post("/admin/settings")
    async def admin_save_settings(request: Request):
        admin_guard(request, post=True)
        f = await request.form()
        try:
            hours = bk.text_to_hours({d: str(f.get(f"hours_{d}", "")) for d in DAYS})
        except ValueError as e:
            return RedirectResponse(f"/admin/settings?error={quote_plus(str(e))}", status_code=303)
        with Session() as s:
            st = settings(s)
            for key, row in st.items():
                if key == "hours":
                    row.value_en = json.dumps(hours)
                elif f"{key}_en" in f:
                    row.value_en = str(f.get(f"{key}_en", "")).strip()[:3000]
                    row.value_zh = str(f.get(f"{key}_zh", "")).strip()[:3000]
            s.commit()
        return RedirectResponse("/admin/settings?saved=1", status_code=303)

    app.include_router(public)

    # ---------- errors ----------

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
            return RedirectResponse(exc.headers["Location"], status_code=303)
        lang = request.url.path.split("/")[1] if request.url.path.count("/") >= 1 else "en"
        lang = lang if lang in LANGS else (request.cookies.get("lang") if request.cookies.get("lang") in LANGS else "en")
        if exc.status_code == 404:
            return render(request, "error.html", lang, status_code=404, page="error", message=None)
        return render(request, "error.html", lang, status_code=exc.status_code, page="error", message=exc.detail)

    return app


app = create_app()
