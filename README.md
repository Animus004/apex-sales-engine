# Apex B2B Sales Intelligence & Audit Engine (`apex-sales-engine`)

> **Autonomous Lead Discovery Pipeline (`ScoutAgent`), B2B Lead Enrichment & Audit Engine (`auditor.audit_lead`), and Automated Multi-Agent Prospecting.**

Apex Sales Engine is an enterprise-grade outbound sales intelligence and automated prospecting platform. Engineered to identify high-probability B2B wholesale buyers, systematically audit and score their commercial viability, and trigger autonomous AI-driven outbound voice prospecting via the carrier-grade **AnimusDialerEngine** telephony bridge.

---

## Architecture Overview

All agents execute within a **single unified Python runtime** utilizing direct in-memory function calls. There is zero inter-agent HTTP latency or microservice overhead. Only the isolated telecom bridge (`dialer/bridge.py`) communicates over HTTP to interact with the local SIP telephony daemon.

```
                           ┌───────────────────────────────────────────────┐
                           │          Public B2B Catalogs & Directories    │
                           └──────────────────────┬────────────────────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │     ScoutAgent      │
                                       │  (Lead Discovery)   │
                                       └──────────┬──────────┘
                                                  │ (raw candidates)
                                                  ▼
                                       ┌─────────────────────┐
                                       │ auditor.audit_lead  │
                                       │ (Enrichment & Score)│
                                       └──────────┬──────────┘
                                                  │ (QUALIFIED score >= 6)
                                                  ▼
                                       ┌─────────────────────┐
                                       │  Lead Queue (CSV)   │
                                       └──────────┬──────────┘
                                                  │
                   ┌──────────────────────────────┴──────────────────────────────┐
                   │                                                             │
                   ▼                                                             ▼
        ┌─────────────────────┐                                       ┌─────────────────────┐
        │   CampaignRunner    │                                       │   CatalogWatcher    │
        │(Autonomous Dialing) │                                       │ (Price & MOQ Intel) │
        └──────────┬──────────┘                                       └─────────────────────┘
                   │ HTTP REST (Port 8098)
                   ▼
        ┌─────────────────────┐
        │  AnimusDialerEngine │ (Carrier SIP / JioFiber LAN / Android Handheld)
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │     CRMWriter       │──► [Structured CRM Log / Google Sheets]
        │ (Structured Mistral)│──► [Followup Dispatcher -> WhatsApp / Email]
        └─────────────────────┘
```

---

## Key Highlights & Core Capabilities

### 1. Lead Discovery Pipeline (`ScoutAgent`)
- **Multi-Source Discovery:** Systematically scrapes and ingests candidate B2B buyers across wholesale platforms, public business registries, e-commerce brand databases, and merchant directories.
- **Entity Normalization:** Standardizes corporate identity, phone numbers into strict E.164 formats (`+91...`), business category tags, and procurement contact roles.
- **Direct Pipe to Audit:** Seamlessly pipes candidate batches directly into `auditor.audit_lead` without intermediate queuing or manual triage.
- **Automated Enqueueing:** Automatically validates, filters, and commits qualified records directly into the campaign queue (`data/leads/harvested_leads.csv`).

### 2. B2B Lead Enrichment & Audit Engine (`auditor.audit_lead`)
- **Multi-Dimensional Commercial Viability Audit:**
  - **Quality Scoring (1-10):** Evaluates overall buyer legitimacy, commercial fit, and procurement capability.
  - **Margin Potential & Unit Economics:** Analyzes the target product's wholesale FOB pricing (e.g. Alibaba volume discount tiers) against estimated retail prices to determine gross margin viability (typically 70%+).
  - **MOQ Feasibility:** Audits the prospect's volume capacity against supplier Minimum Order Quantities (MOQ).
  - **Strategic Pitch Angle:** Generates customized value propositions and objection-handling strategies tailored specifically to the prospect's industry.
  - **Definitive Qualification Decisions:** Assigns actionable status: `QUALIFIED` (score $\ge$ 6), `NURTURE` (score 4-5), or `DISQUALIFIED` (score < 4).
- **Multi-Provider LLM Waterfall:** Executes structured evaluations across **Groq (Qwen 2.5 / Llama 3.3)** $\to$ **Mistral (ministral-8b)** $\to$ **Gemini 2.0 Flash** $\to$ **OpenRouter**, with automatic 429 rate-limit cooldowns and resilient heuristic fallbacks.

### 3. Automated Prospecting & Autonomous Telephony
- **Autonomous Outbound Campaigns:** `CampaignRunner` schedules and drives outbound campaigns, enforcing strict calling windows (e.g. 10:00 to 19:00), per-lead retry schedules (busy vs no-answer cadences), and dial pacing.
- **Carrier-Grade Telephony Bridge:** Dispatches outbound calls through `AnimusDialerEngine` over JioFiber SIP / LAN lines with sub-second voice latency and real-time audio streaming.
- **Structured CRM Synthesis:** Post-call conversational transcripts are immediately audited by `CRMWriter` using Mistral structured outputs to record call outcome, interest score (1-10), key objections, and recommended follow-up actions.
- **Multi-Channel Engagement:** Triggers automated follow-up assets (product spec sheets, sample pricing, WhatsApp messages) for high-intent buyers.

---

## LLM Provider Stack

| Provider | Default Model | Primary Use Case |
|---|---|---|
| **Groq** | `qwen/qwen3.8-27b` / `llama-3.3-70b` | Real-time low-latency voice responses & candidate scoring |
| **Mistral** | `ministral-8b-latest` | B2B lead audits, CRM JSON extraction, and structured output |
| **Gemini** | `gemini-2.0-flash` | Deep product catalog parsing & long-form contract analysis |
| **OpenRouter** | `openrouter/auto` | High-load overflow and global fallback |

---

## Directory Structure

```
apex-sales-engine/
├── agents/                     # Multi-agent crew implementations
│   ├── campaign_runner/        # Outbound call scheduler & cadence engine
│   ├── catalog_watcher/        # Alibaba wholesale price & MOQ monitor
│   ├── crm_writer/             # Post-call outcome parser & CRM logger
│   ├── followup_dispatcher/    # WhatsApp and email collateral dispatcher
│   ├── lead_harvester/         # ScoutAgent & directory harvester
│   └── market_intel/           # Competitor pricing and margin benchmark
├── auditor.py                  # Top-level auditor module export
├── engine/                     # Core sales intelligence engine
│   └── auditor.py              # B2B Lead Enrichment & Commercial Audit Engine
├── catalog/                    # Product catalog data (SKU specs, FOB pricing, MOQs)
│   └── alibaba_products.json
├── config/                     # Configuration and credentials
│   ├── config.example.json     # Campaign and dialing settings template
│   └── llm_keys.example.json   # Multi-provider LLM API key template
├── data/                       # Operational data stores
│   ├── leads/                  # Harvested & audited lead databases
│   ├── call_outcomes/          # Detailed CRM logs and call metrics
│   ├── cache/                  # Runtime cache
│   └── recordings/             # Call audio recordings
├── dialer/                     # Isolated HTTP bridge to AnimusDialerEngine
│   └── bridge.py
├── llm/                        # 4-tier LLM waterfall router
│   └── router.py
├── tests/                      # Unit and integration test suite
│   └── test_audit_engine.py
├── main.py                     # Unified CLI entry point
└── requirements.txt            # Python dependencies
```

---

## Quick Start

### 1. Installation

```bash
git clone https://github.com/Animus004/apex-sales-engine.git
cd apex-sales-engine
pip install -r requirements.txt
```

### 2. Configuration

Copy the example configurations and supply your API keys:

```bash
cp config/config.example.json config/config.json
cp config/llm_keys.example.json config/llm_keys.json
```

### 3. CLI Commands

```bash
# Verify connection to multi-provider LLM router (Groq/Mistral/Gemini)
python main.py test-router

# Discover and audit prospects using ScoutAgent
python main.py scout --category "Consumer Electronics" --sku "ALIBABA-SMART-MINI-01" --limit 5

# Audit a specific target B2B buyer
python main.py audit-lead --phone "+919876543210" --company "Apex Retail" --sku "ALIBABA-SMART-MINI-01"

# Check AnimusDialerEngine connectivity
python main.py health

# View pending qualified leads in the queue
python main.py list-leads

# Perform a dry-run campaign without triggering live outbound calls
python main.py dry-run --sku "ALIBABA-SMART-MINI-01"
```

### 4. Running Tests

```bash
python -m unittest tests/test_audit_engine.py
```

---

## Integration with AnimusDialerEngine

`apex-sales-engine` acts as the sales intelligence brain and automated prospecting orchestrator. Outbound voice execution is delegated to `AnimusDialerEngine` running locally at `http://localhost:8098`, allowing full integration with ISP SIP gateways (e.g. JioFiber landline) and connected mobile devices.
