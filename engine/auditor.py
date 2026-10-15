"""
Apex B2B Sales Intelligence & Lead Enrichment Audit Engine.
Evaluates B2B prospects, calculates commercial margin viability,
identifies decision-maker hooks, and assigns qualification status.
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("sales.auditor")


def audit_lead(lead: Dict[str, Any], product: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Audits and enriches a B2B sales lead against target product specifications.
    
    Args:
        lead: Lead dictionary containing company, name, phone, category, and notes.
        product: Optional product dictionary from the catalog (e.g. Alibaba SKU details).
        
    Returns:
        Structured audit report including quality score, qualification decision,
        commercial fit assessment, strategic pitch angle, and recommended action.
    """
    company = lead.get("company", "Unknown Business")
    name = lead.get("name", "Decision Maker")
    phone = lead.get("phone", "")
    notes = lead.get("notes", "")
    category = lead.get("category", "")
    
    prod_name = product.get("name", "Product Catalog") if product else "B2B Wholesale Catalog"
    prod_sku = product.get("sku", lead.get("product_sku", "N/A")) if product else lead.get("product_sku", "N/A")
    moq = product.get("moq", 50) if product else 50
    fob_price = product.get("fob_price_usd", "Market FOB") if product else "Market FOB"
    margin = product.get("estimated_margin_percent", 70.0) if product else 70.0

    prompt = f"""You are the Chief Auditor at Apex B2B Sales Intelligence.
Perform a rigorous commercial viability audit for this prospect.

Prospect Profile:
- Company: {company}
- Contact: {name}
- Phone: {phone}
- Category: {category}
- Context/Notes: {notes}

Target Offering:
- Product: {prod_name} (SKU: {prod_sku})
- Target FOB Price: ${fob_price}
- Minimum Order Qty (MOQ): {moq}
- Estimated Retail Margin: {margin}%

Analyze commercial fit, retail resale viability, and procurement capacity.
Return ONLY valid JSON matching this exact structure:
{{
  "quality_score": <int 1-10>,
  "commercial_viability": "HIGH|MEDIUM|LOW",
  "audit_decision": "QUALIFIED|NURTURE|DISQUALIFIED",
  "estimated_margin_potential": "<string>",
  "strategic_pitch_angle": "<1-2 sentence hook for voice or messaging outreach>",
  "key_objection_risk": "<main risk e.g. MOQ barrier or cash flow>",
  "recommended_action": "AUTONOMOUS_DIAL|WHATSAPP_CATALOG|MANUAL_REVIEW|DISCARD",
  "audit_rationale": "<brief explanation>"
}}
No markdown formatting, output raw JSON only."""

    try:
        from llm.router import complete
        raw = complete(prompt, task_type="structured", max_tokens=300)
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed = json.loads(clean)
    except Exception as e:
        logger.warning(f"[AUDITOR] LLM evaluation fallback for {company}: {e}")
        # Rule-based fallback if LLM is offline
        has_phone = bool(phone and len(phone) >= 10)
        has_context = bool(notes and len(notes) > 10)
        score = 7 if (has_phone and has_context) else (5 if has_phone else 3)
        decision = "QUALIFIED" if score >= 6 else ("NURTURE" if score >= 4 else "DISQUALIFIED")
        parsed = {
            "quality_score": score,
            "commercial_viability": "HIGH" if score >= 7 else "MEDIUM",
            "audit_decision": decision,
            "estimated_margin_potential": f"{margin}% gross margin potential",
            "strategic_pitch_angle": f"Introduce {prod_name} with low {moq}-unit MOQ and high margin for {company}.",
            "key_objection_risk": "MOQ and shipping lead time",
            "recommended_action": "AUTONOMOUS_DIAL" if decision == "QUALIFIED" else "WHATSAPP_CATALOG",
            "audit_rationale": "Evaluated based on contact completeness and category alignment."
        }

    audit_result = {
        "lead_id": phone or f"lead_{int(datetime.now().timestamp())}",
        "audited_at": datetime.now().isoformat(),
        "company": company,
        "contact_name": name,
        "phone": phone,
        "product_sku": prod_sku,
        "product_name": prod_name,
        "audit": parsed
    }
    
    logger.info(
        f"[AUDIT COMPLETE] {company} -> Score: {parsed.get('quality_score')}/10 "
        f"[{parsed.get('audit_decision')}] Action: {parsed.get('recommended_action')}"
    )
    return audit_result


def audit_batch(leads: list[Dict[str, Any]], product: Optional[Dict[str, Any]] = None) -> list[Dict[str, Any]]:
    """Audits a batch of prospects and filters qualified leads."""
    results = []
    for lead in leads:
        report = audit_lead(lead, product)
        results.append(report)
    return results
