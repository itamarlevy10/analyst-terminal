import anthropic
import base64
import json
from datetime import datetime

BALANCE_SHEET_FIELDS = [
    "cash", "short_term_deposits", "pledged_deposit", "trade_receivables",
    "other_receivables", "income_tax_receivable", "inventory",
    "total_current_assets", "deferred_tax_assets", "fixed_assets",
    "right_of_use_assets", "intangible_assets", "goodwill",
    "total_non_current_assets", "total_assets", "trade_payables",
    "income_tax_payable", "other_payables", "dividend_payable",
    "current_grant_liabilities", "current_lease_liabilities",
    "total_current_liabilities", "grant_liabilities", "lease_liabilities",
    "deferred_tax_liabilities", "total_non_current_liabilities",
    "total_liabilities", "equity", "equity_ratio",
    "total_liabilities_and_equity",
]  # balance_check (31st field under "fields") is computed by our code below, never requested from Claude

_BALANCE_SHEET_PROMPT = """זהו דוח כספי (רבעוני/שנתי) של חברה ישראלית או דואלית, מאתר מאיה (TASE).
הדוח עשוי להיות בעברית, באנגלית, או משולב.

המשימה שלך: למצוא את המאזן (Balance Sheet / "מאזן" / "Statement(s) of Financial Position") בתוך המסמך,
ולחלץ ממנו את הנתונים לפי הסכמה, מעמודת התאריך העדכנית ביותר בלבד.

חשוב מאוד:
1. במאזן משווה יש בד"כ 2-3 עמודות תאריך (למשל סוף רבעון נוכחי, אותו רבעון שנה קודמת, סוף שנה קודמת).
   חלץ רק מהעמודה עם התאריך העדכני ביותר. קרא את כותרות העמודות בעיון —
   בטבלאות בעברית (RTL) סדר העמודות עלול להיות הפוך ממה שנראה טבעי לקורא אנגלית.
2. period_type ו-period_length_months נקבעים לפי אופן ההצגה הכללי של הדוח (עמוד השער, כותרת דוח
   רווח והפסד הסמוך), ולא לפי טבלת המאזן עצמה — מאזן תמיד מתואר "ליום X" (נקודת זמן), ולעולם לא
   "לתקופה של X חודשים".
   - "לשנה שהסתיימה" / "for the year ended" / דוח שנתי מלא -> annual, 12
   - "לתקופה של תשעה חודשים שהסתיימה" / "for the nine months ended" -> quarterly_cumulative, 9
   - "לתקופה של שישה חודשים" / "מחצית" / "for the six months ended" -> quarterly_cumulative, 6
   - כשמוצג רק נתון רבעוני עצמאי של 3 חודשים (לא מצטבר) -> quarterly_standalone, 3
   - אם מוצגים גם 3 חודשים עצמאי וגם מצטבר (נפוץ בדוחות רבעון 3), קבע לפי מה שהדוח עצמו מציג
     כתקופת הדיווח העיקרית — במקרה של ספק, בחר את המצטבר.
   period_end = תאריך העמודה העדכנית ביותר במאזן, בפורמט ISO (YYYY-MM-DD).
3. source_report_date = תאריך אישור/פרסום הדוח עצמו (מופיע בד"כ ליד חתימות הדירקטוריון, קרוב לעמוד
   המאזן) — זה שונה מ-period_end.
4. currency ו-units נקראים מכותרת טבלת המאזן (למשל "באלפי דולר" / "in USD thousands").
5. company = סימול המסחר (טיקר) של החברה אם מופיע, אחרת שם קצר של החברה.

כלל ברזל — אסור לנחש:
fields הוא מערך של רשומות {"name": ..., "value": ...} — הוסף רשומה רק לשדה שמופיע בפועל במאזן
עבור התקופה הזו. אם סעיף לא מופיע — פשוט אל תכלול אותו במערך בכלל (אל תמציא ערך אפס או ערך מנוחש).
אסור לחשב, להסיק, להשלים או להעריך ערך שלא מודפס במפורש. אסור להעתיק ערך מעמודת תאריך אחרת.
עדיף תמיד להשמיט שדה על פני ניחוש. זה כולל את equity_ratio — כלול אותו רק אם הדוח עצמו מציג יחס הון
עצמי מפורש (לא לחשב equity/total_liabilities_and_equity בעצמך). זה גם כולל את כל שדות ה-total_*
(total_current_assets, total_non_current_assets, total_current_liabilities,
total_non_current_liabilities, total_assets, total_liabilities, total_liabilities_and_equity) —
תמיד לקרוא אותם כשורת הסה"כ המודפסת בפועל, לא לחשב אותם בעצמך על ידי סכימת השורות.

מיפוי שדות (Hebrew / English):
- cash: מזומנים ושווי מזומנים / Cash and cash equivalents
- short_term_deposits: פיקדונות/השקעות לזמן קצר, סכום גדול, השקעה נזילה / Short-term deposits or
  investments — LARGE
- pledged_deposit: פיקדון מוגבל בשעבוד, סכום קטן, בטוחה מוגבלת / Restricted or pledged deposit —
  SMALL, שונה מ-short_term_deposits
- trade_receivables: לקוחות / Trade receivables, Accounts receivable
- other_receivables: חייבים אחרים, הוצאות מראש / Other receivables, Prepaid expenses
- income_tax_receivable: חייבים/מקדמות בגין מסים / Current taxes receivable
- inventory: מלאי / Inventory
- total_current_assets: סה"כ רכוש שוטף / Total current assets
- deferred_tax_assets: מסים נדחים (נכס) / Deferred tax assets
- fixed_assets: רכוש קבוע, נטו / Property, plant and equipment, Fixed assets net
- right_of_use_assets: נכסי זכות שימוש / Right-of-use assets
- intangible_assets: נכסים בלתי מוחשיים / Intangible assets
- goodwill: מוניטין / Goodwill
- total_non_current_assets: סה"כ רכוש לא שוטף / Total non-current assets
- total_assets: סה"כ נכסים / Total assets
- trade_payables: ספקים ונותני שירותים / Trade payables, Accounts payable
- income_tax_payable: זכאים בגין מסים / Current tax liabilities, Income tax payable
- other_payables: זכאים אחרים / Other payables, Accrued expenses
- dividend_payable: דיבידנד לשלם / Dividend payable
- current_grant_liabilities: התחייבות למענקים, חלק שוטף / Government grants payable, current
- current_lease_liabilities: התחייבויות חכירה, חלק שוטף / Lease liabilities, current
- total_current_liabilities: סה"כ התחייבויות שוטפות / Total current liabilities
- grant_liabilities: התחייבות למענקים, חלק לא שוטף / Government grants payable, non-current
- lease_liabilities: התחייבויות חכירה, חלק לא שוטף / Lease liabilities, non-current
- deferred_tax_liabilities: מסים נדחים (התחייבות) / Deferred tax liabilities
- total_non_current_liabilities: סה"כ התחייבויות לא שוטפות / Total non-current liabilities
- total_liabilities: סה"כ התחייבויות / Total liabilities
- equity: סה"כ הון עצמי / Total equity
- equity_ratio: יחס הון עצמי למאזן, רק אם מוצג מפורשות / Equity ratio (only if explicitly disclosed)
- total_liabilities_and_equity: סה"כ התחייבויות והון / Total liabilities and equity

מספרים בסוגריים כמו (1,234) הם שליליים: -1234."""


def _balance_sheet_json_schema() -> dict:
    # "fields" is an array of {name, value} entries rather than 30 nullable
    # properties — the API rejects schemas with more than 16 union/nullable-typed
    # parameters ("exponential compilation cost"), and 30 nullable numbers blew
    # past that. An entry present = the line item was printed; an entry absent =
    # null. Our own post-processing (below) expands this into a flat dict with
    # all 31 keys always present, so callers never see this wire shape.
    return {
        "type": "object",
        "properties": {
            "company": {"type": "string"},
            "period_end": {"type": "string"},
            "period_type": {
                "type": "string",
                "enum": ["annual", "quarterly_cumulative", "quarterly_standalone"],
            },
            "period_length_months": {"type": "integer", "enum": [3, 6, 9, 12]},
            "source_report_date": {"type": "string"},
            "currency": {"type": "string", "enum": ["USD", "ILS"]},
            "units": {"type": "string", "enum": ["thousands", "millions"]},
            "fields": {
                "type": "array",
                "description": (
                    "One entry per balance-sheet line item that is actually printed in "
                    "the report for this period. Omit the entry entirely for any field "
                    "not shown — never include an entry with a guessed or zero value."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "enum": BALANCE_SHEET_FIELDS},
                        "value": {"type": "number"},
                    },
                    "required": ["name", "value"],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "company", "period_end", "period_type", "period_length_months",
            "source_report_date", "currency", "units", "fields",
        ],
        "additionalProperties": False,
    }


def extract_balance_sheet_from_pdf(pdf_bytes: bytes, api_key: str, source_reference: str = "") -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": _balance_sheet_json_schema()},
        },
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64,
                    },
                },
                {"type": "text", "text": _BALANCE_SHEET_PROMPT},
            ],
        }],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude סירב לעבד את המסמך (safety refusal).")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("תגובת Claude נחתכה (max_tokens) — נסה שוב.")

    text_block = next(b for b in response.content if b.type == "text")
    raw = json.loads(text_block.text)

    # Expand the {name, value} entry array into a flat dict with all 31 keys
    # always present (None for anything Claude omitted).
    fields = {name: None for name in BALANCE_SHEET_FIELDS}
    for item in raw.get("fields", []):
        name = item.get("name")
        if name in fields:
            fields[name] = item.get("value")

    total_assets = fields.get("total_assets")
    total_liab_eq = fields.get("total_liabilities_and_equity")
    fields["balance_check"] = (
        round(total_assets - total_liab_eq, 2)
        if total_assets is not None and total_liab_eq is not None
        else None
    )

    return {
        "company": raw["company"],
        "period_end": raw["period_end"],
        "period_type": raw["period_type"],
        "period_length_months": raw["period_length_months"],
        "source_report_date": raw["source_report_date"],
        "source_reference": source_reference or f"upload-{datetime.now().strftime('%Y%m%dT%H%M%S')}",
        "fields": fields,
        "currency": raw["currency"],
        "units": raw["units"],
    }


def _check_subtotal(warnings: list[str], fields: dict, total_key: str, component_keys: list[str]) -> None:
    total = fields.get(total_key)
    components = [fields.get(k) for k in component_keys]
    if total is None or any(c is None for c in components):
        return  # incomplete set — can't verify, skip silently
    computed = round(sum(components), 2)
    if abs(computed - total) > 1:
        detail = ", ".join(f"{k}={fields.get(k)}" for k in component_keys)
        warnings.append(f'{total_key} ({total}) אינו תואם לסכום הרכיבים ({computed}): {detail}.')


def validate_balance_sheet(record: dict, existing_records: list[dict] | None = None) -> list[str]:
    """Run sanity checks on an extracted balance sheet record. Returns a list of
    warning strings (empty if nothing looks off) — the caller decides how to surface them."""
    warnings: list[str] = []
    fields = record.get("fields", {})

    balance_check = fields.get("balance_check")
    if balance_check is None:
        warnings.append("לא ניתן לאמת איזון (total_assets או total_liabilities_and_equity חסרים).")
    elif abs(balance_check) > 1:
        warnings.append(
            f"המאזן אינו מאוזן: total_assets - total_liabilities_and_equity = {balance_check} "
            f"(total_assets={fields.get('total_assets')}, "
            f"total_liabilities_and_equity={fields.get('total_liabilities_and_equity')})."
        )

    _check_subtotal(warnings, fields, "total_current_assets",
        ["cash", "short_term_deposits", "pledged_deposit", "trade_receivables",
         "other_receivables", "income_tax_receivable", "inventory"])
    _check_subtotal(warnings, fields, "total_non_current_assets",
        ["deferred_tax_assets", "fixed_assets", "right_of_use_assets",
         "intangible_assets", "goodwill"])
    _check_subtotal(warnings, fields, "total_current_liabilities",
        ["trade_payables", "income_tax_payable", "other_payables", "dividend_payable",
         "current_grant_liabilities", "current_lease_liabilities"])
    _check_subtotal(warnings, fields, "total_non_current_liabilities",
        ["grant_liabilities", "lease_liabilities", "deferred_tax_liabilities"])

    # Informational only — no H1/H2 derivation is implemented (future work); this just
    # flags that a shorter cumulative period already exists for the same company/year.
    if record.get("period_type") == "quarterly_cumulative" and existing_records:
        year = (record.get("period_end") or "")[:4]
        this_len = record.get("period_length_months")
        for other in existing_records:
            other_year = (other.get("period_end") or "")[:4]
            other_len = other.get("period_length_months")
            if (other.get("period_type") == "quarterly_cumulative"
                    and other_year == year
                    and other_len is not None and this_len is not None
                    and other_len < this_len):
                warnings.append(
                    f"קיימת כבר תקופה מצטברת קצרה יותר ({other_len} חודשים) לאותה שנה — "
                    f"ניתן יהיה בעתיד לגזור רבעון עצמאי/מחצית. לידיעה בלבד."
                )
                break

    return warnings
