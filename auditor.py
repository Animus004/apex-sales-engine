"""
Top-level export for Apex B2B Sales Intelligence & Lead Enrichment Audit Engine.
Allows direct import: `import auditor; auditor.audit_lead(lead)`
"""
from engine.auditor import audit_lead, audit_batch

__all__ = ["audit_lead", "audit_batch"]
