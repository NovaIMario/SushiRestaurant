"""English / Chinese interface text. Menu and settings text lives in the database instead
(each row has an English and a Chinese column, and Chinese falls back to English when empty)."""

LANGS = ("en", "zh")

STRINGS = {
    "en": {
        "lang_name": "English", "switch_to": "中文",
        "nav_home": "Home", "nav_menu": "Menu", "nav_book": "Book", "nav_visit": "Visit us",
        "call_us": "Call us", "book_table": "Book a table", "see_menu": "See the menu",
        "our_story": "Our story", "opening_hours": "Opening hours", "closed": "Closed", "find_us": "Find us",
        "open_in_maps": "Open in Google Maps", "photo_soon": "Photo coming soon",
        "highlights": "From our kitchen",
        "hl_sushi": "Sushi", "hl_sushi_text": "Nigiri and rolls made to order with fish from Scottish waters.",
        "hl_ramen": "Ramen", "hl_ramen_text": "Slow-cooked broths, springy noodles and toppings made in house.",
        "hl_private": "Private dining", "hl_private_text": "Birthdays, family dinners and team events: tell us what you're planning.",
        "menu_title": "Menu", "vegetarian": "Vegetarian", "spicy": "Spicy", "allergens": "Allergens",
        "allergen_notice": "Allergen information for each dish is coming soon. If you have an allergy or "
                           "intolerance, please ask our staff before ordering.",
        "allergen_ask": "Ask staff about allergens",
        "sold_out": "Not available today",
        "book_title": "Book with us", "book_intro": "Send us a request and we'll call or email you to confirm. "
                                                    "Prefer to talk? Call us any time we're open.",
        "kind": "What would you like to book?", "kind_table": "A table", "kind_private": "Private dining / event",
        "date": "Date", "time": "Time", "party": "Number of guests", "name": "Your name", "phone": "Phone",
        "email": "Email (optional)", "notes": "Anything we should know?",
        "notes_ph": "Allergies, high chair, occasion, menu ideas for events...",
        "consent": "I agree that {name} may store these details to handle my booking.",
        "privacy": "Privacy notice", "send_request": "Send booking request", "pick_date_first": "Pick a date first",
        "no_times": "We're closed on this day",
        "private_hint": "For private dining and events (8 or more guests) we'll get in touch to plan the details.",
        "thanks_title": "Thank you!", "thanks_text": "We've received your request for {party} on {date} at {time}. "
                                                    "It isn't confirmed yet: we'll contact you shortly.",
        "back_home": "Back to the home page",
        "err_name": "Please enter your name.", "err_phone": "Please enter a valid phone number.",
        "err_email": "That email address doesn't look right.", "err_date": "Please choose a date between today and {days} days ahead.",
        "err_time": "Please choose one of the available times.", "err_party": "Please choose between {lo} and {hi} guests.",
        "err_consent": "Please tick the box so we can store your details.", "err_kind": "Please choose what to book.",
        "err_rate": "Too many requests from your connection. Please call us instead.", "err_fix": "Please check the form:",
        "footer_rights": "All rights reserved.",
        "not_found": "Page not found", "not_found_text": "That page doesn't exist.",
    },
    "zh": {
        "lang_name": "中文", "switch_to": "English",
        "nav_home": "首页", "nav_menu": "菜单", "nav_book": "预订", "nav_visit": "到店",
        "call_us": "致电我们", "book_table": "预订座位", "see_menu": "查看菜单",
        "our_story": "我们的故事", "opening_hours": "营业时间", "closed": "休息", "find_us": "地址",
        "open_in_maps": "在 Google 地图中打开", "photo_soon": "图片即将更新",
        "highlights": "厨房精选",
        "hl_sushi": "寿司", "hl_sushi_text": "现点现做的握寿司与卷寿司，选用苏格兰海域的鲜鱼。",
        "hl_ramen": "拉面", "hl_ramen_text": "慢火熬制的汤底、弹牙的面条和自制配料。",
        "hl_private": "私人宴请", "hl_private_text": "生日、家庭聚餐、公司活动：告诉我们您的计划。",
        "menu_title": "菜单", "vegetarian": "素食", "spicy": "辣", "allergens": "过敏原",
        "allergen_notice": "各菜品的过敏原信息即将更新。如您有食物过敏或不耐受，请在点餐前咨询店员。",
        "allergen_ask": "过敏原请咨询店员",
        "sold_out": "今日暂停供应",
        "book_title": "预订", "book_intro": "提交预订申请后，我们会致电或发邮件与您确认。想直接沟通？营业时间内欢迎来电。",
        "kind": "您想预订什么？", "kind_table": "餐桌", "kind_private": "私人宴请 / 活动",
        "date": "日期", "time": "时间", "party": "人数", "name": "姓名", "phone": "电话",
        "email": "电子邮箱（选填）", "notes": "还有什么需要我们知道的吗？",
        "notes_ph": "过敏、儿童座椅、庆祝场合、活动菜单想法……",
        "consent": "我同意「{name}」保存以上信息用于处理我的预订。",
        "privacy": "隐私声明", "send_request": "提交预订申请", "pick_date_first": "请先选择日期",
        "no_times": "当天休息",
        "private_hint": "私人宴请和活动（8 人或以上）我们会与您联系，商定细节。",
        "thanks_title": "谢谢！", "thanks_text": "我们已收到您 {date} {time}、{party} 位的预订申请。预订尚未确认，我们会尽快与您联系。",
        "back_home": "返回首页",
        "err_name": "请填写姓名。", "err_phone": "请填写有效的电话号码。",
        "err_email": "电子邮箱格式不正确。", "err_date": "请选择今天起 {days} 天内的日期。",
        "err_time": "请选择可预订的时间。", "err_party": "人数请选择 {lo} 至 {hi} 位。",
        "err_consent": "请勾选同意，以便我们保存您的信息。", "err_kind": "请选择预订类型。",
        "err_rate": "您的请求过于频繁，请直接致电我们。", "err_fix": "请检查以下内容：",
        "footer_rights": "版权所有。",
        "not_found": "页面不存在", "not_found_text": "找不到这个页面。",
    },
}

DAY_NAMES = {
    "en": {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday", "fri": "Friday",
           "sat": "Saturday", "sun": "Sunday"},
    "zh": {"mon": "星期一", "tue": "星期二", "wed": "星期三", "thu": "星期四", "fri": "星期五",
           "sat": "星期六", "sun": "星期日"},
}

# Every key must exist in both languages (checked by a test).
assert STRINGS["en"].keys() == STRINGS["zh"].keys()


def translator(lang: str):
    table = STRINGS[lang]

    def t(key: str, **kw) -> str:
        text = table[key]
        return text.format(**kw) if kw else text
    return t


def pick(obj, field: str, lang: str) -> str:
    """`pick(item, "name", "zh")` -> item.name_zh, or item.name_en if there's no Chinese text."""
    if lang == "zh":
        zh = getattr(obj, f"{field}_zh", "")
        if zh:
            return zh
    return getattr(obj, f"{field}_en", "")
