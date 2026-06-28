# חצבים — דאשבורד אנליסט

דאשבורד לניהול מידע ודוחות כספיים על חברות שבמעקב, בנוי עם Streamlit.

## הרצה מקומית

```bash
pip install -r requirements.txt
streamlit run app.py
```

## פיצ'רים

- **טאב לכל חברה** עם פיד מידע, מילות מפתח ודוחות כספיים
- **פיד מידע** מ-LinkedIn, Google, מאיה, וידני
- **סינון לפי מקור**
- **טבלת דוחות כספיים** ניתנת לעריכה, עם הוספת סעיפים ותקופות
- **ייצוא Excel** בפורמט מקצועי
- **גיבוי/ייבוא** של כל הנתונים כ-JSON

## Streamlit Cloud

1. העלה ל-GitHub
2. כנס ל-[share.streamlit.io](https://share.streamlit.io)
3. חבר את הריפו, הגדר `app.py` כנקודת כניסה
4. פרס

## מבנה הפרויקט

```
├── app.py                  # האפליקציה הראשית
├── requirements.txt
├── data/
│   └── default_data.json   # נתוני ברירת מחדל
├── utils/
│   ├── data_manager.py     # CRUD + persistence
│   └── excel_export.py     # ייצוא Excel מפורמט
└── .streamlit/
    └── config.toml
```
