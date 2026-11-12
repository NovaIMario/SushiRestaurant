"""Database tables and placeholder content.

SQLite locally, Postgres in production; SQLAlchemy hides the difference. Tables are created on
startup and filled with placeholder content the first time, so the site is never empty.
"""
import json
from datetime import date, datetime, time, timezone

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Time, create_engine,
                        select)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Setting(Base):
    """Editable site text and details, in both languages (`value_zh` falls back to English)."""
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value_en: Mapped[str] = mapped_column(Text, default="")
    value_zh: Mapped[str] = mapped_column(Text, default="")


class Category(Base):
    __tablename__ = "menu_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_en: Mapped[str] = mapped_column(String(80))
    name_zh: Mapped[str] = mapped_column(String(80), default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    items: Mapped[list["Item"]] = relationship(back_populates="category", cascade="all, delete-orphan",
                                               order_by="Item.sort, Item.id")


class Item(Base):
    __tablename__ = "menu_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("menu_categories.id", ondelete="CASCADE"))
    name_en: Mapped[str] = mapped_column(String(120))
    name_zh: Mapped[str] = mapped_column(String(120), default="")
    desc_en: Mapped[str] = mapped_column(Text, default="")
    desc_zh: Mapped[str] = mapped_column(Text, default="")
    price_pence: Mapped[int] = mapped_column(Integer, default=0)
    allergens: Mapped[str] = mapped_column(String(300), default="")   # comma-separated keys from ALLERGENS
    vegetarian: Mapped[bool] = mapped_column(Boolean, default=False)
    spicy: Mapped[int] = mapped_column(Integer, default=0)            # 0-3 chillies
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[Category] = relationship(back_populates="items")

    @property
    def allergen_list(self) -> list[str]:
        return [a for a in self.allergens.split(",") if a in ALLERGENS]


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))              # "table" or "private"
    name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(120), default="")
    day: Mapped[date] = mapped_column(Date)
    at: Mapped[time] = mapped_column(Time)
    party_size: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="new")  # new / confirmed / declined / cancelled
    lang: Mapped[str] = mapped_column(String(2), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


BOOKING_STATUSES = ("new", "confirmed", "declined", "cancelled")

# The 14 allergens UK food law requires restaurants to declare. Key -> (English, Chinese).
ALLERGENS = {
    "celery": ("Celery", "芹菜"), "gluten": ("Gluten", "麸质"), "crustaceans": ("Crustaceans", "甲壳类"),
    "eggs": ("Eggs", "蛋"), "fish": ("Fish", "鱼"), "lupin": ("Lupin", "羽扇豆"), "milk": ("Milk", "奶"),
    "molluscs": ("Molluscs", "软体动物"), "mustard": ("Mustard", "芥末"), "nuts": ("Tree nuts", "坚果"),
    "peanuts": ("Peanuts", "花生"), "sesame": ("Sesame", "芝麻"), "soya": ("Soya", "大豆"),
    "sulphites": ("Sulphites", "亚硫酸盐"),
}

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# ---------- placeholder content (everything here is meant to be replaced in the admin page) ----------

DEFAULT_HOURS = {"mon": [], **{d: [["12:00", "14:30"], ["17:30", "22:00"]] for d in DAYS[1:]}}

DEFAULT_SETTINGS = {
    "name": ("Kin", "金"),
    "tagline": ("Sushi & ramen in the heart of Edinburgh", "爱丁堡市中心的寿司与拉面"),
    "story": (
        "We are a Chinese family who have spent our lives in professional kitchens, first in Italy, then across "
        "the UK. Kin is the first restaurant that is truly ours: Japanese food made with the care and precision "
        "we learned along the way, served the way we like to welcome guests at home.",
        "我们是一个华人家庭，多年来一直在专业厨房工作，先在意大利，后来在英国各地。"
        "「金」是第一家真正属于我们自己的餐厅：用一路积累的用心与精准制作日本料理，"
        "像在家里招待客人一样欢迎每一位来宾。",
    ),
    "address": ("123 Placeholder Street, Edinburgh EH1 1AA", "爱丁堡 Placeholder Street 123 号，EH1 1AA"),
    # 0131 496 0000-0999 is reserved by Ofcom for TV and drama, so this placeholder never rings anyone.
    "phone": ("0131 496 0000", ""),
    "email": ("hello@example.com", ""),
    "notice": ("Opening soon — menu, prices and hours are placeholders.", "即将开业 — 菜单、价格和营业时间仅为示例。"),
    "hours": (json.dumps(DEFAULT_HOURS), ""),
}

DEFAULT_MENU = [
    (("Nigiri", "握寿司"), [
        ("Salmon nigiri (2 pcs)", "三文鱼握寿司（2 件）", "Scottish salmon on seasoned rice.", "苏格兰三文鱼配醋饭。", 550, False, 0),
        ("Tuna nigiri (2 pcs)", "金枪鱼握寿司（2 件）", "", "", 650, False, 0),
        ("Prawn nigiri (2 pcs)", "鲜虾握寿司（2 件）", "", "", 550, False, 0),
    ]),
    (("Maki & rolls", "卷寿司"), [
        ("Dragon roll (8 pcs)", "龙卷（8 件）", "Prawn tempura, avocado, eel sauce.", "天妇罗虾、牛油果、鳗鱼汁。", 1250, False, 0),
        ("Avocado maki (6 pcs)", "牛油果细卷（6 件）", "", "", 600, True, 0),
        ("Spicy tuna roll (8 pcs)", "香辣金枪鱼卷（8 件）", "", "", 1150, False, 2),
    ]),
    (("Ramen", "拉面"), [
        ("Tonkotsu ramen", "豚骨拉面", "Rich pork broth, chashu, soft egg, nori.", "浓郁猪骨汤、叉烧、溏心蛋、海苔。", 1450, False, 0),
        ("Spicy miso ramen", "辣味噌拉面", "", "", 1450, False, 2),
        ("Vegetable shoyu ramen", "蔬菜酱油拉面", "", "", 1300, True, 0),
    ]),
    (("Small plates", "小食"), [
        ("Edamame", "毛豆", "Sea salt.", "海盐。", 450, True, 0),
        ("Chicken gyoza (5 pcs)", "鸡肉煎饺（5 件）", "", "", 650, False, 0),
        ("Prawn tempura", "天妇罗虾", "", "", 850, False, 0),
    ]),
]


def make_engine(url: str):
    if url.startswith("sqlite"):
        from pathlib import Path
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    # pool_pre_ping: hosted Postgres (e.g. Supabase) drops idle connections; recycle quietly.
    return create_engine(url, pool_pre_ping=True, pool_recycle=300, pool_size=3, max_overflow=2)


def init_db(engine) -> sessionmaker:
    Base.metadata.create_all(engine)
    Session_ = sessionmaker(engine, expire_on_commit=False)
    with Session_() as s:
        seed(s)
    return Session_


def seed(s: Session) -> None:
    """Fill in placeholder settings and menu, only where nothing exists yet (never overwrites edits)."""
    have = {k for (k,) in s.execute(select(Setting.key))}
    for key, (en, zh) in DEFAULT_SETTINGS.items():
        if key not in have:
            s.add(Setting(key=key, value_en=en, value_zh=zh))
    if s.scalar(select(Category.id).limit(1)) is None:
        for ci, ((cen, czh), items) in enumerate(DEFAULT_MENU):
            cat = Category(name_en=cen, name_zh=czh, sort=ci)
            for ii, (nen, nzh, den, dzh, price, veg, spicy) in enumerate(items):
                # No allergens on placeholder dishes on purpose: invented allergen data is dangerous.
                # The menu shows "ask our staff" until real information is entered in the admin page.
                cat.items.append(Item(name_en=nen, name_zh=nzh, desc_en=den, desc_zh=dzh, price_pence=price,
                                      vegetarian=veg, spicy=spicy, sort=ii))
            s.add(cat)
    s.commit()
