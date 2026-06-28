import json
import os
import uuid
from datetime import datetime, timedelta
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


def add_feed_item(data: dict, company_id: str, source: str, title: str, url: str = "", notes: str = "", timestamp: str | None = None) -> dict:
    item = {
        "id": str(uuid.uuid4())[:8],
        "source": source,
        "title": title,
        "url": url,
        "notes": notes,
        "timestamp": timestamp or datetime.now().isoformat(),
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


def classify_keyword(kw: str) -> str:
    import re
    if re.match(r'^[A-Z]{2,6}$', kw):
        return "blue"
    if any('֐' <= c <= '׿' for c in kw):
        return "purple"
    if kw and kw[0].isupper() and ' ' not in kw:
        return "teal"
    return "amber"


def parse_maya_pdf(pdf_bytes: bytes) -> tuple[list, list] | None:
    """
    Extract financial tables from a Maya PDF report (digital, not scanned).
    Returns (sections, periods) or None on failure.
    - sections: list matching the financials["sections"] schema
    - periods: list of detected column header strings
    """
    try:
        import pdfplumber
        import io
        import re
    except ImportError:
        return None

    HEBREW = re.compile(r'[֐-׿]')
    PERIOD_PAT = re.compile(r'\d{4}|Q[1-4]|H[12]|רבעון|מחצית|שנת')

    def _to_float(s: str) -> float | None:
        s = str(s).strip().replace(",", "").replace(" ", "").replace("\xa0", "")
        s = s.replace("(", "-").replace(")", "")
        try:
            return float(s)
        except ValueError:
            return None

    # Collect all (section_name, label, [values]) tuples
    rows_collected: list[tuple[str, str, list[float]]] = []
    detected_periods: list[str] = []
    current_section = "נתונים כספיים"

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                if not table:
                    continue

                # Detect header row (contains period labels)
                first = [str(c or "").strip() for c in table[0]]
                potential_hdr = [c for c in first[1:] if c and PERIOD_PAT.search(c)]
                if len(potential_hdr) >= 1 and not detected_periods:
                    detected_periods = [c for c in first[1:] if c]
                    data_rows = table[1:]
                else:
                    data_rows = table

                for row in data_rows:
                    cells = [str(c or "").strip() for c in row]
                    cells = [c.replace("\n", " ") for c in cells]

                    # Find Hebrew label (first cell with Hebrew)
                    label = next((c for c in cells if HEBREW.search(c) and len(c) > 1), None)
                    if not label:
                        continue

                    # Check if this looks like a section header (few/no numbers)
                    nums = [_to_float(c) for c in cells if _to_float(c) is not None]
                    if not nums:
                        current_section = label
                        continue

                    rows_collected.append((current_section, label, nums))

    if not rows_collected:
        return None

    # Determine column count from most common row width
    from collections import Counter
    widths = Counter(len(r[2]) for r in rows_collected)
    target_width = widths.most_common(1)[0][0]

    # Build periods list
    if detected_periods:
        periods = detected_periods[:target_width]
        while len(periods) < target_width:
            periods.append(f"עמודה {len(periods)+1}")
    else:
        periods = [f"עמודה {i+1}" for i in range(target_width)]

    # Group rows by section
    from collections import defaultdict
    by_section: dict[str, list] = defaultdict(list)
    for sec, lbl, vals in rows_collected:
        padded = (vals + [0] * target_width)[:target_width]
        by_section[sec].append({"label": lbl, "values": padded})

    sections = []
    for sec_name, rows in by_section.items():
        total = [sum(r["values"][i] for r in rows) for i in range(target_width)]
        sections.append({
            "name": sec_name,
            "rows": rows,
            "total_label": f'סה"כ {sec_name}',
            "total": total,
        })

    return sections, periods


def import_financials_from_maya(data: dict, company_id: str, sections: list, periods: list):
    for c in data["companies"]:
        if c["id"] == company_id:
            c["financials"] = {
                "periods": periods,
                "sections": sections,
                "maya_imported": True,
            }
            break
    save_data(data)


def fetch_news_for_company(company: dict, max_age_days: int | None = 7) -> list:
    try:
        import feedparser
        from time import mktime
    except ImportError:
        return []

    keywords = company.get("keywords", [])
    if not keywords:
        return []

    _tbs_map = {1: "qdr:d", 7: "qdr:w", 30: "qdr:m"}
    tbs_param = f"&tbs={_tbs_map[max_age_days]}" if max_age_days in _tbs_map else ""
    cutoff = datetime.now() - timedelta(days=max_age_days) if max_age_days else None

    seen_titles: set[str] = set()
    items = []

    for keyword in keywords:
        url = (
            f"https://news.google.com/rss/search?q={quote(keyword)}"
            f"{tbs_param}&hl=iw&gl=IL&ceid=IL:iw"
        )
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                published = entry.get("published_parsed")
                if published:
                    import calendar
                    ts_dt = datetime.fromtimestamp(calendar.timegm(published))
                    if cutoff and ts_dt < cutoff:
                        continue
                    ts = ts_dt.isoformat()
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
    return items[:15]


def format_timestamp(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        total_sec = (datetime.now() - dt).total_seconds()
        if total_sec < 0:
            return dt.strftime("%d/%m/%Y %H:%M")
        if total_sec < 60:
            return "עכשיו"
        if total_sec < 3600:
            return f"לפני {int(total_sec // 60)} דקות"
        if total_sec < 86400:
            return f"לפני {int(total_sec // 3600)} שעות"
        if total_sec < 172800:
            return "אתמול"
        if total_sec < 604800:
            return f"לפני {int(total_sec // 86400)} ימים"
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return ts
