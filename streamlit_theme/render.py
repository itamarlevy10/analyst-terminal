"""
חצבים — Terminal Light · iframe renderer.

הרעיון: כל טאב מרונדר כ-*מסמך HTML שלם* בתוך st.components.v1.html (iframe).
בתוך iframe ה-CSS של Streamlit לא מגיע — אז זה נראה בדיוק כמו המוקאפ.

ניווט + טפסים עובדים דרך ה-iframe:
  • לינקים: <a target="_top" href="?co=..&tab=..">  → מעדכן query params של האפליקציה → rerun.
  • טפסים: <form method="get" target="_top">         → שדות הקלדה זורמים ל-st.query_params.

ב-app.py קוראים st.query_params, משנים את הדאטה, ואז components.html(page_html(...), height=...).
ראה USAGE ב-README.md.
"""
from datetime import datetime
from html import escape

# ── פלטה מונוכרומטית ────────────────────────────────────────────
P = {
    "bg": "#EEF1F5", "panel": "#FFFFFF", "stat": "#F7F8FA",
    "border": "#E6EAF0", "border_str": "#DDE3EA",
    "ink": "#1B2027", "sec": "#5A6675", "muted": "#94A0AF",
    "accent": "#232B36", "accent_bg": "#EDEFF2",
    "ribbon": "#1B2027", "up": "#137A4B", "down": "#C32D2D",
    "kw_co": "#1F7A4D", "kw_comp": "#C0392B",
}
SOURCE_META = {
    "google":   {"label": "Google",   "color": "#B45309", "bg": "#FBF1E0"},
    "maya":     {"label": "מאיה",      "color": "#5B4FC9", "bg": "#ECEAFB"},
    "linkedin": {"label": "LinkedIn",  "color": "#0A66C2", "bg": "#E5F0FB"},
    "x":        {"label": "X",        "color": "#000000", "bg": "#EDEDED"},
    "manual":   {"label": "ידני",      "color": "#1F7A4D", "bg": "#E6F3EC"},
    "reddit":   {"label": "Reddit",    "color": "#C0390A", "bg": "#FFF0EC"},
    "other":    {"label": "אחר",       "color": "#555555", "bg": "#F2F2F2"},
}
DEFAULT_COMPETITORS = {"anduril", "uvision", "אנדוריל"}


def classify_keyword(kw, competitors=DEFAULT_COMPETITORS):
    return "competitor" if kw.strip().lower() in competitors else "company"


# ── helpers ─────────────────────────────────────────────────────
_CURRENCY_SYMBOLS = {"USD": "$", "ILS": "₪"}

def money_M(x, currency="ILS", units="thousands"):
    try:
        symbol = _CURRENCY_SYMBOLS.get(currency, currency + " ")
        scaled = x / 1000 if units == "thousands" else x
        return f"{symbol}{scaled:.1f}M"
    except Exception:
        return "—"

def _time(ts):
    try:
        d = datetime.fromisoformat(ts)
        return d.strftime("%H:%M") if d.date() == datetime.now().date() else d.strftime("%d.%m")
    except: return ""

def _e(s):  # escape user text
    return escape(str(s)) if s is not None else ""

def _qs(**kw):
    from urllib.parse import quote
    return "?" + "&".join(f"{k}={quote(str(v))}" for k, v in kw.items() if v is not None)


# ── <head> + base styles (inline, iframe-isolated) ──────────────
_HEAD = """<!doctype html><html dir="rtl" lang="he"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;}
html,body{margin:0;padding:0;background:%(bg)s;font-family:'Heebo','Segoe UI',sans-serif;-webkit-font-smoothing:antialiased;color:%(ink)s;}
a{text-decoration:none;color:inherit;}
.mono{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;}
.wrap{max-width:1480px;margin:0 auto;padding:14px;}
::-webkit-scrollbar{width:9px;height:9px;}::-webkit-scrollbar-thumb{background:rgba(0,0,0,.16);border-radius:99px;}
input,select,textarea{font-family:'Heebo',sans-serif;}
a.feed-title:hover{text-decoration:underline;}
@keyframes spin{to{transform:rotate(360deg)}}
.spinner{display:inline-block;width:13px;height:13px;border:2px solid rgba(255,255,255,.35);border-top-color:#fff;border-radius:50%%;animation:spin .7s linear infinite;vertical-align:-2px}
</style></head><body><div class="wrap">""" % P

_FOOT = "</div></body></html>"


# ── building blocks ─────────────────────────────────────────────
def _topbar(b64):
    img = (f'<img src="data:image/png;base64,{b64}" style="width:21px;height:21px;object-fit:contain">'
           if b64 else "ח")
    return f"""<div style="display:flex;align-items:center;justify-content:space-between;padding:0 18px;height:52px;background:{P['panel']};border:1px solid {P['border']};border-radius:10px;margin-bottom:8px">
<div style="display:flex;align-items:center;gap:11px">
<span style="width:32px;height:32px;border-radius:9px;background:#fff;border:1px solid {P['border_str']};display:flex;align-items:center;justify-content:center;overflow:hidden">{img}</span>
<span style="font-size:17px;font-weight:800">חצבים</span>
<span style="font-size:12px;color:{P['muted']};letter-spacing:.05em">RESEARCH&nbsp;TERMINAL</span></div>
<div class="mono" style="font-size:12px;color:{P['sec']}">{datetime.now().strftime('%H:%M')}&nbsp;IL</div></div>"""


def _strip(companies, active_id, tab):
    pills = []
    for co in companies:
        on = co["id"] == active_id
        bb = f"border-bottom:2px solid {P['accent']};" if on else ""
        tkc = P['ink'] if on else P['muted']
        nmc = P['ink'] if on else P['sec']
        nmw = "700" if on else "400"
        pills.append(
            f'<a target="_top" href="{_qs(co=co["id"], tab=tab)}" style="display:flex;align-items:center;gap:7px;padding:11px 16px;border-inline-start:1px solid {P["bg"]};{bb}">'
            f'<span class="mono" style="font-weight:600;font-size:13px;color:{tkc}">{_e(co.get("ticker",""))}</span>'
            f'<span style="font-size:13.5px;color:{nmc};font-weight:{nmw}">{_e(co["name"])}</span></a>')
    pills.append(f'<a target="_top" href="{_qs(co=active_id, tab=tab, add_co=1)}" style="display:flex;align-items:center;padding:11px 16px;border-inline-start:1px solid {P["bg"]};color:{P["muted"]};font-size:13px;cursor:pointer">+ הוסף</a>')
    return f'<div style="display:flex;background:{P["panel"]};border:1px solid {P["border"]};border-radius:10px;overflow:hidden">{"".join(pills)}</div>'


def _tabs(active, co_id):
    out = []
    for t, lbl in [("feed", "📰 פיד מידע"), ("fin", "📊 דוחות כספיים"), ("settings", "⚙️ הגדרות")]:
        on = t == active
        c = P['ink'] if on else P['muted']
        bar = f'<span style="position:absolute;bottom:-1px;right:8px;left:8px;height:2px;background:{P["accent"]};border-radius:2px"></span>' if on else ""
        out.append(f'<a target="_top" href="{_qs(co=co_id, tab=t)}" style="position:relative;padding:9px 15px 12px;font-size:13.5px;font-weight:700;color:{c}">{lbl}{bar}</a>')
    return (f'<div style="display:flex;gap:4px;padding:6px 4px 0">{"".join(out)}</div>'
            f'<div style="height:1px;background:{P["border_str"]}"></div>')


def _kpi(bs_kpis):
    """Ribbon of headline balance-sheet figures. bs_kpis comes from
    utils.build_balance_sheet.latest_balance_sheet_kpis() — None when nothing
    has been imported yet, in which case the ribbon renders empty (no
    placeholder numbers), not hidden entirely."""
    if not bs_kpis:
        return f'<div style="background:{P["ribbon"]};border-radius:10px;padding:11px 8px;margin:8px 0;min-height:20px"></div>'
    currency = bs_kpis.get("currency", "ILS")
    units = bs_kpis.get("units", "thousands")
    def cell(c):
        val = f"{c['value']*100:.1f}%" if c["is_percent"] else money_M(c["value"], currency, units)
        p = c["pct_change"]
        up = f'<span class="mono" style="font-size:11px;color:#5ee0a0">{p:+.0f}%</span>' if p is not None else ""
        return (f'<div style="display:flex;align-items:baseline;gap:8px;padding:0 18px;border-inline-start:1px solid rgba(255,255,255,.1)">'
                f'<span style="font-size:11px;color:#8a93a3">{_e(c["label"])}</span>'
                f'<span class="mono" style="font-size:14px;font-weight:600;color:#fff">{val}</span>{up}</div>')
    period_tag = (f'<div style="padding:0 18px;font-size:11px;color:#8a93a3">נכון ל-'
                  f'<span class="mono" style="color:#fff">{_e(bs_kpis["period_label"])}</span></div>')
    inner = period_tag + "".join(cell(c) for c in bs_kpis["cells"])
    return f'<div style="display:flex;align-items:center;background:{P["ribbon"]};border-radius:10px;padding:11px 8px;margin:8px 0">{inner}</div>'


def _filters(co_id, active_src):
    out = [f'<span style="font-size:12px;color:{P["muted"]};margin-inline-end:2px">מקור:</span>']
    for k in ["google", "reddit", "maya", "linkedin", "x", "manual"]:
        m = SOURCE_META[k]; on = k in active_src
        new = (active_src - {k}) if on else (active_src | {k})
        dim = "" if on else "opacity:.4;filter:grayscale(.4);"
        out.append(f'<a target="_top" href="{_qs(co=co_id, tab="feed", src=",".join(sorted(new)))}" '
                   f'style="font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:5px;background:{m["bg"]};color:{m["color"]};{dim}">{m["label"]}</a>')
    return f'<div style="display:flex;align-items:center;gap:7px;padding:11px 0;border-bottom:1px solid {P["border_str"]}">{"".join(out)}</div>'


def _feed_row(it, classify):
    from urllib.parse import quote as _q
    m = SOURCE_META.get(it.get("source", "other"), SOURCE_META["other"])
    kw = it.get("matched_keyword", "")
    kwc = (P['kw_comp'], '#FCEAEA', 'rgba(192,57,43,.25)') if (kw and classify(kw) == "competitor") else (P['kw_co'], '#E6F3EC', 'rgba(31,122,77,.25)')
    kw_html = (f'<span style="font-size:11px;padding:2px 8px;border-radius:99px;background:{kwc[1]};color:{kwc[0]};border:1px solid {kwc[2]}">🔑 {_e(kw)}</span>') if kw else ""
    _url = it.get("url", "")
    _title = it.get("title", "")
    if _url:
        title_el = (
            f'<a class="feed-title" href="{_e(_url)}" target="_blank" rel="noopener" '
            f'style="color:{P["ink"]};text-decoration:none;font-size:14px;font-weight:700;line-height:1.45;display:block">'
            f'{_e(_title)}</a>'
        )
    else:
        title_el = f'<div style="font-size:14px;font-weight:700;line-height:1.45">{_e(_title)}</div>'
    # Fallback for links a publisher blocks directly (captcha/paywall bot-walls) — a
    # Google search for the exact headline almost always finds it (or a mirror).
    search_html = ""
    if _title:
        search_url = f'https://www.google.com/search?q={_q(chr(34) + _title + chr(34))}'
        search_html = (f'<a href="{_e(search_url)}" target="_blank" rel="noopener" '
                       f'style="font-size:11px;color:{P["muted"]};white-space:nowrap">🔎 אם הקישור לא עובד — חפש</a>')
    return (
        f'<div style="display:flex;gap:13px;padding:12px 2px;border-bottom:1px solid {P["border"]}">'
        f'<div style="flex:0 0 70px;display:flex;flex-direction:column;gap:5px;align-items:flex-start">'
        f'<span style="font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:5px;background:{m["bg"]};color:{m["color"]}">{m["label"]}</span>'
        f'<span class="mono" style="font-size:11px;color:{P["muted"]}">{_time(it.get("timestamp",""))}</span></div>'
        f'<div style="flex:1;min-width:0">'
        f'{title_el}'
        f'<div style="font-size:12.5px;color:{P["sec"]};margin-top:3px;line-height:1.5">{_e(it.get("snippet",""))[:200]}</div>'
        f'<div style="display:flex;gap:8px;margin-top:6px;align-items:center">{kw_html}'
        f'<span class="mono" style="font-size:11px;color:{P["muted"]}">{_e(it.get("source_label",""))}</span>'
        f'<span style="margin-inline-start:auto">{search_html}</span></div></div></div>')


def _feed_section(label, color, bg, items, classify):
    count = f'<span class="mono" style="font-size:11px;color:{P["muted"]};margin-inline-start:2px">{len(items)}</span>'
    header = (
        f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:2px">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:{color}"></span>'
        f'<span style="font-size:12.5px;font-weight:800;color:{color}">{label}</span>{count}</div>')
    if items:
        body = "".join(_feed_row(it, classify) for it in items)
    else:
        body = f'<div style="padding:16px 4px;color:{P["muted"]};font-size:12.5px">אין פריטים בקטגוריה זו</div>'
    return (f'<div style="background:{bg};border-radius:9px;padding:12px 12px 2px;margin-bottom:14px">'
            f'{header}<div>{body}</div></div>')


def _feed(items, classify):
    if not items:
        return (f'<div style="text-align:center;padding:48px 16px;color:{P["muted"]}">'
                f'<div style="font-size:40px">📭</div><div style="font-size:15px;font-weight:600;margin-top:8px">הפיד ריק</div></div>')
    co_items   = [it for it in items if classify(it.get("matched_keyword", "")) != "competitor"]
    comp_items = [it for it in items if classify(it.get("matched_keyword", "")) == "competitor"]
    return (
        _feed_section("החברה ומוצריה", P['kw_co'], '#F4FAF7', co_items, classify) +
        _feed_section("מתחרות וסביבה", P['kw_comp'], '#FDF6F5', comp_items, classify)
    )


def _rail(co_id, keywords, sources, last_scan, classify, age="all", scanning=False):
    co = [k for k in keywords if classify(k) == "company"]
    comp = [k for k in keywords if classify(k) == "competitor"]
    def chips(items, color, bg, bdr):
        out = []
        for k in items:
            out.append(f'<span style="display:inline-flex;align-items:center;gap:5px;border-radius:99px;padding:3px 9px;font-size:11.5px;margin:2px 0;background:{bg};color:{color};border:1px solid {bdr}">{_e(k)}'
                       f'<a target="_top" href="{_qs(co=co_id, tab="feed", del_kw=k)}" style="font-size:10px;opacity:.6">✕</a></span>')
        return " ".join(out)
    src = "".join(f'<div style="display:flex;align-items:center;gap:7px;font-size:12px;color:{P["sec"]};padding:6px 10px;background:{P["stat"]};border:1px solid {P["border"]};border-radius:7px;margin-top:6px">🔗 {_e(s)}</div>' for s in sources)
    age_pills = "".join(
        f'<a target="_top" href="{_qs(co=co_id, tab="feed", age=val)}" '
        f'style="font-size:11px;font-weight:600;padding:3px 10px;border-radius:5px;'
        f'background:{""+P["accent"] if age==val else P["stat"]};'
        f'color:{"#fff" if age==val else P["sec"]};'
        f'border:1px solid {P["border_str"]}">{lbl}</a>'
        for lbl, val in [("הכל","all"),("יום","1"),("שבוע","7"),("חודש","30")]
    )
    if scanning:
        scan_btn = (f'<div style="display:flex;align-items:center;justify-content:center;gap:8px;'
                    f'background:{P["accent"]};color:#fff;border-radius:7px;padding:8px;font-size:13px;font-weight:700;opacity:.85">'
                    f'<span class="spinner"></span>סורק…</div>')
    else:
        scan_btn = (f'<a target="_top" href="{_qs(co=co_id, tab="feed", scan=1, age=age)}" '
                    f'style="display:block;text-align:center;background:{P["accent"]};color:#fff;border-radius:7px;padding:8px;font-size:13px;font-weight:700">↻ סרוק עכשיו</a>')
    return f"""<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
<span style="font-size:12.5px;font-weight:700">סריקה</span><span class="mono" style="font-size:10.5px;color:{P['muted']}">{_e(last_scan)}</span></div>
<div style="display:flex;gap:5px;margin-bottom:8px">{age_pills}</div>
{scan_btn}
<div style="display:flex;align-items:center;gap:7px;font-size:11.5px;font-weight:700;margin:15px 0 8px;color:{P['kw_co']}"><span style="width:8px;height:8px;border-radius:50%;background:{P['kw_co']}"></span>החברה ומוצריה<span class="mono" style="margin-inline-start:auto;color:{P['muted']}">{len(co)}</span></div>
<div>{chips(co, P['kw_co'], '#E6F3EC', 'rgba(31,122,77,.25)')}</div>
<div style="display:flex;align-items:center;gap:7px;font-size:11.5px;font-weight:700;margin:15px 0 8px;color:{P['kw_comp']}"><span style="width:8px;height:8px;border-radius:50%;background:{P['kw_comp']}"></span>מתחרות וסביבה<span class="mono" style="margin-inline-start:auto;color:{P['muted']}">{len(comp)}</span></div>
<div>{chips(comp, P['kw_comp'], '#FCEAEA', 'rgba(192,57,43,.25)')}</div>
<form method="get" target="_top" style="display:flex;gap:6px;margin-top:11px">
<input type="hidden" name="co" value="{_e(co_id)}"><input type="hidden" name="tab" value="feed">
<input name="add_kw" placeholder="הוסף מילת מפתח…" style="flex:1;min-width:0;height:30px;border:1px solid {P['border_str']};border-radius:7px;padding:0 10px;font-size:12px;color:{P['ink']};background:#fff">
<select name="add_kw_cat" style="height:30px;border:1px solid {P['border_str']};border-radius:7px;padding:0 4px;font-size:11px;color:{P['sec']};background:#fff">
<option value="company">חברה</option><option value="competitor">מתחרה</option></select>
<button style="height:30px;padding:0 12px;border:1px solid {P['border_str']};border-radius:7px;background:#fff;color:{P['sec']};font-size:12px;font-weight:600;cursor:pointer">+</button></form>
<div style="font-size:11px;color:{P['muted']};margin-top:15px">מקורות נוספים · {len(sources)}</div>{src}"""


def _add_manual(co_id):
    return f"""<details style="margin:8px 0 4px">
<summary style="list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 13px;border:1px solid {P['border_str']};border-radius:7px;background:#fff;color:{P['accent']};font-size:12.5px;font-weight:700">➕ הוסף דיווח ידני</summary>
<form method="get" target="_top" style="margin-top:10px;padding:14px;background:{P['stat']};border:1px solid {P['border_str']};border-radius:10px">
<input type="hidden" name="co" value="{_e(co_id)}"><input type="hidden" name="tab" value="feed">
<div style="font-size:12.5px;font-weight:700;margin-bottom:10px">דיווח ידני חדש</div>
<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px">
<select name="m_src" style="height:34px;padding:0 10px;border:1px solid {P['border_str']};border-radius:7px;background:#fff;font-size:13px">
<option value="manual">ידני</option><option value="maya">מאיה / TASE</option><option value="google">Google</option><option value="linkedin">LinkedIn</option><option value="x">X</option></select>
<input name="m_url" placeholder="קישור (אופציונלי)" style="flex:1;min-width:160px;height:34px;padding:0 12px;border:1px solid {P['border_str']};border-radius:7px;background:#fff;font-size:13px"></div>
<textarea name="m_title" placeholder="מה גילית? כותרת / תיאור…" style="width:100%;min-height:64px;padding:10px 12px;border:1px solid {P['border_str']};border-radius:7px;background:#fff;font-size:13px;resize:vertical"></textarea>
<input name="m_notes" placeholder="הערות (אופציונלי)" style="width:100%;height:34px;margin-top:8px;padding:0 12px;border:1px solid {P['border_str']};border-radius:7px;background:#fff;font-size:13px">
<div style="margin-top:10px"><button style="height:34px;padding:0 18px;border:none;border-radius:7px;background:{P['accent']};color:#fff;font-size:13px;font-weight:700;cursor:pointer">➕ הוסף לפיד</button></div>
</form></details>"""


# ════════════ הפונקציה הראשית — מסמך מלא לטאב ════════════
def page_html(tab, companies, active_id, company, bs_kpis,
              feed_items, active_src, last_scan="", b64="", age="all",
              classify=classify_keyword, scanning=False):
    """מחזיר מסמך HTML שלם להעברה ל-st.components.v1.html(page_html(...), height=...)."""
    parts = [_HEAD, _topbar(b64), _strip(companies, active_id, tab), _tabs(tab, active_id)]
    if tab == "feed":
        parts.append(_kpi(bs_kpis))
        parts.append('<div style="display:flex;gap:18px;align-items:flex-start;margin-top:4px">')
        parts.append(f'<div style="flex:1;min-width:0;background:{P["panel"]};border:1px solid {P["border"]};border-radius:10px;padding:6px 18px 18px">')
        parts.append(_add_manual(active_id))
        parts.append(_filters(active_id, active_src))
        parts.append(_feed(feed_items, classify))
        parts.append('</div>')
        parts.append(f'<div style="flex:0 0 296px;background:{P["panel"]};border:1px solid {P["border"]};border-radius:10px;padding:16px 18px">')
        parts.append(_rail(active_id, company.get("keywords", []), company.get("scan_sources", []), last_scan, classify, age=age, scanning=scanning))
        parts.append('</div></div>')
    parts.append(_FOOT)
    return "".join(parts)
