import streamlit as st
import json
from datetime import datetime, timedelta
from utils.data_manager import (
    load_data, save_data, get_companies, get_company,
    add_company, delete_company,
    add_feed_item, delete_feed_item,
    add_keyword, remove_keyword,
    add_financial_section, add_financial_row, add_period,
    update_financial_cell,
    get_avatar_info, format_timestamp, fetch_news_for_company,
    classify_keyword,
    add_scan_source, remove_scan_source, fetch_from_source_urls,
    fetch_reddit_for_company,
    SOURCE_META, AVATAR_COLORS
)
from utils.excel_export import export_company_financials

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="חצבים — דאשבורד אנליסט",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme CSS ─────────────────────────────────────────────────
def _get_css(dark: bool) -> str:
    if dark:
        bg         = "#0D1421"
        bg_sidebar = "#0F1629"
        bg_card    = "#131E30"
        bg_input   = "rgba(255,255,255,0.04)"
        bg_stat    = "rgba(255,255,255,0.04)"
        bg_tab_bar = "#0F1E33"
        bg_tab_sel = "#1A2F4A"
        border     = "rgba(255,255,255,0.07)"
        border_str = "rgba(255,255,255,0.12)"
        text_pri   = "#FFFFFF"
        text_sec   = "#B7C2D2"
        text_muted = "#7A8AA0"
        accent     = "#7C6FE8"
        accent_bg  = "rgba(124,111,232,0.14)"
        accent_bdr = "rgba(124,111,232,0.3)"
        kw_color   = "#A89EEE"
        kw_blue    = "#60A5FA"
        kw_purple  = "#A78BFA"
        kw_teal    = "#2DD4BF"
        kw_amber   = "#FBB040"
        btn_sec_bg = "rgba(255,255,255,0.04)"
        btn_sec_c  = "#B7C2D2"
        btn_sec_bd = "rgba(255,255,255,0.1)"
        btn_sec_hb = "rgba(255,255,255,0.08)"
        btn_sec_hc = "#FFFFFF"
        btn_sec_hd = "rgba(255,255,255,0.2)"
        divider    = "rgba(255,255,255,0.07)"
        fin_head   = "rgba(124,111,232,0.14)"
        fin_headc  = "#A89EEE"
        fin_total  = "rgba(124,111,232,0.26)"
    else:
        bg         = "#F8F9FB"
        bg_sidebar = "#FFFFFF"
        bg_card    = "#FFFFFF"
        bg_input   = "#FFFFFF"
        bg_stat    = "#F7F7F8"
        bg_tab_bar = "#EEEDF8"
        bg_tab_sel = "#FFFFFF"
        border     = "#E5E9EF"
        border_str = "#CDD5DF"
        text_pri   = "#0A1628"
        text_sec   = "#374151"
        text_muted = "#6B7A8D"
        accent     = "#5349C8"
        accent_bg  = "#F0EDF9"
        accent_bdr = "#C8C3ED"
        kw_color   = "#4A3DAA"
        kw_blue    = "#1D4ED8"
        kw_purple  = "#6D28D9"
        kw_teal    = "#0F766E"
        kw_amber   = "#B45309"
        btn_sec_bg = "#FFFFFF"
        btn_sec_c  = "#374151"
        btn_sec_bd = "#D0D7E2"
        btn_sec_hb = "#F8F9FB"
        btn_sec_hc = "#0A1628"
        btn_sec_hd = "#9AA8B4"
        divider    = "#EBEBEB"
        fin_head   = "#EEEDFE"
        fin_headc  = "#5349C8"
        fin_total  = "#D6D3F5"

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Heebo:wght@400;500;700&display=swap');

/* ── Global RTL ── */
html, body, [class*="css"],
.stApp, .main, .block-container,
[data-testid="stSidebar"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stMarkdownContainer"],
[data-testid="stCaptionContainer"] {{
    direction: rtl !important;
    font-family: 'Heebo', 'Inter', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}}
/* Text-only elements — right-aligned */
p, h1, h2, h3, h4, h5, h6, label, span,
[data-testid="stMarkdownContainer"] p,
[data-testid="stCaptionContainer"] p {{
    text-align: right !important;
    direction: rtl !important;
}}
input, textarea {{
    text-align: right !important;
    direction: rtl !important;
}}
/* Dataframe cells — centered */
[data-testid="stDataFrame"] td,
[data-testid="stDataFrame"] th {{
    text-align: center !important;
}}
[data-testid="stDataFrame"] td:first-child,
[data-testid="stDataFrame"] th:first-child {{
    text-align: right !important;
}}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}
div[data-testid="stToolbar"] {{ visibility: hidden; }}
[data-testid="stHeader"] {{ display: none !important; }}

/* ── App background ── */
.stApp {{ background: {bg} !important; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: {bg_sidebar} !important;
    border-left: 1px solid {border} !important;
}}
[data-testid="stSidebar"] .block-container {{ padding: 1rem; }}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {{ color: {text_sec} !important; }}
[data-testid="stSidebar"] small {{ color: {text_muted} !important; }}

/* ── Main container ── */
.main .block-container {{ padding: 1.5rem 2rem; max-width: 1400px; }}

/* ── General text ── */
p, .stMarkdown p {{ color: {text_sec}; }}
h1, h2, h3, h4, h5, h6 {{ color: {text_pri}; }}
[data-testid="stCaptionContainer"] p {{ color: {text_muted} !important; font-size: 12px !important; }}
hr {{ border-color: {divider} !important; margin: 10px 0 !important; }}

/* ── Buttons — primary ── */
.stButton > button[kind="primary"] {{
    background: {accent} !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    border: none !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 14px -4px rgba(83,73,200,0.4) !important;
    transition: background 0.15s !important;
}}
.stButton > button[kind="primary"]:hover {{ filter: brightness(1.1) !important; }}
.stButton > button[kind="primary"]:active {{ transform: translateY(1px) !important; }}

/* ── Buttons — secondary ── */
.stButton > button:not([kind="primary"]) {{
    background: {btn_sec_bg} !important;
    color: {btn_sec_c} !important;
    border: 1px solid {btn_sec_bd} !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
}}
.stButton > button:not([kind="primary"]):hover {{
    background: {btn_sec_hb} !important;
    color: {btn_sec_hc} !important;
    border-color: {btn_sec_hd} !important;
}}

/* ── Download buttons ── */
.stDownloadButton > button {{
    background: {btn_sec_bg} !important;
    color: {btn_sec_c} !important;
    border: 1px solid {btn_sec_bd} !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    background: {bg_tab_bar} !important;
    border-radius: 12px !important;
    padding: 4px !important;
    border: 1px solid {border} !important;
    gap: 2px !important;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    color: {text_muted} !important;
    border-radius: 9px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border: none !important;
}}
.stTabs [aria-selected="true"] {{
    background: {bg_tab_sel} !important;
    color: {text_pri} !important;
    box-shadow: inset 0 0 0 1px {border_str} !important;
}}

/* ── Expanders ── */
[data-testid="stExpander"] {{
    background: {bg_card} !important;
    border: 1px solid {border} !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
    font-weight: 600 !important;
    font-size: 13.5px !important;
    color: {text_pri} !important;
    padding: 14px 16px !important;
}}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-baseweb="textarea"] textarea {{
    background: {bg_input} !important;
    border: 1px solid {border_str} !important;
    border-radius: 10px !important;
    color: {text_pri} !important;
    font-size: 13.5px !important;
}}
[data-testid="stTextInput"] input:focus,
[data-baseweb="textarea"] textarea:focus {{
    border-color: {accent} !important;
    box-shadow: 0 0 0 3px rgba(83,73,200,0.12) !important;
}}
[data-testid="stTextInput"] input::placeholder,
[data-baseweb="textarea"] textarea::placeholder {{ color: {text_muted} !important; }}

/* ── Selectbox / dropdown ── */
[data-baseweb="select"] > div {{
    background: {bg_input} !important;
    border-color: {border_str} !important;
    border-radius: 10px !important;
    color: {text_pri} !important;
}}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {border} !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}}

/* ── Alerts ── */
[data-testid="stSuccess"] {{
    background: rgba(22,163,74,0.08) !important;
    border: 1px solid rgba(22,163,74,0.22) !important;
    border-radius: 10px !important;
}}
[data-testid="stInfo"] {{
    background: rgba(83,73,200,0.07) !important;
    border: 1px solid rgba(83,73,200,0.18) !important;
    border-radius: 10px !important;
}}
[data-testid="stWarning"] {{
    background: rgba(217,119,6,0.07) !important;
    border: 1px solid rgba(217,119,6,0.18) !important;
    border-radius: 10px !important;
}}
[data-testid="stError"] {{
    background: rgba(220,38,38,0.07) !important;
    border: 1px solid rgba(220,38,38,0.18) !important;
    border-radius: 10px !important;
}}

/* ── Radio ── */
[data-testid="stRadio"] label {{ color: {text_sec} !important; }}
[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {{ color: {text_sec} !important; }}

/* ── Spinner ── */
[data-testid="stSpinner"] {{ color: {accent} !important; }}

/* ── Custom component styles ── */
.feed-badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 600;
    margin-bottom: 4px;
}}

/* Keyword chips — category colors (theme-independent) */
.kw-chip-base, .kw-blue-chip, .kw-purple-chip, .kw-teal-chip, .kw-amber-chip {{
    display: inline-block;
    border-radius: 99px;
    padding: 3px 11px;
    font-size: 12px;
    font-weight: 500;
    margin: 2px 0;
    line-height: 1.5;
}}
.kw-blue-chip   {{ background:rgba(59,130,246,0.13);  color:{kw_blue};   border:0.5px solid rgba(59,130,246,0.35); }}
.kw-purple-chip {{ background:rgba(139,92,246,0.13);  color:{kw_purple}; border:0.5px solid rgba(139,92,246,0.35); }}
.kw-teal-chip   {{ background:rgba(20,184,166,0.13);  color:{kw_teal};   border:0.5px solid rgba(20,184,166,0.35); }}
.kw-amber-chip  {{ background:rgba(245,158,11,0.13);  color:{kw_amber};  border:0.5px solid rgba(245,158,11,0.35); }}

.stat-mini {{
    background: {bg_stat};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 12px 14px;
    text-align: center;
}}
.stat-num {{ font-size: 22px; font-weight: 700; color: {text_pri}; }}
.stat-lbl {{ font-size: 11px; color: {text_muted}; margin-top: 2px; }}

.feed-snippet {{
    font-size: 12px;
    color: {text_muted};
    background: rgba(128,128,128,0.06);
    padding: 6px 10px;
    border-radius: 6px;
    margin: 4px 0 2px 0;
    border-right: 2px solid {accent_bdr};
    line-height: 1.55;
}}

.company-avatar {{
    width: 42px; height: 42px;
    border-radius: 10px;
    display: inline-flex;
    align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px;
}}

.fin-section-header {{
    background: {fin_head};
    color: {fin_headc};
    font-weight: 600;
    font-size: 13px;
    padding: 6px 12px;
    border-radius: 6px 6px 0 0;
    border: 0.5px solid {accent_bdr};
}}
</style>
"""

# ── Session state ─────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True


st.markdown(_get_css(st.session_state.dark_mode), unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = load_data()

if "active_company_id" not in st.session_state:
    companies = get_companies(st.session_state.data)
    st.session_state.active_company_id = companies[0]["id"] if companies else None

if "source_filters" not in st.session_state:
    st.session_state.source_filters = {"google", "reddit", "maya", "manual", "other"}

if "fin_edit_mode" not in st.session_state:
    st.session_state.fin_edit_mode = False

if "news_age_days" not in st.session_state:
    st.session_state.news_age_days = 7

if "last_scan_times" not in st.session_state:
    st.session_state.last_scan_times = {}

data = st.session_state.data
companies = get_companies(data)


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    hdr_col, mode_col = st.columns([0.75, 0.25])
    with hdr_col:
        st.markdown("### 📊 חצבים")
        st.markdown("**דאשבורד אנליסט**")
    with mode_col:
        mode_icon = "☀️" if st.session_state.dark_mode else "🌙"
        if st.button(mode_icon, key="toggle_dark", help="החלף מצב תצוגה"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    st.divider()

    st.markdown("**חברות במעקב**")
    for i, company in enumerate(companies):
        initials, bg, fg = get_avatar_info(company, i)
        is_active = company["id"] == st.session_state.active_company_id
        label = f"{'▶ ' if is_active else ''}{company['name']}"
        if is_active:
            st.markdown(
                f"<div style='background:#5349C8;color:white;border-radius:8px;"
                f"padding:8px 12px;font-weight:600;font-size:13px;margin:2px 0'>"
                f"▶ {company['name']}</div>",
                unsafe_allow_html=True
            )
        else:
            if st.button(company["name"], key=f"nav_{company['id']}", use_container_width=True):
                st.session_state.active_company_id = company["id"]
                st.rerun()

    st.divider()

    # Add company
    with st.expander("➕ הוסף חברה"):
        new_name = st.text_input("שם החברה", key="new_co_name", placeholder="לדוגמה: Mobileye")
        new_ticker = st.text_input("טיקר", key="new_co_ticker", placeholder="MBLY")
        new_kw = st.text_input("מילות מפתח (בפסיקים)", key="new_co_kw", placeholder="MBLY, Mobileye, intel")
        if st.button("הוסף חברה", key="do_add_co", use_container_width=True, type="primary"):
            if new_name:
                kws = [k.strip() for k in new_kw.split(",") if k.strip()]
                co = add_company(data, new_name, new_ticker, kws)
                st.session_state.active_company_id = co["id"]
                st.rerun()

    st.divider()
    st.caption(f"עדכון אחרון: {datetime.now().strftime('%H:%M')}")


# ── Main content ──────────────────────────────────────────────
company = get_company(data, st.session_state.active_company_id)
if not company:
    st.info("בחר חברה מהתפריט הצדי, או הוסף חברה חדשה.")
    st.stop()

company_idx = next((i for i, c in enumerate(companies) if c["id"] == company["id"]), 0)
initials, avatar_bg, avatar_fg = get_avatar_info(company, company_idx)

# ── Company header ────────────────────────────────────────────
col_av, col_info, col_actions = st.columns([0.06, 0.7, 0.24])
with col_av:
    st.markdown(
        f"<div class='company-avatar' style='background:{avatar_bg};color:{avatar_fg}'>{initials}</div>",
        unsafe_allow_html=True
    )
with col_info:
    ticker = company.get("ticker", "")
    st.markdown(f"## {company['name']} {f'({ticker})' if ticker else ''}")
    feed_count = len(company.get("feeds", []))
    kw_count = len(company.get("keywords", []))
    st.caption(f"{feed_count} פריטי מידע · {kw_count} מילות מפתח")

with col_actions:
    with col_actions:
        if st.button("🗑️ מחק חברה", key="del_co", use_container_width=True):
            st.session_state["confirm_delete"] = True

if st.session_state.get("confirm_delete"):
    st.warning(f"בטוח שרוצה למחוק את {company['name']}?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("כן, מחק", type="primary"):
            remaining = [c for c in companies if c["id"] != company["id"]]
            delete_company(data, company["id"])
            st.session_state.active_company_id = remaining[0]["id"] if remaining else None
            st.session_state["confirm_delete"] = False
            st.rerun()
    with c2:
        if st.button("ביטול"):
            st.session_state["confirm_delete"] = False
            st.rerun()

st.divider()

# ── Tabs ──────────────────────────────────────────────────────
tab_feed, tab_fin, tab_settings = st.tabs(["📰 פיד מידע", "📊 דוחות כספיים", "⚙️ הגדרות"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1: FEED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_feed:
    col_feed, col_panel = st.columns([0.60, 0.40], gap="large")

    # ── LEFT (60%): Feed items ────────────────────────────────
    with col_feed:
        st.markdown("##### פיד מידע")

        # Source filter toggles
        src_cols = st.columns(len(SOURCE_META))
        for si, (src_key, src_info) in enumerate(SOURCE_META.items()):
            with src_cols[si]:
                active = src_key in st.session_state.source_filters
                if st.button(f"{'✓ ' if active else ''}{src_info['label']}", key=f"filter_{src_key}", use_container_width=True):
                    if active:
                        st.session_state.source_filters.discard(src_key)
                    else:
                        st.session_state.source_filters.add(src_key)
                    st.rerun()

        st.markdown("")

        # Time range filter
        _time_options = {"היום": 1, "שבוע אחרון": 7, "חודש אחרון": 30, "הכל": None}
        time_filter = st.radio("הצג מידע מ:", options=list(_time_options.keys()), horizontal=True, index=3, key="time_filter")
        _days = _time_options[time_filter]
        _now = datetime.now()

        def _in_range(item: dict) -> bool:
            if _days is None:
                return True
            try:
                return (_now - datetime.fromisoformat(item.get("timestamp", ""))) <= timedelta(days=_days)
            except Exception:
                return True

        feeds = company.get("feeds", [])
        filtered_feeds = [f for f in feeds if f.get("source") in st.session_state.source_filters]
        time_filtered = [f for f in filtered_feeds if _in_range(f)]

        if feeds:
            st.caption(f"מציג {len(time_filtered)} מתוך {len(feeds)} פריטים")
        st.markdown("")

        # Feed items or empty state
        if not feeds:
            st.markdown(
                "<div style='text-align:center;padding:52px 16px;opacity:0.42'>"
                "<div style='font-size:42px'>📭</div>"
                "<div style='font-size:15px;font-weight:600;margin:10px 0 6px'>הפיד ריק</div>"
                "<div style='font-size:12px;line-height:1.7'>"
                "לחץ על <b>סרוק עכשיו</b> כדי למשוך חדשות על החברה,<br>"
                "או הוסף פריט ידני מהעמודה הימנית."
                "</div></div>",
                unsafe_allow_html=True,
            )
        elif not time_filtered:
            st.info("אין פריטים בטווח הזמן הנבחר.")
        else:
            for item in time_filtered:
                src  = item.get("source", "other")
                meta = SOURCE_META.get(src, SOURCE_META["other"])
                c1, c2 = st.columns([0.92, 0.08])
                with c1:
                    st.markdown(
                        f"<span class='feed-badge' style='background:{meta['bg']};color:{meta['color']}'>"
                        f"{meta['icon']} {meta['label']}</span>",
                        unsafe_allow_html=True,
                    )
                    url = item.get("url", "")
                    title = item.get("title", "")
                    st.markdown(f"**[{title}]({url})**" if url else f"**{title}**")
                    if item.get("snippet"):
                        snip = item["snippet"][:220] + "…" if len(item["snippet"]) > 220 else item["snippet"]
                        st.markdown(f"<div class='feed-snippet'>{snip}</div>", unsafe_allow_html=True)
                    if item.get("notes"):
                        st.caption(f"📝 {item['notes']}")
                    st.caption(format_timestamp(item.get("timestamp", "")))
                with c2:
                    if st.button("✕", key=f"del_{item['id']}", help="מחק"):
                        delete_feed_item(data, company["id"], item["id"])
                        st.rerun()
                st.markdown(
                    "<hr style='border:none;border-top:0.5px solid rgba(128,128,128,0.15);margin:4px 0'>",
                    unsafe_allow_html=True,
                )

    # ── RIGHT (40%): Keyword manager + add form ───────────────
    with col_panel:
        # Stats row
        feeds_all = company.get("feeds", [])
        s_go = sum(1 for f in feeds_all if f.get("source") == "google")
        s_rd = sum(1 for f in feeds_all if f.get("source") == "reddit")
        s_ma = sum(1 for f in feeds_all if f.get("source") == "maya")
        s_mn = sum(1 for f in feeds_all if f.get("source") == "manual")
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1: st.markdown(f"<div class='stat-mini'><div class='stat-num'>{s_go}</div><div class='stat-lbl'>Google</div></div>", unsafe_allow_html=True)
        with sc2: st.markdown(f"<div class='stat-mini'><div class='stat-num'>{s_rd}</div><div class='stat-lbl'>Reddit</div></div>", unsafe_allow_html=True)
        with sc3: st.markdown(f"<div class='stat-mini'><div class='stat-num'>{s_ma}</div><div class='stat-lbl'>מאיה</div></div>", unsafe_allow_html=True)
        with sc4: st.markdown(f"<div class='stat-mini'><div class='stat-num'>{s_mn}</div><div class='stat-lbl'>ידני</div></div>", unsafe_allow_html=True)

        st.markdown("")

        # ── Keyword Manager Panel ──────────────────────────────
        st.markdown("##### 🔍 מילות מפתח לסריקה")

        keywords = company.get("keywords", [])
        if keywords:
            CHIPS_PER_ROW = 3
            chip_w = round(0.80 / CHIPS_PER_ROW, 3)
            del_w  = round(0.10 / CHIPS_PER_ROW, 3)
            for row_start in range(0, len(keywords), CHIPS_PER_ROW):
                row_kws = keywords[row_start:row_start + CHIPS_PER_ROW]
                n = len(row_kws)
                widths = []
                for _ in range(n):
                    widths.extend([chip_w, del_w])
                remainder = round(1.0 - sum(widths), 3)
                if remainder > 0.01:
                    widths.append(remainder)
                cols = st.columns(widths, vertical_alignment="center")
                for j, kw in enumerate(row_kws):
                    cat = classify_keyword(kw)
                    with cols[j * 2]:
                        st.markdown(f"<span class='kw-{cat}-chip'>{kw}</span>", unsafe_allow_html=True)
                    with cols[j * 2 + 1]:
                        if st.button("✕", key=f"rmkw_{company['id']}_{kw}", help=f"הסר {kw}"):
                            remove_keyword(data, company["id"], kw)
                            st.rerun()
        else:
            st.markdown(
                "<div style='text-align:center;padding:14px 8px;opacity:0.42'>"
                "<span style='font-size:22px'>🏷️</span><br>"
                "<span style='font-size:12px'>אין מילות מפתח. הוסף למטה.</span>"
                "</div>",
                unsafe_allow_html=True,
            )

        # Add keyword — form lets Enter key submit
        with st.form("add_kw_form", clear_on_submit=True):
            kw_inp_col, kw_btn_col = st.columns([0.72, 0.28])
            with kw_inp_col:
                new_kw = st.text_input("kw", placeholder="הקלד מילת מפתח...", label_visibility="collapsed")
            with kw_btn_col:
                kw_ok = st.form_submit_button("+ הוסף", use_container_width=True)
            if kw_ok and new_kw.strip():
                add_keyword(data, company["id"], new_kw.strip())
                st.rerun()

        # ── Sources to Scan Panel ──────────────────────────────
        st.markdown("##### 🔗 מקורות לסריקה")

        from urllib.parse import urlparse as _urlparse
        scan_sources = company.get("scan_sources", [])
        if scan_sources:
            SRC_PER_ROW = 2
            src_chip_w = round(0.80 / SRC_PER_ROW, 3)
            src_del_w  = round(0.10 / SRC_PER_ROW, 3)
            for row_start in range(0, len(scan_sources), SRC_PER_ROW):
                row_srcs = scan_sources[row_start:row_start + SRC_PER_ROW]
                n = len(row_srcs)
                widths_s = []
                for _ in range(n):
                    widths_s.extend([src_chip_w, src_del_w])
                remainder_s = round(1.0 - sum(widths_s), 3)
                if remainder_s > 0.01:
                    widths_s.append(remainder_s)
                src_cols = st.columns(widths_s, vertical_alignment="center")
                for j, src_url in enumerate(row_srcs):
                    parsed = _urlparse(src_url)
                    domain = (parsed.netloc or src_url).replace("www.", "")[:28]
                    with src_cols[j * 2]:
                        st.markdown(f"<span class='kw-teal-chip'>🔗 {domain}</span>", unsafe_allow_html=True)
                    with src_cols[j * 2 + 1]:
                        if st.button("✕", key=f"rmsrc_{company['id']}_{src_url}", help=f"הסר {src_url}"):
                            remove_scan_source(data, company["id"], src_url)
                            st.rerun()
        else:
            st.markdown(
                "<div style='text-align:center;padding:10px 8px;opacity:0.4'>"
                "<span style='font-size:12px'>הוסף קישורי RSS או אתרים לסריקה אוטומטית</span>"
                "</div>",
                unsafe_allow_html=True,
            )

        with st.form("add_src_form", clear_on_submit=True):
            src_inp_col, src_btn_col = st.columns([0.72, 0.28])
            with src_inp_col:
                new_src_url = st.text_input("src", placeholder="https://calcalist.co.il/rss", label_visibility="collapsed")
            with src_btn_col:
                src_ok = st.form_submit_button("+ הוסף", use_container_width=True)
            if src_ok and new_src_url.strip():
                add_scan_source(data, company["id"], new_src_url.strip())
                st.rerun()

        st.divider()

        # Last scan info
        last_scan_ts = st.session_state.last_scan_times.get(company["id"])
        if last_scan_ts:
            st.caption(f"💡 {len(keywords)} מילות מפתח · עדכון אחרון: {format_timestamp(last_scan_ts)}")
        else:
            st.caption(f"💡 {len(keywords)} מילות מפתח · טרם סרקת")

        # Age selector + scan button
        _age_labels = {"24 שעות": 1, "שבוע": 7, "חודש": 30, "ללא מגבלה": None}
        age_col, scan_col = st.columns([0.45, 0.55])
        with age_col:
            _age_sel = st.selectbox("טווח", list(_age_labels.keys()), index=1, key="news_age_sel", label_visibility="collapsed")
        _age_days = _age_labels[_age_sel]
        with scan_col:
            if st.button("🔄 סרוק עכשיו", key="refresh_news", use_container_width=True, type="primary"):
                with st.spinner("סורק חדשות..."):
                    new_items    = fetch_news_for_company(company, max_age_days=_age_days)
                    reddit_items = fetch_reddit_for_company(company, max_age_days=_age_days)
                    custom_items = fetch_from_source_urls(company, max_age_days=_age_days)
                existing_titles = {f.get("title", "") for f in company.get("feeds", [])}
                added = 0
                for ni in new_items:
                    if ni["title"] not in existing_titles:
                        add_feed_item(data, company["id"], "google", ni["title"], ni["url"],
                                      timestamp=ni["timestamp"], snippet=ni.get("snippet", ""))
                        existing_titles.add(ni["title"])
                        added += 1
                for ni in reddit_items:
                    if ni["title"] not in existing_titles:
                        sub = ni.get("subreddit", "")
                        add_feed_item(data, company["id"], "reddit", ni["title"], ni["url"],
                                      notes=f"r/{sub}" if sub else "",
                                      timestamp=ni["timestamp"], snippet=ni.get("snippet", ""))
                        existing_titles.add(ni["title"])
                        added += 1
                for ni in custom_items:
                    if ni["title"] not in existing_titles:
                        add_feed_item(data, company["id"], "other", ni["title"], ni["url"],
                                      notes=ni.get("source_domain", ""),
                                      timestamp=ni["timestamp"], snippet=ni.get("snippet", ""))
                        existing_titles.add(ni["title"])
                        added += 1
                st.session_state.last_scan_times[company["id"]] = datetime.now().isoformat()
                msg = f"נמצאו {added} פריטים חדשים ✓" if added > 0 else "אין פריטים חדשים"
                st.toast(msg)
                st.rerun()

        # ── Manual add form ────────────────────────────────────
        st.markdown("##### ➕ הוסף פריט ידני")
        with st.form("add_feed_form", clear_on_submit=True):
            new_src = st.selectbox("מקור", list(SOURCE_META.keys()), format_func=lambda k: SOURCE_META[k]["label"], key="new_src_sel")
            new_title = st.text_area("כותרת / תיאור", placeholder="מה גילית? הוסף קישור, ציטוט, הערה...", height=72)
            new_url   = st.text_input("קישור (אופציונלי)", placeholder="https://...")
            new_notes = st.text_input("הערות (אופציונלי)", placeholder="הקשר נוסף...")
            if st.form_submit_button("➕ הוסף לפיד", use_container_width=True, type="primary"):
                if new_title.strip():
                    add_feed_item(data, company["id"], new_src, new_title.strip(), new_url.strip(), new_notes.strip())
                    st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2: FINANCIALS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_fin:
    import pandas as pd

    fin = company.get("financials", {})
    periods = fin.get("periods", [])
    sections = fin.get("sections", [])
    maya_imported = fin.get("maya_imported", False)

    # ── Maya PDF import via Claude API ────────────────────────
    with st.expander("📥 ייבוא דוח מאיה (PDF)", expanded=not maya_imported):
        st.markdown("העלה דוח כספי PDF מאתר מאיה — Claude יקרא אותו ויוסיף עמודה חדשה לטבלה.")

        from utils.pdf_extractor import extract_financials_from_pdf

        imp_col1, imp_col2 = st.columns([0.6, 0.4])
        with imp_col1:
            period_name_input = st.text_input(
                "שם התקופה",
                placeholder="לדוגמה: Q2-26",
                key="pdf_period_name",
            )
        with imp_col2:
            uploaded_pdf = st.file_uploader("בחר קובץ PDF", type=["pdf"], key="maya_upload")

        do_import = st.button(
            "🤖 ייבא עם Claude",
            type="primary",
            key="do_pdf_import",
            disabled=not (period_name_input or "").strip() or uploaded_pdf is None,
        )

        if do_import and period_name_input.strip() and uploaded_pdf:
            with st.spinner("Claude קורא את הדוח... (10–20 שניות)"):
                try:
                    api_key = st.secrets["ANTHROPIC_API_KEY"]
                    pdf_bytes_claude = uploaded_pdf.read()
                    extracted = extract_financials_from_pdf(
                        pdf_bytes_claude, period_name_input.strip(), api_key
                    )

                    inc = extracted.get("income_statement", {})
                    bal = extracted.get("balance_sheet", {})
                    kpi = extracted.get("kpis", {})

                    # Map to exact row labels from companies.json
                    label_map = {
                        "רווח והפסד": {
                            "הכנסות":                  inc.get("revenue"),
                            "עלות המכר":               inc.get("cost_of_sales"),
                            "רווח גולמי":              inc.get("gross_profit"),
                            'הוצאות מו"פ':             inc.get("rd_expenses"),
                            "הוצאות מכירה והנהלה":     inc.get("selling_and_admin_expenses"),
                            "רווח תפעולי":             inc.get("operating_profit"),
                            "רווח לפני מס":            inc.get("profit_before_tax"),
                            "רווח נקי":                inc.get("net_profit"),
                        },
                        "מדדים תפעוליים": {
                            "צבר הזמנות":    kpi.get("order_backlog"),
                            "לקוחות פעילים": kpi.get("active_customers"),
                            "רכוש קבוע":     bal.get("fixed_assets"),
                        },
                    }

                    # Add new period column (appends 0 to all rows)
                    add_period(data, company["id"], period_name_input.strip())
                    company = get_company(data, company["id"])
                    new_period_idx = len(company["financials"]["periods"]) - 1

                    # Fill in values — direct edit to avoid N disk writes
                    filled = 0
                    for comp_obj in data["companies"]:
                        if comp_obj["id"] != company["id"]:
                            continue
                        for sec in comp_obj["financials"]["sections"]:
                            sec_map = label_map.get(sec["name"], {})
                            for row in sec["rows"]:
                                val = sec_map.get(row["label"])
                                if val is not None:
                                    row["values"][new_period_idx] = val
                                    filled += 1
                        break
                    save_data(data)
                    st.session_state.data = load_data()

                    st.success(f"✅ {period_name_input.strip()} יובא בהצלחה — {filled} שדות אוכלסו. בדוק את הטבלה למטה.")
                    st.rerun()

                except KeyError:
                    st.error("מפתח ANTHROPIC_API_KEY חסר ב-`.streamlit/secrets.toml`.")
                except Exception as _e:
                    st.error(f"שגיאה: {_e}")

    # ── No data state ─────────────────────────────────────────
    if not maya_imported or not sections:
        st.info("העלה דוח PDF מאיה למעלה כדי לאכלס את הטבלאות הכספיות.")
        st.stop()

    # ── Header row ────────────────────────────────────────────
    col_fin_hdr, col_fin_btn = st.columns([0.65, 0.35])
    with col_fin_hdr:
        st.markdown(f"##### דוחות כספיים — {company['name']}")
        st.caption(f"תקופות: {' · '.join(periods)}   |   יחידות: אלפי ₪ / $")
    with col_fin_btn:
        b1, b2, b3 = st.columns(3)
        with b1:
            edit_label = "✏️ עריכה" if not st.session_state.fin_edit_mode else "✅ סיים"
            if st.button(edit_label, key="toggle_edit", use_container_width=True):
                st.session_state.fin_edit_mode = not st.session_state.fin_edit_mode
                st.rerun()
        with b2:
            xlsx_bytes = export_company_financials(company)
            st.download_button(
                "⬇️ Excel",
                data=xlsx_bytes,
                file_name=f"{company['name']}_financials.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_excel_fin",
            )
        with b3:
            if st.button("🗑️ נקה", key="clear_fin", use_container_width=True):
                st.session_state["confirm_clear_fin"] = True

    if st.session_state.get("confirm_clear_fin"):
        st.warning("למחוק את כל הנתונים הכספיים?")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("כן, מחק", type="primary", key="do_clear_fin"):
                for c in data["companies"]:
                    if c["id"] == company["id"]:
                        c["financials"] = {"periods": [], "sections": [], "maya_imported": False}
                        break
                save_data(data)
                st.session_state["confirm_clear_fin"] = False
                st.rerun()
        with cc2:
            if st.button("ביטול", key="cancel_clear_fin"):
                st.session_state["confirm_clear_fin"] = False
                st.rerun()

    st.divider()

    # ── Render financial tables ────────────────────────────────
    for sec_idx, sec in enumerate(sections):
        st.markdown(
            f"<div class='fin-section-header'>{sec['name']}</div>",
            unsafe_allow_html=True
        )

        if st.session_state.fin_edit_mode:
            rows_data = []
            for row in sec.get("rows", []):
                row_dict = {"סעיף": row["label"]}
                for pi, period in enumerate(periods):
                    row_dict[period] = row["values"][pi] if pi < len(row["values"]) else 0
                rows_data.append(row_dict)

            df_edit = pd.DataFrame(rows_data)
            edited = st.data_editor(
                df_edit,
                key=f"editor_{company['id']}_{sec_idx}",
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config={"סעיף": st.column_config.TextColumn("סעיף", width="medium")}
            )
            for ri, row in edited.iterrows():
                for pi, period in enumerate(periods):
                    try:
                        val = float(row[period]) if row[period] is not None else 0
                        update_financial_cell(data, company["id"], sec_idx, ri, pi, val)
                    except Exception:
                        pass

            with st.form(f"add_row_{sec_idx}", clear_on_submit=True):
                new_row_label = st.text_input("שם שורה חדשה", key=f"new_row_lbl_{sec_idx}", placeholder="לדוגמה: הכנסות ממנויים")
                if st.form_submit_button("➕ הוסף שורה"):
                    if new_row_label.strip():
                        add_financial_row(data, company["id"], sec_idx, new_row_label.strip())
                        st.rerun()
        else:
            rows_data = []
            for row in sec.get("rows", []):
                row_dict = {"סעיף": row["label"]}
                for pi, period in enumerate(periods):
                    val = row["values"][pi] if pi < len(row["values"]) else 0
                    row_dict[period] = f"{val:,.0f}" if isinstance(val, (int, float)) else val
                rows_data.append(row_dict)

            _total_label = sec.get('total_label', 'סה"כ')
            total_dict = {"סעיף": f"📌 {_total_label}"}
            for pi, period in enumerate(periods):
                val = sec["total"][pi] if pi < len(sec.get("total", [])) else 0
                total_dict[period] = f"{val:,.0f}" if isinstance(val, (int, float)) else val
            rows_data.append(total_dict)

            st.dataframe(pd.DataFrame(rows_data), use_container_width=True, hide_index=True)

        st.markdown("")

    # ── Comparison table: last two periods ────────────────────
    if len(periods) >= 2 and not st.session_state.fin_edit_mode:
        p_prev, p_curr = periods[-2], periods[-1]
        comp_rows = []
        for sec in sections:
            for row in sec.get("rows", []):
                v_prev = row["values"][-2] if len(row["values"]) >= 2 else 0
                v_curr = row["values"][-1] if len(row["values"]) >= 1 else 0
                delta = v_curr - v_prev
                pct = (delta / abs(v_prev) * 100) if v_prev != 0 else None
                comp_rows.append({
                    "סעיף": row["label"],
                    p_prev: f"{v_prev:,.0f}",
                    p_curr: f"{v_curr:,.0f}",
                    "שינוי": f"{delta:+,.0f}",
                    "% שינוי": f"{pct:+.1f}%" if pct is not None else "—",
                })

        if comp_rows:
            st.divider()
            st.markdown(f"##### שינויים: {p_prev} → {p_curr}")
            st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

    # ── Add section / period (edit mode) ──────────────────────
    if st.session_state.fin_edit_mode:
        st.divider()
        col_sec1, col_sec2, col_per1, col_per2 = st.columns(4)
        with col_sec1:
            new_sec_name = st.text_input("שם סעיף חדש", placeholder="לדוגמה: הכנסות", key="new_sec_name")
        with col_sec2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ הוסף סעיף", key="do_add_sec"):
                if new_sec_name.strip():
                    add_financial_section(data, company["id"], new_sec_name.strip())
                    st.rerun()
        with col_per1:
            new_period = st.text_input("תקופה חדשה", placeholder="לדוגמה: Q2-26", key="new_period")
        with col_per2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ הוסף תקופה", key="do_add_period"):
                if new_period.strip():
                    add_period(data, company["id"], new_period.strip())
                    st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3: SETTINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_settings:
    st.markdown("##### הגדרות חברה")

    with st.form("edit_company_form"):
        edit_name = st.text_input("שם החברה", value=company["name"])
        edit_ticker = st.text_input("טיקר", value=company.get("ticker", ""))
        if st.form_submit_button("שמור שינויים", type="primary"):
            for c in data["companies"]:
                if c["id"] == company["id"]:
                    c["name"] = edit_name.strip()
                    c["ticker"] = edit_ticker.strip()
                    break
            save_data(data)
            st.success("נשמר ✓")
            st.rerun()

    st.divider()
    st.markdown("##### ייצוא / גיבוי")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        all_json = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ ייצוא כל הנתונים (JSON)",
            data=all_json.encode("utf-8"),
            file_name="chatzavim_data.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_exp2:
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
    st.markdown("##### אודות")
    st.caption("גרסה 1.0 · חצבים דאשבורד אנליסט · בנוי עם Streamlit")
