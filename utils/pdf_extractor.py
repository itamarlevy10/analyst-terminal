import anthropic
import base64
import json
import re


def extract_financials_from_pdf(pdf_bytes: bytes, period_name: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    prompt = f"""זהו דוח כספי רבעוני של חברה ישראלית מאתר מאיה.

חלץ את הנתונים הבאים בלבד והחזר JSON בלבד, ללא markdown, ללא טקסט נוסף:

{{
  "period": "{period_name}",
  "income_statement": {{
    "revenue": null,
    "cost_of_sales": null,
    "gross_profit": null,
    "rd_expenses": null,
    "selling_and_admin": null,
    "operating_profit": null,
    "profit_before_tax": null,
    "net_profit": null
  }},
  "kpis": {{
    "order_backlog": null,
    "active_customers": null
  }}
}}

הנחיות:
1. הכנסות = הכנסות ממכירות
2. עלות המכר = עלות המכירות (מספר שלילי)
3. הוצאות מו"פ = הוצאות מחקר ופיתוח (שלילי)
4. selling_and_admin = הוצאות מכירה ושיווק + הוצאות הנהלה וכלליות מחוברים יחד (שלילי)
5. צבר הזמנות = באלפי דולר
6. מספרים בסוגריים כמו (22,094) = שלילי: -22094
7. החזר JSON בלבד"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
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
                {"type": "text", "text": prompt},
            ],
        }],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def financials_to_sections(data: dict) -> dict:
    """Map Claude's extracted JSON to the exact section/row structure used in companies.json."""
    inc = data.get("income_statement", {})
    kpi = data.get("kpis", {})
    return {
        "period": data.get("period"),
        "sections": {
            "רווח והפסד": {
                "הכנסות":                inc.get("revenue"),
                "עלות המכר":             inc.get("cost_of_sales"),
                "רווח גולמי":            inc.get("gross_profit"),
                'הוצאות מו"פ':           inc.get("rd_expenses"),
                "הוצאות מכירה והנהלה":   inc.get("selling_and_admin"),
                "רווח תפעולי":           inc.get("operating_profit"),
                "רווח לפני מס":          inc.get("profit_before_tax"),
                "רווח נקי":              inc.get("net_profit"),
            },
            "מדדים תפעוליים": {
                "צבר הזמנות":    kpi.get("order_backlog"),
                "לקוחות פעילים": kpi.get("active_customers"),
            },
        },
    }


def check_for_duplicates(company: dict, new_period: str) -> dict:
    """Check if a period already exists before importing."""
    existing_periods = company.get("financials", {}).get("periods", [])

    findings = {
        "exact_match": None,
        "similar_matches": [],
        "recommendation": "ok",
    }

    if new_period in existing_periods:
        findings["exact_match"] = new_period
        findings["recommendation"] = "duplicate"
        return findings

    def normalize(p: str) -> str:
        return re.sub(r"[-/ ]", "", p).upper()

    norm_new = normalize(new_period)
    for ep in existing_periods:
        if normalize(ep) == norm_new:
            findings["similar_matches"].append(ep)

    if findings["similar_matches"]:
        findings["recommendation"] = "possible_duplicate"

    return findings
