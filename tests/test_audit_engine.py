"""
Unit and integration tests for Apex B2B Sales Intelligence & Audit Engine.
Verifies ScoutAgent discovery, auditor.audit_lead qualification, and lead pipelines.
"""
import unittest
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import auditor
from agents.lead_harvester.harvester import ScoutAgent, load_pending_leads
from agents.campaign_runner.runner import _product_for_sku


class TestApexSalesEngine(unittest.TestCase):

    def test_audit_lead_direct_call(self):
        lead = {
            "company": "Apex Global Retailers",
            "name": "Karan Malhotra",
            "phone": "+919876543210",
            "category": "Consumer Electronics",
            "notes": "Looking for 500 units of AMOLED smart watches for upcoming festival sale."
        }
        product = _product_for_sku("ALIBABA-SMART-MINI-01")
        report = auditor.audit_lead(lead, product=product)

        self.assertIn("audit", report)
        self.assertIn("quality_score", report["audit"])
        self.assertIn("audit_decision", report["audit"])
        self.assertIn("strategic_pitch_angle", report["audit"])
        self.assertIn("commercial_viability", report["audit"])
        self.assertEqual(report["company"], "Apex Global Retailers")

    def test_scout_agent_discovery(self):
        scout = ScoutAgent(default_category="Consumer Electronics")
        discovered = scout.discover_raw_leads(limit=3)
        self.assertGreaterEqual(len(discovered), 1)
        self.assertIn("phone", discovered[0])
        self.assertIn("company", discovered[0])

    def test_scout_and_audit_pipeline(self):
        scout = ScoutAgent(default_category="Home and Living")
        product = _product_for_sku("ALIBABA-DIFFUSER-PRO-02")
        pipeline_results = scout.scout_and_audit(category="Home and Living", product=product, limit=2, auto_enqueue=False)
        self.assertGreaterEqual(len(pipeline_results), 1)
        first = pipeline_results[0]
        self.assertIn("audit", first)


if __name__ == "__main__":
    unittest.main()
