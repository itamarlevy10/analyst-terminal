import html as _html
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

DATA_FILE = Path(__file__).parent.parent / "data" / "companies.json"
DEFAULT_FILE = Path(__file__).parent.parent / "data" / "default_data.json"

SOURCE_META = {
    "google":    {"label": "Google",    "color": "#B05E0D", "bg": "#FDF3E0", "icon": "🟠"},
    "reddit":    {"label": "Reddit",    "color": "#C0390A", "bg": "#FFF0EC", "icon": "🔴"},
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


def add_balance_sheet_extraction(data: dict, company_id: str, record: dict) -> dict:
    """Append a balance-sheet extraction record, keyed on (company, period_end,
    period_type). Never overwrites — an identical re-extraction is reported as
    'duplicate', a same-key-but-different-values extraction as 'conflict', so
    the caller can flag it for manual review instead of silently losing data."""
    company = get_company(data, company_id)
    if company is None:
        return {"status": "error", "message": f"company_id {company_id!r} not found"}

    extractions = company.setdefault("balance_sheet_extractions", [])
    key = (record.get("company"), record.get("period_end"), record.get("period_type"))

    for existing in extractions:
        existing_key = (existing.get("company"), existing.get("period_end"), existing.get("period_type"))
        if existing_key == key:
            if existing.get("fields") == record.get("fields"):
                return {"status": "duplicate", "existing": existing}
            return {"status": "conflict", "existing": existing, "incoming": record}

    extractions.append(record)
    save_data(data)
    return {"status": "added", "record": record}


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
        "competitor_keywords": [],
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


def add_feed_item(data: dict, company_id: str, source: str, title: str, url: str = "", notes: str = "", timestamp: str | None = None, snippet: str = "", matched_keyword: str = "", keyword_context: str = "") -> dict:
    item = {
        "id": str(uuid.uuid4())[:8],
        "source": source,
        "title": title,
        "url": url,
        "notes": notes,
        "snippet": snippet,
        "matched_keyword": matched_keyword,
        "keyword_context": keyword_context,
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


def add_keyword(data: dict, company_id: str, keyword: str, category: str = "company"):
    for c in data["companies"]:
        if c["id"] == company_id:
            if keyword not in c["keywords"]:
                c["keywords"].append(keyword)
            comp_kw = c.setdefault("competitor_keywords", [])
            if category == "competitor":
                if keyword not in comp_kw:
                    comp_kw.append(keyword)
            elif keyword in comp_kw:
                comp_kw.remove(keyword)
            break
    save_data(data)


def remove_keyword(data: dict, company_id: str, keyword: str):
    for c in data["companies"]:
        if c["id"] == company_id:
            c["keywords"] = [k for k in c["keywords"] if k != keyword]
            c["competitor_keywords"] = [k for k in c.get("competitor_keywords", []) if k != keyword]
            break
    save_data(data)


def get_avatar_info(company: dict, idx: int) -> tuple[str, str, str]:
    name = company["name"]
    initials = company.get("avatar") or "".join(w[0] for w in name.split()[:2]).upper()
    bg, fg = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
    bg = company.get("avatar_bg", bg)
    fg = company.get("avatar_fg", fg)
    return initials, bg, fg


def _find_keyword_context(title: str, snippet: str, keyword: str, window: int = 180) -> str:
    """Return a text excerpt (plain text) around the first match of keyword."""
    import re
    text = snippet if snippet else title
    m = re.search(re.escape(keyword), text, re.IGNORECASE)
    if not m:
        m = re.search(re.escape(keyword), title, re.IGNORECASE)
        if m:
            return title
        return ""
    start = max(0, m.start() - window // 2)
    end   = min(len(text), m.end() + window // 2)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return (prefix + text[start:end] + suffix).strip()


def fetch_news_for_company(company: dict, max_age_days: int | None = 7) -> list:
    try:
        import feedparser
        from time import mktime
    except ImportError:
        return []

    keywords = company.get("keywords", [])
    if not keywords:
        return []

    import re as _re
    import calendar

    _tbs_map = {1: "qdr:d", 7: "qdr:w", 30: "qdr:m"}
    tbs_param = f"&tbs={_tbs_map[max_age_days]}" if max_age_days in _tbs_map else ""
    cutoff = datetime.now() - timedelta(days=max_age_days) if max_age_days else None

    seen_titles: set[str] = set()
    items = []

    def _is_hebrew(s: str) -> bool:
        return any('א' <= c <= 'ת' for c in s)

    # Search both Israeli Hebrew edition AND global English edition
    def _edition_urls(kw: str) -> list[str]:
        q = quote(kw)
        urls = [f"https://news.google.com/rss/search?q={q}{tbs_param}&hl=en&gl=US&ceid=US:en"]
        if _is_hebrew(kw):
            urls.append(f"https://news.google.com/rss/search?q={q}{tbs_param}&hl=iw&gl=IL&ceid=IL:iw")
        else:
            # Also search Israeli edition for English keywords (Israeli companies get Hebrew coverage)
            urls.append(f"https://news.google.com/rss/search?q={q}{tbs_param}&hl=iw&gl=IL&ceid=IL:iw")
        return urls

    from concurrent.futures import ThreadPoolExecutor

    fetch_jobs = [(kw, url) for kw in keywords for url in _edition_urls(kw)]

    def _fetch_one(job):
        keyword, url = job
        try:
            return keyword, feedparser.parse(url).entries
        except Exception:
            return keyword, []

    with ThreadPoolExecutor(max_workers=min(12, len(fetch_jobs) or 1)) as pool:
        fetched = list(pool.map(_fetch_one, fetch_jobs))

    # Process sequentially (in keyword order) so dedup/ordering stays deterministic.
    for keyword, entries in fetched:
        for entry in entries:
            title = entry.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            published = entry.get("published_parsed")
            if published:
                ts_dt = datetime.fromtimestamp(calendar.timegm(published))
                if cutoff and ts_dt < cutoff:
                    continue
                ts = ts_dt.isoformat()
            else:
                ts = datetime.now().isoformat()
            raw_summary = entry.get("summary", "") or entry.get("description", "")
            snippet = _html.unescape(_re.sub(r'<[^>]+>', '', raw_summary).strip())[:300] if raw_summary else ""
            items.append({
                "title": title,
                "url": entry.get("link", ""),
                "timestamp": ts,
                "snippet": snippet,
                "matched_keyword": keyword,
                "keyword_context": _find_keyword_context(title, snippet, keyword),
            })

    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items[:60]


def add_scan_source(data: dict, company_id: str, url: str):
    for c in data["companies"]:
        if c["id"] == company_id:
            sources = c.setdefault("scan_sources", [])
            if url not in sources:
                sources.append(url)
            break
    save_data(data)


def remove_scan_source(data: dict, company_id: str, url: str):
    for c in data["companies"]:
        if c["id"] == company_id:
            c["scan_sources"] = [u for u in c.get("scan_sources", []) if u != url]
            break
    save_data(data)


def _reddit_oauth_token(client_id: str, client_secret: str, user_agent: str) -> str | None:
    import requests
    try:
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": user_agent},
            timeout=8,
        )
        return r.json().get("access_token") if r.ok else None
    except Exception:
        return None


def fetch_reddit_for_company(company: dict, max_age_days: int | None = 7,
                              reddit_client_id: str | None = None,
                              reddit_client_secret: str | None = None) -> list:
    try:
        import requests
        import feedparser
        import re
        import time
        import calendar
    except ImportError:
        return []

    keywords = company.get("keywords", [])
    if not keywords:
        return []

    _t_map = {1: "day", 7: "week", 30: "month"}
    t_param = _t_map.get(max_age_days, "year") if max_age_days else "all"
    cutoff = datetime.now() - timedelta(days=max_age_days) if max_age_days else None
    ua = "analyst-terminal/1.0 (analyst research tool)"

    session = requests.Session()
    session.headers.update({"User-Agent": ua})

    token = None
    if reddit_client_id and reddit_client_secret:
        token = _reddit_oauth_token(reddit_client_id, reddit_client_secret, ua)

    if token:
        # OAuth apps get a much higher rate limit (~100 req/min) — safe to
        # hit every keyword concurrently.
        def _fetch_oauth(keyword):
            url = f"https://oauth.reddit.com/search?q={quote(keyword)}&sort=new&t={t_param}&limit=25&raw_json=1"
            try:
                r = session.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=8)
                if not r.ok:
                    return keyword, []
                posts = []
                for child in r.json().get("data", {}).get("children", []):
                    d = child.get("data", {})
                    permalink = d.get("permalink", "")
                    posts.append({
                        "title": d.get("title", ""),
                        "url": f"https://www.reddit.com{permalink}" if permalink else d.get("url", ""),
                        "created_epoch": d.get("created_utc"),
                        "body": d.get("selftext", ""),
                        "subreddit": d.get("subreddit", ""),
                    })
                return keyword, posts
            except Exception:
                return keyword, []

        from concurrent.futures import ThreadPoolExecutor
        jobs = keywords[:8]
        with ThreadPoolExecutor(max_workers=min(6, len(jobs) or 1)) as pool:
            fetched = list(pool.map(_fetch_oauth, jobs))
    else:
        # No API credentials: fall back to the anonymous RSS endpoint, which
        # allows only ~1 request per ~45-60s per IP (verified live — every
        # request past the first 429s immediately). Firing these concurrently
        # or with a short retry just burns the budget on failures, so this
        # runs strictly sequentially and waits out the real reset window
        # reported by Reddit, capped to just the 2 highest-value keywords
        # (the company itself + its primary competitor) to keep total wait
        # time reasonable.
        def _fetch_rss(keyword):
            url = f"https://www.reddit.com/search.rss?q={quote(keyword)}&sort=new&t={t_param}&limit=25"
            try:
                r = session.get(url, timeout=8)
                if r.status_code == 429:
                    return [], int(r.headers.get("x-ratelimit-reset", "45") or 45)
                if not r.ok:
                    return [], 0
                posts = []
                for entry in feedparser.parse(r.content).entries:
                    subreddit = ""
                    if entry.get("tags"):
                        subreddit = entry["tags"][0].get("term", "").strip()
                    posts.append({
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "published_parsed": entry.get("published_parsed"),
                        "body": entry.get("summary", ""),
                        "subreddit": subreddit,
                    })
                return posts, 0
            except Exception:
                return [], 0

        # Use two company-side keywords, never a competitor — a well-known
        # competitor's own name (e.g. "Anduril") is so widely discussed on
        # Reddit that it drowns the feed in generic unrelated noise, not
        # anything about this company specifically. Also skip short all-caps
        # tickers (e.g. "NXSN") when a better alternative exists — verified
        # those mostly match random unrelated posts too.
        competitor_kws = set(company.get("competitor_keywords", []))
        company_side_kws = [k for k in keywords if k not in competitor_kws]
        non_ticker = [k for k in company_side_kws if not re.match(r'^[A-Z]{2,6}$', k)]
        ordered = non_ticker + [k for k in company_side_kws if k not in non_ticker]
        jobs = ordered[:2]
        if not jobs:
            jobs = keywords[:2]

        fetched = []
        for i, keyword in enumerate(jobs):
            posts, wait_s = _fetch_rss(keyword)
            if not posts and wait_s:
                time.sleep(min(wait_s + 1, 65))
                posts, _ = _fetch_rss(keyword)
            fetched.append((keyword, posts))

    seen_titles: set[str] = set()
    items = []
    for keyword, posts in fetched:
        for p in posts:
            title = (p.get("title") or "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            if p.get("created_epoch"):
                ts_dt = datetime.fromtimestamp(p["created_epoch"])
            elif p.get("published_parsed"):
                ts_dt = datetime.fromtimestamp(calendar.timegm(p["published_parsed"]))
            else:
                ts_dt = datetime.now()
            if cutoff and ts_dt < cutoff:
                continue
            ts = ts_dt.isoformat()

            raw_body = p.get("body", "")
            body = _html.unescape(re.sub(r"<[^>]+>", " ", raw_body).strip())
            body = re.sub(r"\s+", " ", body)[:300]
            subreddit = p.get("subreddit", "")
            snippet = body if body else f"r/{subreddit}"

            # Skip results where the keyword doesn't actually appear in title or body
            if keyword.lower() not in (title + " " + body).lower():
                continue

            items.append({
                "title": title,
                "url": p.get("url", ""),
                "timestamp": ts,
                "snippet": snippet,
                "subreddit": subreddit,
                "matched_keyword": keyword,
                "keyword_context": _find_keyword_context(title, snippet, keyword),
            })

    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items[:40]


def _resolve_feed_entries(source_url: str, feedparser) -> tuple[list, str]:
    """Return (entries, resolved_url). Tries RSS auto-discovery if direct parse yields nothing."""
    import re
    import requests
    from urllib.parse import urljoin, urlparse

    _ua = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    def _try(url: str):
        try:
            resp = requests.get(url, headers=_ua, timeout=8)
            ct = resp.headers.get("content-type", "").lower()
            if resp.ok and any(x in ct for x in ("xml", "rss", "atom")):
                f = feedparser.parse(resp.content)
                if f.entries:
                    return f.entries
        except Exception:
            pass
        try:
            f = feedparser.parse(url)
            if f.entries:
                return f.entries
        except Exception:
            pass
        return None

    entries = _try(source_url)
    if entries:
        return entries, source_url

    parsed = urlparse(source_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Discover RSS links from the page HTML
    try:
        resp = requests.get(source_url, headers=_ua, timeout=8)
        if resp.ok and "html" in resp.headers.get("content-type", "").lower():
            discovered = re.findall(
                r'href=["\']([^"\']*(?:rss|feed|atom)[^"\']*)["\']',
                resp.text, re.IGNORECASE,
            )
            for link in discovered[:5]:
                candidate = urljoin(base, link)
                if candidate != source_url:
                    entries = _try(candidate)
                    if entries:
                        return entries, candidate
    except Exception:
        pass

    # Try common RSS path patterns
    for path in ["/rss/", "/rss", "/misc/rss", "/feed/", "/feed",
                 "/rss.xml", "/atom.xml", "/feeds/all.rss"]:
        candidate = urljoin(base, path)
        entries = _try(candidate)
        if entries:
            return entries, candidate

    return [], source_url


def fetch_from_source_urls(company: dict, max_age_days: int | None = 7) -> list:
    try:
        import feedparser
        import re
        import calendar
        from urllib.parse import urlparse
    except ImportError:
        return []

    scan_sources = company.get("scan_sources", [])
    if not scan_sources:
        return []

    keywords = company.get("keywords", [])
    cutoff = datetime.now() - timedelta(days=max_age_days) if max_age_days else None
    seen_titles: set[str] = set()
    items = []

    for source_url in scan_sources:
        try:
            domain = urlparse(source_url).netloc.replace("www.", "") or source_url[:30]
            entries, _ = _resolve_feed_entries(source_url, feedparser)
            for entry in entries:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                published = entry.get("published_parsed")
                if published:
                    ts_dt = datetime.fromtimestamp(calendar.timegm(published))
                    if cutoff and ts_dt < cutoff:
                        continue
                    ts = ts_dt.isoformat()
                else:
                    ts = datetime.now().isoformat()
                raw_summary = entry.get("summary", "") or entry.get("description", "")
                snippet = _html.unescape(re.sub(r'<[^>]+>', '', raw_summary).strip())[:300] if raw_summary else ""

                # Only keep items that actually mention one of the tracked keywords —
                # a source like a general news homepage publishes mostly unrelated
                # articles, so unfiltered inclusion buried real matches in noise.
                search_text = (title + " " + snippet).lower()
                matched_kw = next((kw for kw in keywords if kw.lower() in search_text), "")
                if not matched_kw:
                    continue

                seen_titles.add(title)
                keyword_ctx = _find_keyword_context(title, snippet, matched_kw)
                items.append({
                    "title": title,
                    "url": entry.get("link", ""),
                    "timestamp": ts,
                    "snippet": snippet,
                    "source_domain": domain,
                    "matched_keyword": matched_kw,
                    "keyword_context": keyword_ctx,
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
