"""
Agent 5: CRM Writer
Writes structured call outcomes to a local CSV (and optionally Google Sheets).
Uses Mistral ministral-8b for clean JSON output.
"""
import csv, json, os, logging
from datetime import datetime

logger = logging.getLogger("sales.crm_writer")

CRM_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "call_outcomes", "crm_log.csv")
FIELDNAMES = ["call_id", "timestamp", "lead_name", "lead_company", "phone",
              "product_sku", "campaign_id", "outcome", "interest_score",
              "key_objection", "follow_up_action", "summary", "duration_s"]

def _ensure_file():
    os.makedirs(os.path.dirname(CRM_FILE), exist_ok=True)
    if not os.path.exists(CRM_FILE):
        with open(CRM_FILE, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()

def write_outcome(call_result: dict) -> dict:
    """Parse a raw call result dict and write a clean CRM row."""
    from llm.router import complete

    # Use Mistral to extract structured CRM fields from raw call result
    prompt = f"""Extract CRM fields from this call result and return JSON:

Call data:
{json.dumps(call_result, indent=2)[:1500]}

Return JSON with these exact keys:
{{
  "outcome": "INTERESTED|NOT_INTERESTED|CALLBACK|NO_ANSWER|ERROR",
  "interest_score": <int 1-10>,
  "key_objection": "<main objection or null>",
  "follow_up_action": "<what to do next>",
  "summary": "<1-2 sentences>"
}}
Only valid JSON. No markdown."""

    raw = complete(prompt, task_type="structured", max_tokens=200)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed = json.loads(clean)
    except:
        parsed = {"outcome": "UNKNOWN", "interest_score": 0, "summary": raw[:100],
                  "key_objection": None, "follow_up_action": "Manual review needed"}

    lead = call_result.get("lead", {})
    row = {
        "call_id": call_result.get("call_id", ""),
        "timestamp": datetime.now().isoformat(),
        "lead_name": lead.get("name", ""),
        "lead_company": lead.get("company", ""),
        "phone": lead.get("phone", ""),
        "product_sku": call_result.get("product_sku", ""),
        "campaign_id": call_result.get("campaign_id", ""),
        "outcome": parsed.get("outcome", "UNKNOWN"),
        "interest_score": parsed.get("interest_score", 0),
        "key_objection": parsed.get("key_objection", ""),
        "follow_up_action": parsed.get("follow_up_action", ""),
        "summary": parsed.get("summary", ""),
        "duration_s": call_result.get("duration_s", 0),
    }

    _ensure_file()
    with open(CRM_FILE, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore").writerow(row)

    logger.info(f"[CRM] Wrote outcome for {row['phone']}: {row['outcome']} (score {row['interest_score']})")
    return row
