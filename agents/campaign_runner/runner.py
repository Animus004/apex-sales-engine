"""
Agent 3: Campaign Runner
Reads the lead queue, enforces calling hours, calls AnimusDialerEngine via bridge.
All logic is pure Python - no FastAPI, no HTTP except the DialerBridge call.
"""
import csv, json, os, logging, time
from datetime import datetime, time as dtime
from typing import Optional

logger = logging.getLogger("sales.campaign_runner")

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.json")
CAT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "catalog", "alibaba_products.json")

def _cfg() -> dict:
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def _catalog() -> list:
    try:
        with open(CAT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def _product_for_sku(sku: str) -> Optional[dict]:
    for p in _catalog():
        if p.get("sku") == sku:
            return p
    return _catalog()[0] if _catalog() else None

def _in_calling_window() -> bool:
    cfg = _cfg()
    now = datetime.now().time()
    try:
        start_h, start_m = map(int, cfg.get("calling_window_start","10:00").split(":"))
        end_h, end_m = map(int, cfg.get("calling_window_end","19:00").split(":"))
        return dtime(start_h, start_m) <= now <= dtime(end_h, end_m)
    except:
        return True

class CampaignRunner:
    def __init__(self, campaign_id: str, lead_file: str, product_sku: str = ""):
        self.campaign_id = campaign_id
        self.lead_file = lead_file
        self.product_sku = product_sku
        self.outcomes: list[dict] = []
        self._running = False

    def run(self, dry_run: bool = False) -> list[dict]:
        """Run the campaign. Blocks until all leads are processed."""
        from agents.lead_harvester.harvester import load_pending_leads
        from dialer.bridge import start_call, get_outcome, health_check

        if not health_check():
            logger.error("[CAMPAIGN] AnimusDialerEngine not reachable at localhost:8098")
            return []

        cfg = _cfg()
        leads = load_pending_leads(limit=100)
        logger.info(f"[CAMPAIGN {self.campaign_id}] Starting with {len(leads)} leads")

        for lead in leads:
            if not self._running and not dry_run:
                break
            if not _in_calling_window():
                logger.info("[CAMPAIGN] Outside calling window - pausing")
                time.sleep(300)
                continue

            phone = lead.get("phone","").strip()
            sku = self.product_sku or lead.get("product_sku","")
            product = _product_for_sku(sku)

            if not phone or not product:
                logger.warning(f"[CAMPAIGN] Skipping lead - missing phone or product: {lead}")
                continue

            if dry_run:
                logger.info(f"[DRY RUN] Would call {phone} for {product['name']}")
                self.outcomes.append({"phone": phone, "status": "DRY_RUN"})
                continue

            logger.info(f"[CAMPAIGN] Dialing {phone} - {lead.get('name','?')} @ {lead.get('company','?')}")
            call_id = start_call(phone, lead, product, self.campaign_id)

            if not call_id:
                logger.error(f"[CAMPAIGN] Failed to start call to {phone}")
                self.outcomes.append({"phone": phone, "status": "ERROR"})
                continue

            outcome = get_outcome(call_id, max_wait=300)
            outcome["lead"] = lead
            outcome["product_sku"] = sku
            self.outcomes.append(outcome)
            logger.info(f"[CAMPAIGN] Call {call_id} done: {outcome.get('status')}")

            # Pace between calls
            pace = int(cfg.get("dial_pace_seconds", 15))
            time.sleep(pace)

        logger.info(f"[CAMPAIGN {self.campaign_id}] Done. {len(self.outcomes)} calls processed.")
        return self.outcomes

    def start(self):
        self._running = True

    def stop(self):
        self._running = False
