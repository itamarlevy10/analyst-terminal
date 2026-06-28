import anthropic
import base64
import json
import re


def extract_financials_from_pdf(pdf_bytes: bytes, period_name: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    prompt = f"""זהו דוח כספי רבעוני של חברה ישראלית מאתר מאיה (TASE disclosure site).

חלץ את כל הנתונים הכספיים מהדוח והחזר JSON בלבד, ללא שום טקסט לפני או אחרי, ללא markdown:

{{
  "period": "{period_name}",
  "income_statement": {{
    "revenue": null,
    "cost_of_sales": null,
    "gross_profit": null,
    "rd_expenses": null,
    "selling_and_admin_expenses": null,
    "operating_profit": null,
    "finance_income": null,
    "finance_expenses": null,
    "profit_before_tax": null,
    "tax": null,
    "net_profit": null
  }},
  "balance_sheet": {{
    "cash": null,
    "short_term_deposits": null,
    "receivables": null,
    "inventory": null,
    "total_current_assets": null,
    "fixed_assets": null,
    "intangible_assets": null,
    "total_equity": null
  }},
  "cash_flow": {{
    "operating": null,
    "investing": null,
    "financing": null,
    "end_balance": null
  }},
  "kpis": {{
    "order_backlog": null,
    "active_customers": null
  }}
}}

חוקים:
1. מספרים בלבד — ללא סימני מטבע, ללא פסיקים, ללא אחוזים
2. הוצאות בסוגריים כמו (22,094) = מספר שלילי: -22094
3. selling_and_admin_expenses = סכום הוצאות מכירה + הנהלה וכלליות יחד (מספר שלילי)
4. אם סעיף לא קיים בדוח — השאר null
5. החזר JSON בלבד"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
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
