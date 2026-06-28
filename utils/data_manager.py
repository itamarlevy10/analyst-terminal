import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

DATA_FILE = Path(__file__).parent.parent / "data" / "companies.json"
DEFAULT_FILE = Path(__file__).parent.parent / "data" / "default_data.json"

SOURCE_META = {
    "linkedin":  {"label": "LinkedIn",  "color": "#1A5FA8", "bg": "#E6F0FA", "icon": "🔵"},
    "google":    {"label": "Google",    "color": "#B05E0D", "bg": "#FDF3E0", "icon": "🟠"},
    "maya":      {"label": "מאיה",      "color": "#4A3DAA", "bg": "#F0EDF9", "icon": "🟣"},
    "manual":    {"label": "ידני",      "color": "#2A6B24", "bg": "#EAF4E8", "icon": "✏️"},
    "other":     {"label": "אחר",       "color": "#555",    "bg": "#F2F2F2", "icon": "⚪"},
}

AVATAR_COLORS = [
    ("#E6F1FB", "#1A5FA8"),
    ("#EAF4E8", "#2A6B24"),
    ("#FAF0E0", "#8A4E0A"),
    ("#F0EDF9", "#4A3DAA"),
    ("#FCEBEB", "#A32D2D"),
    ("#E1F5EE", "#0F6E56"),
]


def load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    with open(DEFAULT_FILE) as f:
        data = json.load(f)
    save_data(data)
    return data


def save_data(data: dict):
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_companies(data: dict) -> list:
    return data.get("companies", [])


def get_company(data: dict, company_id: str) -> dict | None:
    for c in data["companies"]:
        if c["id"] == company_id:
            return c
    return None


def add_company(data: dict, name: str, ticker: str, keywords: list[str]) -> dict:
    idx = len(data["companies"])
    bg, fg = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
    initials = "".join(w[0] for w in name.split()[:2]).upper()
    company = {
        "id": name.lower().replace(" ", "_").replace(".", "") + "_" + str(uuid.uuid4())[:4],
        "name": name,
        "ticker": ticker,
        "avatar": initials,
        "avatar_bg": bg,
        "avatar_fg": fg,
        "keywords": [k.strip() for k in keywords if k.strip()],
        "feeds": [],
        "financials": {
            "periods": ["2023", "2024", "2025E", "H1-24", "H2-24", "H1-25", "Q1-25", "Q1-26"],
            "sections": []
        }
    }
    data["companies"].append(company)
    save_data(data)
    return company


def delete_company(data: dict, company_id: str):
    data["companies"] = [c for c in data["companies"] if c["id"] != company_id]
    save_data(data)


def add_feed_item(data: dict, company_id: str, source: str, title: str, url: str = "", notes: str = "") -> dict:
    item = {
        "id": str(uuid.uuid4())[:8],
        "source": source,
        "title": title,
        "url": url,
        "notes": notes,
        "timestamp": datetime.now().isoformat()
    }
    for c in data["companies"]:
        if c["id"] == company_id:
            c["feeds"].insert(0, item)
            break
    save_data(data)
    return item


def delete_feed_item(data: dict, company_id: str, item_id: str):
    for c in data["companies"]:
        if c["id"] == company_id:
            c["feeds"] = [f for f in c["feeds"] if f["id"] != item_id]
            break
    save_data(data)


def add_keyword(data: dict, company_id: str, keyword: str):
    for c in data["companies"]:
        if c["id"] == company_id:
            if keyword not in c["keywords"]:
                c["keywords"].append(keyword)
            break
    save_data(data)


def remove_keyword(data: dict, company_id: str, keyword: str):
    for c in data["companies"]:
        if c["id"] == company_id:
            c["keywords"] = [k for k in c["keywords"] if k != keyword]
            break
    save_data(data)


def update_financial_cell(data: dict, company_id: str, section_idx: int, row_idx: int, period_idx: int, value):
    for c in data["companies"]:
        if c["id"] == company_id:
            c["financials"]["sections"][section_idx]["rows"][row_idx]["values"][period_idx] = value
            break
    save_data(data)


def add_financial_section(data: dict, company_id: str, section_name: str):
    for c in data["companies"]:
        if c["id"] == company_id:
            n = len(c["financials"]["periods"])
            c["financials"]["sections"].append({
                "name": section_name,
                "rows": [],
                "total_label": f'סה"כ {section_name}',
                "total": [0] * n
            })
            break
    save_data(data)


def add_financial_row(data: dict, company_id: str, section_idx: int, row_label: str):
    for c in data["companies"]:
        if c["id"] == company_id:
            n = len(c["financials"]["periods"])
            c["financials"]["sections"][section_idx]["rows"].append({
                "label": row_label,
                "values": [0] * n
            })
            break
    save_data(data)


def add_period(data: dict, company_id: str, period_name: str):
    for c in data["companies"]:
        if c["id"] == company_id:
            c["financials"]["periods"].append(period_name)
            for sec in c["financials"]["sections"]:
                for row in sec["rows"]:
                    row["values"].append(0)
                sec["total"].append(0)
            break
    save_data(data)


def get_avatar_info(company: dict, idx: int) -> tuple[str, str, str]:
    name = company["name"]
    initials = company.get("avatar") or "".join(w[0] for w in name.split()[:2]).upper()
    bg, fg = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
    bg = company.get("avatar_bg", bg)
    fg = company.get("avatar_fg", fg)
    return initials, bg, fg


def fetch_news_for_company(company: dict) -> list:
    try:
        import feedparser
        from time import mktime
    except ImportError:
        return []

    keywords = company.get("keywords", [])
    if not keywords:
        return []

    seen_titles: set[str] = set()
    items = []

    for keyword in keywords:
        url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=iw&gl=IL&ceid=IL:iw"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                published = entry.get("published_parsed")
                if published:
                    ts = datetime.fromtimestamp(mktime(published)).isoformat()
                else:
                    ts = datetime.now().isoformat()
                items.append({
                    "title": title,
                    "url": entry.get("link", ""),
                    "timestamp": ts,
                })
        except Exception:
            continue

    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items[:10]


def format_timestamp(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        delta = datetime.now() - dt
        if delta.seconds < 3600:
            return f"לפני {delta.seconds // 60} דקות"
        if delta.days == 0:
            return f"לפני {delta.seconds // 3600} שעות"
        if delta.days == 1:
            return "אתמול"
        return f"לפני {delta.days} ימים"
    except Exception:
        return ts
