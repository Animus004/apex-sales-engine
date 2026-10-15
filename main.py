"""
Apex B2B Sales Engine -- Single-Process Entry Point
All agents run in this process. Direct function calls only, zero inter-agent HTTP overhead.
"""
import sys
import os
import json
import logging
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sales.main")


def cmd_test_router():
    """Test all 4 LLM providers."""
    from llm.router import complete
    print("Testing Groq (fast)...")
    r = complete("Say: Groq online", task_type="fast", max_tokens=20)
    print("  Groq:", r.encode("ascii", "replace").decode("ascii"))
    print("Testing Mistral (structured)...")
    r2 = complete("Return: {status: ok}", task_type="structured", max_tokens=20)
    print("  Mistral:", r2.encode("ascii", "replace").decode("ascii"))
    print("Router OK")


def cmd_list_leads():
    """List all pending leads."""
    from agents.lead_harvester.harvester import load_pending_leads
    leads = load_pending_leads()
    print(f"Found {len(leads)} pending leads:")
    for l in leads[:10]:
        print(f"  {l.get('phone')} - {l.get('name')} @ {l.get('company')} [{l.get('product_sku','')}]")


def cmd_scout(category: str = "Consumer Electronics", sku: str = "", limit: int = 5):
    """Run ScoutAgent lead discovery pipeline and audit candidates."""
    from agents.lead_harvester.harvester import ScoutAgent
    from agents.campaign_runner.runner import _product_for_sku

    product = _product_for_sku(sku) if sku else None
    scout = ScoutAgent(default_category=category)
    print(f"Running ScoutAgent discovery pipeline for category: '{category}'...")
    results = scout.scout_and_audit(category=category, product=product, limit=limit, auto_enqueue=True)
    print(f"\n[SCOUT COMPLETE] Processed {len(results)} prospects:")
    for r in results:
        audit = r.get("audit", {})
        print(f"  -> {r.get('company')} ({r.get('contact_name')}) | Phone: {r.get('phone')}")
        print(f"     Score: {audit.get('quality_score')}/10 | Decision: {audit.get('audit_decision')} | Margin: {audit.get('estimated_margin_potential')}")
        print(f"     Pitch: {audit.get('strategic_pitch_angle')}\n")


def cmd_audit_lead(phone: str, company: str = "Target Corp", name: str = "Purchasing Head", sku: str = ""):
    """Run B2B lead enrichment/audit engine on a specific target."""
    import auditor
    from agents.campaign_runner.runner import _product_for_sku

    product = _product_for_sku(sku) if sku else None
    lead = {
        "phone": phone,
        "company": company,
        "name": name,
        "product_sku": sku,
        "notes": "Targeted B2B prospective buyer."
    }
    report = auditor.audit_lead(lead, product=product)
    print(json.dumps(report, indent=2))


def cmd_dry_run(campaign_id: str = "test-001", product_sku: str = ""):
    """Dry run a campaign (no real calls)."""
    from agents.lead_harvester.harvester import load_pending_leads
    leads = load_pending_leads()
    print(f"DRY RUN - would call {len(leads)} leads")
    for l in leads[:5]:
        print(f"  -> {l.get('phone')} | {l.get('name')} | {l.get('product_sku','')}")


def cmd_health():
    """Check AnimusDialerEngine health."""
    from dialer.bridge import health_check
    ok = health_check()
    print("AnimusDialerEngine:", "ONLINE" if ok else "OFFLINE (start AnimusDialerEngine first)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apex B2B Sales Engine CLI")
    parser.add_argument("command", choices=["test-router", "list-leads", "scout", "audit-lead", "dry-run", "health"],
                        help="Command to run")
    parser.add_argument("--campaign-id", default=f"campaign_{datetime.now().strftime('%Y%m%d_%H%M')}")
    parser.add_argument("--sku", default="", help="Product SKU to pitch")
    parser.add_argument("--category", default="Consumer Electronics", help="Product category for scouting")
    parser.add_argument("--phone", default="+919876543210", help="Phone number for audit-lead")
    parser.add_argument("--company", default="Sample Enterprise", help="Company name for audit-lead")
    parser.add_argument("--name", default="Decision Maker", help="Contact name for audit-lead")
    parser.add_argument("--limit", type=int, default=5, help="Limit number of leads for scout")
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(__file__))

    if args.command == "test-router":
        cmd_test_router()
    elif args.command == "list-leads":
        cmd_list_leads()
    elif args.command == "scout":
        cmd_scout(category=args.category, sku=args.sku, limit=args.limit)
    elif args.command == "audit-lead":
        cmd_audit_lead(phone=args.phone, company=args.company, name=args.name, sku=args.sku)
    elif args.command == "dry-run":
        cmd_dry_run(args.campaign_id, args.sku)
    elif args.command == "health":
        cmd_health()
