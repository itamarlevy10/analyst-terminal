# חצבים — Terminal Light · ערכת הטמעה ל-Streamlit (גישת iframe)

**למה זה היה מכוער קודם:** רינדור HTML עם `st.markdown` נלחם ב-Streamlit — ה-parser הופך הזחות ל-code blocks, מוסיף `<p>` משלו, וה-CSS הגלובלי של Streamlit דורס את הסטיילים. 

**הפתרון כאן:** כל טאב מרונדר כ**מסמך HTML שלם בתוך `st.components.v1.html()` (iframe)**. בתוך iframe ה-CSS של Streamlit *לא מגיע* — אז זה נראה בדיוק כמו המוקאפ. ניווט וטפסים עובדים דרך `target="_top"` שמעדכן את ה-query params של האפליקציה.

## קבצים
- **`render.py`** — ⭐ הכל כאן. הפונקציה הראשית: `page_html(...)` שמחזירה מסמך HTML שלם לטאב.
- **`assets/hazavim-mark.png`** — לוגו (כותרת + טאב).

## app.py — שלד מלא להחלפת שכבת התצוגה
```python
import base64
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from streamlit_theme import render as R

st.set_page_config(page_title="חצבים — דאשבורד אנליסט",
                   page_icon=Image.open("streamlit_theme/assets/hazavim-mark.png"),
                   layout="wide")

# מסיר padding של Streamlit כך שה-iframe ממלא את הרוחב
st.markdown("<style>#MainMenu,footer,[data-testid='stHeader']{display:none}"
            ".block-container{padding:1rem 1.2rem;max-width:1520px}</style>",
            unsafe_allow_html=True)

data = load_data()
companies = get_companies(data)
qp = st.query_params

active_id = qp.get("co") or (companies[0]["id"] if companies else None)
tab       = qp.get("tab", "feed")
active_src = set((qp.get("src") or "google,maya,linkedin,manual").split(","))

# ── פעולות שמגיעות מה-iframe (לינקים/טפסים עם target=_top) ──
def _clear(*keys):
    for k in keys:
        if k in qp: del qp[k]

if qp.get("scan"):                                   # "סרוק עכשיו"
    run_scan(active_id);            _clear("scan");   st.rerun()
if qp.get("del_kw"):                                 # ✕ על chip
    remove_keyword(data, active_id, qp["del_kw"]); save_data(data)
    _clear("del_kw");               st.rerun()
if qp.get("add_kw"):                                 # טופס הוספת מילת מפתח
    add_keyword(data, active_id, qp["add_kw"].strip()); save_data(data)
    _clear("add_kw");               st.rerun()
if qp.get("m_title"):                                # טופס דיווח ידני
    add_manual_item(data, active_id, {
        "source":  qp.get("m_src", "manual"),
        "title":   qp["m_title"].strip(),
        "url":     qp.get("m_url", ""),
        "snippet": qp.get("m_notes", ""),
    }); save_data(data)
    _clear("m_title", "m_src", "m_url", "m_notes"); st.rerun()

company = get_company(data, active_id)
fin     = company.get("financials", {})
b64     = base64.b64encode(open("streamlit_theme/assets/hazavim-mark.png", "rb").read()).decode()

# פריטי הפיד מסוננים לפי המקורות הפעילים (הלוגיקה הקיימת שלך)
feed_items = [it for it in get_feed_items(company)
              if it.get("source", "other") in active_src] if tab == "feed" else []

html = R.page_html(
    tab=tab, companies=companies, active_id=active_id, company=company, fin=fin,
    feed_items=feed_items, active_src=active_src,
    last_scan=last_scan_label(active_id), b64=b64,
)
components.html(html, height=1300, scrolling=True)   # התאם height לפי הצורך
```

## נקודות חשובות
- **גובה ה-iframe:** `components.html(..., height=N)` דורש גובה קבוע. התחל ב-1300 והגדל אם נחתך. (אופציונלי: סקריפט שמודד `document.body.scrollHeight` ושולח `postMessage` — אבל height קבוע + `scrolling=True` מספיק.)
- **מבנה הנתונים שהפונקציות מצפות לו:**
  - `company`: `{"id","name","ticker","keywords":[...], "scan_sources":[...], "financials":{...}}`
  - `financials`: `{"periods":["2025 שנתי","Q1 2025","Q1 2026"], "sections":[{"name":"רווח והפסד","rows":[{"label":"הכנסות","values":[168354,36163,67389],"total":false}, ...]}]}` (ערכים באלפי ₪; שליליים = הוצאות בסוגריים אוטומטית)
  - `feed item`: `{"source":"google","title":"...","snippet":"...","matched_keyword":"...","timestamp":"2026-06-28T08:05","source_label":"מאיה · 28.6"}`
- **קטגוריות מילות מפתח (ירוק/אדום):** `render.DEFAULT_COMPETITORS` קובע מי מתחרה (כרגע `anduril/uvision/אנדוריל`). או העבר `classify=` משלך ל-`page_html`.
- **אל תיגע ב-HTML של render.** טוויקים עיצוביים — רק בפלטה `P` או בפונקציות שב-`render.py`.
- מספרים: הפונקציות מקבלות נתונים גולמיים (אלפי ₪) ומפרמטות לבד ל-`₪67.4M` ול-%. אל תעביר מחרוזות מעוצבות.
