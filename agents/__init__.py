"""
Apex B2B Sales Engine - Multi-Agent System
Direct function calls between agents, zero inter-agent HTTP overhead.
"""
from agents.lead_harvester.harvester import ScoutAgent, add_leads, load_pending_leads
from agents.campaign_runner.runner import CampaignRunner
from agents.crm_writer.writer import write_outcome

__all__ = [
    "ScoutAgent",
    "CampaignRunner",
    "write_outcome",
    "add_leads",
    "load_pending_leads",
]
