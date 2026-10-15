"""
AnimusSalesEngine -- Dialer Bridge
The ONLY file in AnimusSalesEngine that uses HTTP.
Thin async wrapper around AnimusDialerEngine REST API.
"""
import json, time, logging, urllib.request, urllib.error
from typing import Optional

logger = logging.getLogger("sales.dialer_bridge")

def _load_url() -> str:
    import os
    try:
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("dialer_engine_url", "http://localhost:8098")
    except:
        return "http://localhost:8098"

def start_call(phone: str, lead: dict, product: dict, campaign_id: str = "") -> Optional[str]:
    """Initiate outbound call. Returns call_id or None on failure."""
    url = _load_url() + "/call/start"
    payload = json.dumps({"phone": phone, "lead": lead, "product": product, "campaign_id": campaign_id}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("call_id")
    except Exception as e:
        logger.error(f"[BRIDGE] start_call failed: {e}")
        return None

def get_outcome(call_id: str, poll_interval: float = 2.0, max_wait: float = 300.0) -> dict:
    """Poll call status until completed. Returns final outcome dict."""
    url = _load_url() + f"/call/status/{call_id}"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
                if data.get("status") not in ("QUEUED", "DIALING", "IN_PROGRESS"):
                    return data
        except Exception as e:
            logger.warning(f"[BRIDGE] poll error: {e}")
        time.sleep(poll_interval)
    return {"status": "TIMEOUT", "call_id": call_id}

def health_check() -> bool:
    """Returns True if AnimusDialerEngine is reachable."""
    try:
        with urllib.request.urlopen(_load_url() + "/health", timeout=5) as r:
            return json.loads(r.read()).get("status") == "online"
    except:
        return False
