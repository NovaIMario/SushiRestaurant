# Kin 金 — restaurant website

A bilingual (English / 中文) website for a Japanese restaurant in Edinburgh: home page, menu,
booking requests (tables and private dining), and an admin area where the owners edit everything
without touching code.

**Live:** https://sushirestaurant-61sj.onrender.com ([English](https://sushirestaurant-61sj.onrender.com/en) · [中文](https://sushirestaurant-61sj.onrender.com/zh))

**Status:** pre-opening. The name, address, phone, menu, prices, hours and photos are all
placeholders and can be changed in the admin page.

## What it does

| Page | |
|---|---|
| `/en`, `/zh` | Home: story, highlights, address, opening hours. `/` picks the visitor's language. |
| `/en/menu` | Menu by section, with prices, vegetarian/spicy tags and allergens. |
| `/en/book` | Booking request form. Times come from the opening hours (every 15 min, last seating 1 h before closing). |
| `/admin` | Bookings: confirm, decline or cancel. |
| `/admin/menu` | Add, edit, hide or delete dishes and sections; tick allergens per dish. |
| `/admin/settings` | Name, tagline, top banner, story, address, phone, email, opening hours. |

The language toggle keeps you on the same page. Chinese text falls back to English if left empty.

## Run locally

```bash
pip install -r requirements-dev.txt
cp .env.example .env        # then set ADMIN_PASSWORD and SECRET_KEY
uvicorn app.main:app --reload
python -m pytest            # 48 tests
```

Locally the data is a SQLite file in `data/`.

## Deploy on Render

1. Push this folder to a GitHub repo and create a **Web Service** from it on Render (Docker; `render.yaml` is included).
2. Create a **new** Supabase project (keep it separate from other projects) and copy its *Session pooler* connection string.
3. In Render → Environment set `ADMIN_PASSWORD`, `SECRET_KEY` (random) and `DATABASE_URL` (the Supabase string).
   Without `DATABASE_URL`, Render's disk is wiped on every deploy and bookings would be lost.

## Before opening

- Replace the placeholders in `/admin/settings` and `/admin/menu`; remove the top banner.
- **Allergens:** tick the allergens for every dish (UK law requires the 14 major allergens to be available).
  Until a dish has them, the menu shows "Ask staff about allergens".
- Swap the drawn placeholder images for real photos.
- Check the privacy notice (`/en/privacy`) wording.
- Optional later: a custom domain, email notifications for new bookings.

## Security notes

Admin login uses an HMAC-signed cookie (12 h, HttpOnly, SameSite=Lax), constant-time password check and
rate limiting; admin forms reject cross-site posts. Bookings are validated server-side, rate-limited per IP,
and have a honeypot field against spam bots. All user text is HTML-escaped by the templates.
