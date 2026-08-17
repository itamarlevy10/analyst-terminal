"""
Analyst Terminal — דאשבורד אנליסט
שכבת תצוגה: streamlit_theme/render.py (iframe)
שכבת נתונים: utils/data_manager.py
"""
import json
import uuid
from datetime import datetime, timedelta

import streamlit as st
import streamlit.components.v1 as components

from streamlit_theme import render as R
from utils.data_manager import (
    load_data, save_data, get_companies, get_company,
    add_company, delete_company,
    add_feed_item, delete_feed_item,
    add_keyword, remove_keyword,
    fetch_news_for_company,
    add_scan_source, remove_scan_source, fetch_from_source_urls,
    fetch_reddit_for_company,
)

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Analyst Terminal — דאשבורד אנליסט",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    "<style>#MainMenu,footer,[data-testid='stHeader']{display:none}"
    ".block-container{padding:1rem 1.2rem;max-width:1520px}</style>",
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = load_data()
if "scan_results" not in st.session_state:
    st.session_state.scan_results = {}
if "last_scan_times" not in st.session_state:
    st.session_state.last_scan_times = {}

data      = st.session_state.data
companies = get_companies(data)

# ── Query params ──────────────────────────────────────────────
qp        = st.query_params
active_id = qp.get("co") or (companies[0]["id"] if companies else None)
tab       = qp.get("tab", "feed")
age       = qp.get("age", "all")
src_str   = qp.get("src", "google,maya,reddit,manual,other")
active_src = set(src_str.split(",")) if src_str else {"google", "maya", "reddit", "manual", "other"}

def _clear(*keys):
    for k in keys:
        if k in qp:
            del qp[k]

# ── Actions from query params (fired by iframe links/forms) ───

# Add company (from "+ הוסף" link in company strip)
if qp.get("add_co") and qp.get("ac_name") and qp["ac_name"].strip():
    _name   = qp["ac_name"].strip()
    _ticker = qp.get("ac_ticker", "").strip()
    _kws    = [k.strip() for k in qp.get("ac_kw", "").split(",") if k.strip()]
    new_co  = add_company(data, _name, _ticker, _kws)
    st.session_state.data = load_data()
    _clear("add_co", "ac_name", "ac_ticker", "ac_kw")
    qp["co"]  = new_co["id"]
    qp["tab"] = "feed"
    st.rerun()

if qp.get("del_kw"):
    remove_keyword(data, active_id, qp["del_kw"])
    save_data(data)
    st.session_state.data = load_data()
    _clear("del_kw")
    st.rerun()

if qp.get("del_item"):
    item_id = qp["del_item"]
    co_obj  = get_company(data, active_id)
    if co_obj:
        persistent_ids = {f["id"] for f in co_obj.get("feeds", [])}
        if item_id in persistent_ids:
            delete_feed_item(data, active_id, item_id)
        else:
            sr = st.session_state.scan_results
            sr[active_id] = [f for f in sr.get(active_id, []) if f["id"] != item_id]
    _clear("del_item")
    st.rerun()

if qp.get("add_kw"):
    add_keyword(data, active_id, qp["add_kw"].strip(), category=qp.get("add_kw_cat", "company"))
    save_data(data)
    st.session_state.data = load_data()
    _clear("add_kw", "add_kw_cat")
    st.rerun()

if qp.get("m_title"):
    add_feed_item(
        data, active_id,
        source=qp.get("m_src", "manual"),
        title=qp["m_title"].strip(),
        url=qp.get("m_url", ""),
        notes=qp.get("m_notes", ""),
    )
    save_data(data)
    st.session_state.data = load_data()
    _clear("m_title", "m_src", "m_url", "m_notes")
    st.rerun()

# Scanning is flagged here but the slow network fetches run further below,
# AFTER the dashboard iframe has already been sent to the browser — so the
# user keeps seeing the full page (with a spinner in the rail) instead of a
# blank screen while Google/Reddit/custom sources are queried.
scanning = bool(qp.get("scan"))

# ── Active company ────────────────────────────────────────────
data      = st.session_state.data
companies = get_companies(data)
company   = get_company(data, active_id)

if not company:
    st.info("לא נמצאה חברה.")
    with st.expander("➕ הוסף חברה", expanded=True):
        ac_name   = st.text_input("שם החברה", placeholder="Mobileye")
        ac_ticker = st.text_input("טיקר", placeholder="MBLY")
        ac_kw     = st.text_input("מילות מפתח", placeholder="MBLY, Mobileye")
        if st.button("הוסף", type="primary"):
            if ac_name.strip():
                kws = [k.strip() for k in ac_kw.split(",") if k.strip()]
                co  = add_company(data, ac_name.strip(), ac_ticker.strip(), kws)
                qp["co"] = co["id"]
                st.rerun()
    st.stop()

# ── Classify function ─────────────────────────────────────────
# A keyword is "competitor" only if it was explicitly tagged as such when
# added (company.competitor_keywords) — everything else (ticker, company
# name, and the company's own products) defaults to "company".
_competitor_kw = {k.strip().lower() for k in company.get("competitor_keywords", [])}

def classify(kw: str) -> str:
    return "competitor" if kw.strip().lower() in _competitor_kw else "company"

# ── Last scan label ───────────────────────────────────────────
def _last_scan_label():
    ts = st.session_state.last_scan_times.get(active_id)
    if not ts:
        return "טרם סרקת"
    try:
        d = datetime.fromisoformat(ts)
        return d.strftime("%H:%M") if d.date() == datetime.now().date() else d.strftime("%-d.%-m")
    except Exception:
        return ""

# ── Feed items ────────────────────────────────────────────────
def _get_feed_items():
    session_feeds = st.session_state.scan_results.get(active_id, [])
    manual_feeds  = [f for f in company.get("feeds", []) if f.get("source") in ("manual", "maya")]
    for f in session_feeds + manual_feeds:
        f.setdefault("_co_id", active_id)
    all_items = session_feeds + manual_feeds
    filtered  = [f for f in all_items if f.get("source") in active_src]
    age_days  = {"all": None, "1": 1, "7": 7, "30": 30}.get(age)
    if age_days:
        cutoff = datetime.now() - timedelta(days=age_days)
        def _in_range(it):
            try:
                return datetime.fromisoformat(it.get("timestamp", "")) >= cutoff
            except Exception:
                return True
        filtered = [f for f in filtered if _in_range(f)]
    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return filtered

def _prep_feed_items(items):
    """Add source_label field that render.py displays below each feed item."""
    result = []
    for it in items:
        if "source_label" in it:
            result.append(it)
            continue
        it  = dict(it)
        src = it.get("source", "other")
        sm  = R.SOURCE_META.get(src, R.SOURCE_META.get("other", {"label": "אחר"}))
        lbl = sm["label"]
        ts  = it.get("timestamp", "")
        try:
            d        = datetime.fromisoformat(ts)
            date_str = d.strftime("%H:%M") if d.date() == datetime.now().date() else d.strftime("%d.%m")
            it["source_label"] = f"{lbl} · {date_str}"
        except Exception:
            it["source_label"] = lbl
        result.append(it)
    return result

# ── Iframe height by tab ──────────────────────────────────────
_iframe_height = {"feed": 1600, "fin": 190, "settings": 220}.get(tab, 1400)

from utils.build_balance_sheet import latest_balance_sheet_kpis
bs_kpis    = latest_balance_sheet_kpis(company)
feed_items = _prep_feed_items(_get_feed_items()) if tab == "feed" else []

# ── Iframe nav shim ───────────────────────────────────────────
# Streamlit 1.56 sandboxes components.html WITHOUT allow-top-navigation,
# so target="_top" links/forms are blocked by the browser.
# Fix: with allow-same-origin we can access window.parent.document and
# inject a <script> into the parent's DOM — it executes in the unrestricted
# parent context, so window.location.href navigates freely (full reload).
_NAV_SHIM = """<script>
(function(){
  function _navTop(url){
    try{
      var s=window.parent.document.createElement('script');
      s.textContent='window.location.href='+JSON.stringify(url)+';';
      window.parent.document.body.appendChild(s);
      s.remove();
    }catch(e){}
  }
  document.addEventListener('click',function(e){
    var a=e.target.closest('a[target="_top"]');
    if(a){e.preventDefault();e.stopPropagation();_navTop(a.getAttribute('href'));}
  },true);
  document.addEventListener('submit',function(e){
    var f=e.target;
    if(f.target==='_top'){
      e.preventDefault();
      _navTop('?'+new URLSearchParams(new FormData(f)).toString());
    }
  },true);
})();
</script>"""

# ── Add company modal (opened by "+ הוסף" link in strip) ──────
if qp.get("add_co"):
    st.markdown("##### ➕ הוסף חברה חדשה")
    with st.form("add_co_form", clear_on_submit=True):
        fc1, fc2, fc3 = st.columns([0.4, 0.2, 0.4])
        with fc1: _ac_name   = st.text_input("שם החברה",  placeholder="Mobileye")
        with fc2: _ac_ticker = st.text_input("טיקר",       placeholder="MBLY")
        with fc3: _ac_kw     = st.text_input("מילות מפתח", placeholder="MBLY, Mobileye")
        fb1, fb2 = st.columns(2)
        with fb1: _submitted = st.form_submit_button("➕ הוסף", type="primary", use_container_width=True)
        with fb2: _cancelled = st.form_submit_button("ביטול",  use_container_width=True)
    if _submitted and _ac_name.strip():
        _kws   = [k.strip() for k in _ac_kw.split(",") if k.strip()]
        new_co = add_company(data, _ac_name.strip(), _ac_ticker.strip(), _kws)
        st.session_state.data = load_data()
        del qp["add_co"]
        qp["co"] = new_co["id"]; qp["tab"] = "feed"
        st.rerun()
    if _cancelled:
        del qp["add_co"]
        st.rerun()
    st.divider()

# ── Render entire tab as isolated iframe ──────────────────────
html = R.page_html(
    tab=tab,
    companies=companies,
    active_id=active_id,
    company=company,
    bs_kpis=bs_kpis,
    feed_items=feed_items,
    active_src=active_src,
    last_scan=_last_scan_label(),
    age=age,
    classify=classify,
    scanning=scanning,
)
html = html.replace("</body>", _NAV_SHIM + "</body>")
components.html(html, height=_iframe_height, scrolling=True)

# ── Run the actual scan now that the dashboard above is already visible ──
if scanning:
    co_obj = get_company(data, active_id)
    if co_obj:
        _age_days = {"all": None, "1": 1, "7": 7, "30": 30}.get(age)
        try:    new_items    = fetch_news_for_company(co_obj, max_age_days=_age_days)
        except Exception: new_items = []
        try:    reddit_items = fetch_reddit_for_company(
                    co_obj, max_age_days=_age_days,
                    reddit_client_id=st.secrets.get("REDDIT_CLIENT_ID"),
                    reddit_client_secret=st.secrets.get("REDDIT_CLIENT_SECRET"),
                )
        except Exception: reddit_items = []
        try:    custom_items = fetch_from_source_urls(co_obj, max_age_days=_age_days)
        except Exception: custom_items = []

        existing_session = st.session_state.scan_results.get(active_id, [])
        existing_titles  = (
            {f.get("title", "") for f in co_obj.get("feeds", [])} |
            {f.get("title", "") for f in existing_session}
        )

        def _mk(source, ni, notes=""):
            return {
                "id": str(uuid.uuid4())[:8], "source": source, "_co_id": active_id,
                "title": ni["title"], "url": ni.get("url", ""),
                "snippet": ni.get("snippet", ""), "notes": notes,
                "matched_keyword": ni.get("matched_keyword", ""),
                "keyword_context": ni.get("keyword_context", ""),
                "timestamp": ni.get("timestamp", datetime.now().isoformat()),
            }

        new_scan = []
        for ni in custom_items:
            if ni["title"] not in existing_titles:
                new_scan.append(_mk("other", ni, ni.get("source_domain", "")))
                existing_titles.add(ni["title"])
        for ni in new_items:
            if ni["title"] not in existing_titles:
                new_scan.append(_mk("google", ni))
                existing_titles.add(ni["title"])
        for ni in reddit_items:
            if ni["title"] not in existing_titles:
                sub = ni.get("subreddit", "")
                new_scan.append(_mk("reddit", ni, f"r/{sub}" if sub else ""))
                existing_titles.add(ni["title"])

        st.session_state.scan_results[active_id]    = existing_session + new_scan
        st.session_state.last_scan_times[active_id] = datetime.now().isoformat()
        st.toast(f"נמצאו {len(new_scan)} פריטים חדשים ✓" if new_scan else "אין פריטים חדשים")
    _clear("scan")
    st.rerun()

# ════════════════════════════════════════════════════════════════
# TAB: FINANCIALS — native controls (PDF import, Excel, edit mode)
# ════════════════════════════════════════════════════════════════
if tab == "fin":
    import pandas as pd

    with st.expander("📥 ייבוא דוח מאיה (PDF)", expanded=not company.get("balance_sheet_extractions")):
        st.markdown("העלה דוח כספי PDF מאתר מאיה — Claude יחלץ ממנו את נתוני המאזן.")
        from utils.pdf_extractor import extract_balance_sheet_from_pdf, validate_balance_sheet
        from utils.data_manager import add_balance_sheet_extraction

        uploaded_pdf = st.file_uploader("בחר קובץ PDF", type=["pdf"], key="maya_upload")
        do_import = st.button(
            "🤖 ייבא עם Claude", type="primary", key="do_pdf_import",
            disabled=uploaded_pdf is None,
        )

        if do_import and uploaded_pdf:
            with st.spinner("Claude קורא את המאזן..."):
                try:
                    api_key   = st.secrets["ANTHROPIC_API_KEY"]
                    pdf_bytes = uploaded_pdf.read()
                    record    = extract_balance_sheet_from_pdf(pdf_bytes, api_key, source_reference=uploaded_pdf.name)

                    existing_extractions = company.get("balance_sheet_extractions", [])
                    for w in validate_balance_sheet(record, existing_records=existing_extractions):
                        st.warning(w)

                    result = add_balance_sheet_extraction(data, active_id, record)
                    if result["status"] == "added":
                        st.session_state.data = load_data()
                        st.success(
                            f"✅ יובא: {record['company']} — {record['period_end']} "
                            f"({record['period_type']}, {record['period_length_months']} חודשים)"
                        )
                        st.rerun()
                    elif result["status"] == "duplicate":
                        st.info(
                            f"רשומה זהה כבר קיימת עבור {record['company']} {record['period_end']} "
                            f"({record['period_type']}) — לא נוספה כפילות."
                        )
                    elif result["status"] == "conflict":
                        st.warning(
                            "קיימת רשומה עם אותו מפתח (חברה/תקופה/סוג) אך עם ערכים שונים — "
                            "לא בוצע עדכון אוטומטי. בדוק ידנית:"
                        )
                        st.json({"existing": result["existing"], "incoming": result["incoming"]})
                    else:
                        st.error(result.get("message", "שגיאה לא ידועה בשמירה."))
                except KeyError:
                    st.error("מפתח ANTHROPIC_API_KEY חסר ב-`.streamlit/secrets.toml`.")
                except Exception as _e:
                    st.error(f"שגיאה: {_e}")

    if company.get("balance_sheet_extractions"):
        from utils.build_balance_sheet import build_balance_sheet_table, export_balance_sheet_excel, FIELD_ROWS

        bs_hdr, bs_btn = st.columns([0.7, 0.3])
        with bs_hdr:
            st.markdown(f"##### מאזן — {company['name']}")
            st.caption("מבנה השורות והעמודות תואם לגיליון האקסל הידני של האנליסט.")
        with bs_btn:
            st.download_button(
                "⬇️ הורד אקסל (מאזן)",
                data=export_balance_sheet_excel(company),
                file_name=f"{company['name']}_מאזן.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key="dl_excel_balance_sheet",
            )

        # Split FIELD_ROWS into per-section groups (a "section" marker starts a new
        # group; total/grand_total/check rows attach to whichever group precedes
        # them — this lines up with how the analyst's own Excel groups a grand
        # total right after the section it closes out, e.g. "סה"כ נכסים" sits
        # right under "נכסים לא שוטפים", not in a section of its own).
        _row_groups = []
        for kind, key, label in FIELD_ROWS:
            if kind == "section":
                _row_groups.append({"title": label, "rows": []})
            else:
                _row_groups[-1]["rows"].append((kind, key, label))

        bs_table = build_balance_sheet_table(company)
        _BLOCK_LABELS = {"annual": "שנתי", "semiannual": "חצי שנתי", "quarterly": "רבעוני"}
        for block_name in ["annual", "semiannual", "quarterly"]:
            block = bs_table["blocks"][block_name]
            if not block["columns"]:
                continue
            st.markdown(f"### {_BLOCK_LABELS[block_name]}")
            # st.dataframe always renders columns left-to-right regardless of Hebrew
            # content (unlike the Excel export, which uses real RTL) — so to make
            # the on-screen table read right-to-left (סעיף on the right, periods
            # progressing right-to-left from oldest to newest), reverse the column
            # order: newest period first (leftmost), סעיף last (rightmost).
            ordered_cols = list(reversed(block["columns"])) + ["סעיף"]
            for group in _row_groups:
                st.markdown(f"**{group['title']}**")
                rows_data = []
                for kind, key, label in group["rows"]:
                    row = {"סעיף": label}
                    cells = block["cells"].get(key, {})
                    for col_label in block["columns"]:
                        row[col_label] = cells.get(col_label)
                    rows_data.append(row)
                df_bs = pd.DataFrame(rows_data)[ordered_cols]
                st.dataframe(df_bs, use_container_width=True, hide_index=True)

        if bs_table["extra"]:
            st.markdown("**שדות שלא שויכו לשורה קבועה — לבדיקת האנליסט**")
            st.caption("Claude חילץ ערכים אלו מה-PDF אך הם לא תואמים אף שורה בתבנית הקבועה — "
                       "לא הוספנו אותם באופן אוטומטי לשום מקום.")
            st.dataframe(pd.DataFrame(bs_table["extra"]), use_container_width=True, hide_index=True)

        st.divider()

# ════════════════════════════════════════════════════════════════
# TAB: SETTINGS — native Streamlit below the nav iframe
# ════════════════════════════════════════════════════════════════
elif tab == "settings":
    st.markdown("##### הגדרות חברה")
    with st.form("edit_company_form"):
        edit_name   = st.text_input("שם החברה", value=company["name"])
        edit_ticker = st.text_input("טיקר",      value=company.get("ticker", ""))
        if st.form_submit_button("שמור שינויים", type="primary"):
            for c in data["companies"]:
                if c["id"] == active_id:
                    c["name"]   = edit_name.strip()
                    c["ticker"] = edit_ticker.strip()
                    break
            save_data(data)
            st.success("נשמר ✓")
            st.rerun()

    st.divider()

    st.markdown("##### מקורות סריקה")
    with st.form("add_src", clear_on_submit=True):
        src_c, sbtn_c = st.columns([0.72, 0.28])
        with src_c:
            new_src_url = st.text_input("src", placeholder="https://...", label_visibility="collapsed")
        with sbtn_c:
            if st.form_submit_button("+ מקור", use_container_width=True) and new_src_url.strip():
                add_scan_source(data, active_id, new_src_url.strip())
                save_data(data)
                st.rerun()

    scan_sources = company.get("scan_sources", [])
    if scan_sources:
        for src_url in scan_sources:
            from urllib.parse import urlparse as _up
            domain = (_up(src_url).netloc or src_url).replace("www.", "")[:30]
            sc1, sc2 = st.columns([0.8, 0.2])
            with sc1:
                st.caption(f"🔗 {domain}")
            with sc2:
                if st.button("✕", key=f"delsrc_{src_url}", help="הסר מקור"):
                    remove_scan_source(data, active_id, src_url)
                    save_data(data)
                    st.rerun()

    st.divider()

    if st.button("🗑️ מחק חברה", key="del_co"):
        st.session_state["confirm_delete"] = True
    if st.session_state.get("confirm_delete"):
        st.warning(f"בטוח שרוצה למחוק את {company['name']}?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("כן, מחק", type="primary"):
                remaining = [c for c in companies if c["id"] != active_id]
                delete_company(data, active_id)
                st.session_state["confirm_delete"] = False
                new_id = remaining[0]["id"] if remaining else None
                if new_id:
                    qp["co"] = new_id
                st.rerun()
        with c2:
            if st.button("ביטול"):
                st.session_state["confirm_delete"] = False
                st.rerun()

    st.divider()
    st.markdown("##### ייצוא / גיבוי")
    ce1, ce2 = st.columns(2)
    with ce1:
        all_json = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button("⬇️ ייצוא כל הנתונים (JSON)", data=all_json.encode("utf-8"),
                           file_name="analyst_terminal_export.json", mime="application/json",
                           use_container_width=True)
    with ce2:
        uploaded_json = st.file_uploader("📥 ייבוא נתונים (JSON)", type=["json"], key="import_json")
        if uploaded_json:
            try:
                imported = json.load(uploaded_json)
                save_data(imported)
                st.session_state.data = imported
                st.success("נתונים יובאו בהצלחה ✓")
                st.rerun()
            except Exception as e:
                st.error(f"שגיאה בייבוא: {e}")

    st.divider()
    with st.expander("ℹ️ אודות הפרויקט"):
        st.markdown(
            "**Analyst Terminal** הוא פרויקט אישי — טרמינל מחקר לאנליסטים למעקב אחר "
            "חברות ציבוריות, שנבנה מאפס כדי להדגים כמה יכולות הנדסיות יחד:\n\n"
            "- **חילוץ דוחות כספיים מ-PDF עם Claude** — מעלים דוח מאזן, ומודל שפה קורא "
            "אותו וממפה אותו אוטומטית לשדות מובנים, כולל בדיקות תקינות ואיתור כפילויות/סתירות.\n"
            "- **איסוף מודיעין רב-מקורי** — Google News, Reddit, פידי RSS מותאמים אישית ודיווחים "
            "ידניים, עם סיווג אוטומטי לחברה מול מתחרים וסינון לפי גיל וזמינות.\n"
            "- **מנוע תצוגה RTL בעברית מבוסס iframe** — נבנה במיוחד כדי לעקוף את מגבלות "
            "ה-CSS של Streamlit ולהשיג עיצוב טרמינל פיננסי מלא ותומך-כיווניות.\n"
            "- **ייצוא לאקסל בפורמט אנליסט מקצועי**, טבלאות דוחות כספיים הניתנות לעריכה, "
            "וגיבוי/ייבוא מלא של הנתונים כ-JSON.\n\n"
            "הפרויקט אינו קשור לחברה או מעסיק כלשהו — הנתונים המוצגים הם דוגמת דמו "
            "על בסיס דיווחים ציבוריים. נבנה כדי להראות יכולת engineering מקצה לקצה: "
            "עיבוד נתונים, אינטגרציית LLM, ועיצוב ממשק."
        )
    st.caption("גרסה 1.0 · Analyst Terminal · בנוי עם Streamlit")
