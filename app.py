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

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700&display=swap');

html, body, [class*="css"] { direction: rtl; font-family: 'Heebo', sans-serif; }

/* Sidebar */
[data-testid="stSidebar"] { background: #FAFAFA; border-left: 1px solid #EBEBEB; }
[data-testid="stSidebar"] .block-container { padding: 1rem; }

/* Main area */
.main .block-container { padding: 1.5rem 2rem; max-width: 1400px; }

/* Cards */
.card {
    background: white;
    border: 0.5px solid #E5E5E5;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
}

/* Feed items */
.feed-item {
    padding: 10px 0;
    border-bottom: 0.5px solid #F0F0F0;
}
.feed-item:last-child { border-bottom: none; }

.feed-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 600;
    margin-bottom: 4px;
}

/* Section title */
.section-title {
    font-size: 13px;
    font-weight: 600;
    color: #1A1A1A;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #F0F0F0;
}

/* Keyword chip */
.kw-chip {
    display: inline-block;
    background: #F0EDF9;
    color: #4A3DAA;
    border: 0.5px solid #C8C3ED;
    border-radius: 99px;
    padding: 2px 10px;
    font-size: 12px;
    margin: 2px;
}

/* Stat mini */
.stat-mini {
    background: #F7F7F8;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
}
.stat-num { font-size: 22px; font-weight: 700; color: #1A1A1A; }
.stat-lbl { font-size: 11px; color: #888; margin-top: 2px; }

/* Avatar */
.company-avatar {
    width: 40px; height: 40px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px;
}

/* Top bar */
.top-bar {
    display: flex; align-items: center; gap: 14px;
    padding: 0 0 18px 0;
    border-bottom: 1px solid #EBEBEB;
    margin-bottom: 20px;
}

/* Financial table overrides */
.fin-table th { background: #F7F7F8 !important; font-weight: 600; font-size: 12px; }
.fin-table .section-row td { background: #EEEDFE !important; color: #5349C8 !important; font-weight: 600; }
.fin-table .total-row td { background: #D6D3F5 !important; font-weight: 700; }

/* Hide streamlit elements */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
div[data-testid="stToolbar"] { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = load_data()

if "active_company_id" not in st.session_state:
    companies = get_companies(st.session_state.data)
    st.session_state.active_company_id = companies[0]["id"] if companies else None

if "source_filters" not in st.session_state:
    st.session_state.source_filters = {"linkedin", "google", "maya", "manual", "other"}

if "fin_edit_mode" not in st.session_state:
    st.session_state.fin_edit_mode = False

data = st.session_state.data
companies = get_companies(data)


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 חצבים")
    st.markdown("**דאשבורד אנליסט**")
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
    col_del, col_exp = st.columns(2)
    with col_exp:
        fin = company.get("financials", {})
        if fin.get("sections"):
            xlsx_bytes = export_company_financials(company)
            st.download_button(
                "⬇️ Excel",
                data=xlsx_bytes,
                file_name=f"{company['name']}_financials.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with col_del:
        if st.button("🗑️ מחק", key="del_co", use_container_width=True):
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
    col_left, col_right = st.columns([0.62, 0.38], gap="large")

    with col_left:
        st.markdown("##### פיד מידע")

        # Source filters
        src_cols = st.columns(5)
        sources_list = list(SOURCE_META.items())
        for si, (src_key, src_info) in enumerate(sources_list):
            with src_cols[si]:
                active = src_key in st.session_state.source_filters
                label = f"{'✓ ' if active else ''}{src_info['label']}"
                if st.button(label, key=f"filter_{src_key}", use_container_width=True):
                    if active:
                        st.session_state.source_filters.discard(src_key)
                    else:
                        st.session_state.source_filters.add(src_key)
                    st.rerun()

        st.markdown("")

        # ── Time range filter ──────────────────────────────────
        _time_options = {"היום": 1, "שבוע אחרון": 7, "חודש אחרון": 30, "הכל": None}
        time_filter = st.radio(
            "הצג מידע מ:",
            options=list(_time_options.keys()),
            horizontal=True,
            index=3,
            key="time_filter",
        )
        _days = _time_options[time_filter]
        _now = datetime.now()

        def _in_range(item: dict) -> bool:
            if _days is None:
                return True
            try:
                ts = datetime.fromisoformat(item.get("timestamp", ""))
                return (_now - ts) <= timedelta(days=_days)
            except Exception:
                return True

        feeds = company.get("feeds", [])
        filtered_feeds = [f for f in feeds if f.get("source") in st.session_state.source_filters]
        time_filtered = [f for f in filtered_feeds if _in_range(f)]

        st.caption(f"מציג {len(time_filtered)} מתוך {len(feeds)} פריטים")
        st.markdown("")

        if not time_filtered:
            st.info("אין פריטים להצגה. שנה את הסינון או הוסף פריט חדש.")
        else:
            for item in time_filtered:
                src = item.get("source", "other")
                meta = SOURCE_META.get(src, SOURCE_META["other"])
                with st.container():
                    c1, c2 = st.columns([0.9, 0.1])
                    with c1:
                        st.markdown(
                            f"<span class='feed-badge' style='background:{meta['bg']};color:{meta['color']}'>"
                            f"{meta['icon']} {meta['label']}</span>",
                            unsafe_allow_html=True
                        )
                        title = item.get("title", "")
                        url = item.get("url", "")
                        if url:
                            st.markdown(f"**[{title}]({url})**")
                        else:
                            st.markdown(f"**{title}**")
                        notes = item.get("notes", "")
                        if notes:
                            st.caption(f"📝 {notes}")
                        ts = format_timestamp(item.get("timestamp", ""))
                        st.caption(ts)
                    with c2:
                        if st.button("✕", key=f"del_{item['id']}", help="מחק פריט"):
                            delete_feed_item(data, company["id"], item["id"])
                            st.rerun()
                    st.markdown("<hr style='border:none;border-top:0.5px solid #F0F0F0;margin:4px 0'>", unsafe_allow_html=True)

    with col_right:
        # Stats
        feeds_all = company.get("feeds", [])
        s_li = sum(1 for f in feeds_all if f.get("source") == "linkedin")
        s_go = sum(1 for f in feeds_all if f.get("source") == "google")
        s_ma = sum(1 for f in feeds_all if f.get("source") == "maya")
        s_mn = sum(1 for f in feeds_all if f.get("source") == "manual")

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown(f"<div class='stat-mini'><div class='stat-num'>{s_li}</div><div class='stat-lbl'>LinkedIn</div></div>", unsafe_allow_html=True)
        with sc2:
            st.markdown(f"<div class='stat-mini'><div class='stat-num'>{s_go}</div><div class='stat-lbl'>Google</div></div>", unsafe_allow_html=True)
        sc3, sc4 = st.columns(2)
        with sc3:
            st.markdown(f"<div class='stat-mini'><div class='stat-num'>{s_ma}</div><div class='stat-lbl'>מאיה</div></div>", unsafe_allow_html=True)
        with sc4:
            st.markdown(f"<div class='stat-mini'><div class='stat-num'>{s_mn}</div><div class='stat-lbl'>ידני</div></div>", unsafe_allow_html=True)

        st.markdown("")

        # ── Google News refresh ────────────────────────────────
        if st.button("🔄 רענן חדשות", key="refresh_news", use_container_width=True):
            with st.spinner("מושך חדשות..."):
                new_items = fetch_news_for_company(company)
            existing_titles = {f.get("title", "") for f in company.get("feeds", [])}
            added = 0
            for ni in new_items:
                if ni["title"] not in existing_titles:
                    add_feed_item(data, company["id"], "google", ni["title"], ni["url"])
                    added += 1
            if added > 0:
                st.success(f"נוספו {added} פריטים חדשים")
            else:
                st.info("אין פריטים חדשים")
            st.rerun()

        st.markdown("")

        # Add item form
        st.markdown("##### הוסף פריט")
        with st.form("add_feed_form", clear_on_submit=True):
            new_src = st.selectbox(
                "מקור",
                options=list(SOURCE_META.keys()),
                format_func=lambda k: SOURCE_META[k]["label"],
                key="new_src_sel"
            )
            new_title = st.text_area("כותרת / תיאור", placeholder="מה גילית? הוסף קישור, ציטוט, הערה...", height=80)
            new_url = st.text_input("קישור (אופציונלי)", placeholder="https://...")
            new_notes = st.text_input("הערות (אופציונלי)", placeholder="הקשר נוסף...")
            submitted = st.form_submit_button("➕ הוסף לפיד", use_container_width=True, type="primary")
            if submitted and new_title.strip():
                add_feed_item(data, company["id"], new_src, new_title.strip(), new_url.strip(), new_notes.strip())
                st.rerun()

        # ── Keywords chip UI ───────────────────────────────────
        st.markdown("##### מילות מפתח")
        st.caption("מילות המפתח האלה ישמשו לסריקת חדשות אוטומטית")
        keywords = company.get("keywords", [])
        if keywords:
            for kw in keywords:
                kw_col, del_col = st.columns([0.82, 0.18])
                with kw_col:
                    st.markdown(f"<span class='kw-chip'>{kw}</span>", unsafe_allow_html=True)
                with del_col:
                    if st.button("✕", key=f"del_kw_{company['id']}_{kw}", help=f"הסר {kw}"):
                        remove_keyword(data, company["id"], kw)
                        st.rerun()
        else:
            st.caption("אין מילות מפתח עדיין.")

        add_col, btn_col = st.columns([0.72, 0.28])
        with add_col:
            new_kw_input = st.text_input(
                "מילת מפתח",
                placeholder="לדוגמה: Q2 2025",
                key="add_kw_input",
                label_visibility="collapsed",
            )
        with btn_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("הוסף", key="do_add_kw", use_container_width=True):
                if new_kw_input.strip():
                    add_keyword(data, company["id"], new_kw_input.strip())
                    st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2: FINANCIALS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_fin:
    fin = company.get("financials", {})
    periods = fin.get("periods", [])
    sections = fin.get("sections", [])

    col_fin_hdr, col_fin_btn = st.columns([0.7, 0.3])
    with col_fin_hdr:
        st.markdown("##### דוחות כספיים")
        st.caption("יחידות: אלפי ₪ / $ לפי החברה")
    with col_fin_btn:
        c1, c2 = st.columns(2)
        with c1:
            edit_label = "✏️ עריכה" if not st.session_state.fin_edit_mode else "✅ סיים"
            if st.button(edit_label, key="toggle_edit", use_container_width=True):
                st.session_state.fin_edit_mode = not st.session_state.fin_edit_mode
                st.rerun()
        with c2:
            if fin.get("sections"):
                xlsx_bytes = export_company_financials(company)
                st.download_button(
                    "⬇️ Excel",
                    data=xlsx_bytes,
                    file_name=f"{company['name']}_financials.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

    # ── Maya PDF import ───────────────────────────────────────
    with st.expander("📥 ייבוא דוח מאיה (PDF)", expanded=False):
        st.markdown(
            "העלה קובץ PDF של דוח כספי מאתר מאיה — המערכת תחלץ את הנתונים ותמלא את הטבלה."
        )
        uploaded = st.file_uploader("בחר קובץ PDF", type=["pdf"], key="maya_upload")
        if uploaded:
            col_pdf1, col_pdf2 = st.columns(2)
            with col_pdf1:
                target_period = st.text_input("שם תקופה", placeholder="Q2-25")
            with col_pdf2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("ייבא נתונים", type="primary", key="do_import"):
                    st.info("ייבוא PDF מלא יהיה זמין בגרסה הבאה. כרגע ניתן להזין ידנית בטבלה למטה.")

    if not sections:
        st.info("עדיין אין דוחות כספיים לחברה זו. הוסף סעיף ראשון למטה.")
    else:
        # ── Render financial table ─────────────────────────────
        import pandas as pd

        for sec_idx, sec in enumerate(sections):
            with st.container():
                st.markdown(
                    f"<div style='background:#EEEDFE;color:#5349C8;font-weight:600;"
                    f"font-size:13px;padding:6px 12px;border-radius:6px 6px 0 0;"
                    f"border:0.5px solid #C8C3ED'>{sec['name']}</div>",
                    unsafe_allow_html=True
                )

                if st.session_state.fin_edit_mode:
                    # Editable table using data_editor
                    rows_data = []
                    for row in sec.get("rows", []):
                        row_dict = {"סעיף": row["label"]}
                        for pi, period in enumerate(periods):
                            val = row["values"][pi] if pi < len(row["values"]) else 0
                            row_dict[period] = val
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

                    # Save edits back
                    for ri, row in edited.iterrows():
                        for pi, period in enumerate(periods):
                            try:
                                val = float(row[period]) if row[period] is not None else 0
                                update_financial_cell(data, company["id"], sec_idx, ri, pi, val)
                            except Exception:
                                pass

                    # Add row
                    with st.form(f"add_row_{sec_idx}", clear_on_submit=True):
                        new_row_label = st.text_input("שם שורה חדשה", key=f"new_row_lbl_{sec_idx}", placeholder="לדוגמה: הכנסות ממנויים")
                        if st.form_submit_button("➕ הוסף שורה"):
                            if new_row_label.strip():
                                add_financial_row(data, company["id"], sec_idx, new_row_label.strip())
                                st.rerun()

                else:
                    # Read-only display table
                    rows_data = []
                    for row in sec.get("rows", []):
                        row_dict = {"סעיף": row["label"]}
                        for pi, period in enumerate(periods):
                            val = row["values"][pi] if pi < len(row["values"]) else 0
                            row_dict[period] = f"{val:,.0f}" if isinstance(val, (int, float)) else val
                        rows_data.append(row_dict)

                    # Total row
                    _total_label = sec.get('total_label', 'סה"כ')
                    total_dict = {"סעיף": f"📌 {_total_label}"}
                    for pi, period in enumerate(periods):
                        val = sec["total"][pi] if pi < len(sec.get("total", [])) else 0
                        total_dict[period] = f"{val:,.0f}" if isinstance(val, (int, float)) else val
                    rows_data.append(total_dict)

                    df_show = pd.DataFrame(rows_data)
                    st.dataframe(
                        df_show,
                        use_container_width=True,
                        hide_index=True,
                    )

                st.markdown("")

    # ── Add section ───────────────────────────────────────────
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
