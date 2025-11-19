# Property Maintenance Concierge Agent (Agents Capstone)

## 1. Problem
Rental property maintenance is slow and labor intensive:
- Tenants submit poorly structured issues.
- Landlords manually triage severity and safety.
- Many issues could be solved with safe self‑help (filter cleaning, breaker reset, hose straightening).
- Vendor selection (price vs speed vs quality) is ad hoc.
- Lack of systematic evaluation prior to deploying changes to production.

## 2. Solution (High-Level)
An AI concierge agent orchestrates an end‑to‑end maintenance incident flow:
1. Ingest tenant issue (title, description, priority hint, photos).
2. Perform hybrid triage (LLM + rule heuristics) for severity, safety, escalation.
3. Suggest self‑help (Gemini + KB / RAG) when safe.
4. Escalate automatically when unsafe or failed self‑help.
5. Select optimal vendor from catalog (multi-factor scoring).
6. Simulate quote / approval loop.
7. Schedule, track job completion, and process payment.
8. Close incident and record evaluation metrics for gated deployment.

## 3. Core Flow States
REPORTED → TRIAGED → (SELF_HELP_PROPOSED → SELF_HELP_SUCCEEDED | SELF_HELP_FAILED) →  
ESCALATED → VENDOR_SELECTED → QUOTE_RECEIVED → QUOTE_APPROVED → SCHEDULED → WORK_DONE → PAID → CLOSED

## 4. Architecture Overview

```
+-------------------------+        +---------------------------+
| Tenant (UI / API)       |        | Landlord (UI / Portal)    |
+-----------+-------------+        +---------------+-----------+
            | POST issue                            ^
            v                                       |
+-----------+---------------------------------------+------------------+
|  Orchestration Flow (run_scenario_through_agents) |                  |
|  - State machine + LogsRecorder                   |                  |
+-----------+-------------------+-------------------+------------------+
            |                   |                   |
            |                   |                   |
            v                   v                   v
  +---------+-----+     +-------+------+     +------+--------+
  | Triage Agent  |     | Self-Help KB |     | Vendor Select |
  | (Gemini ADK)  |     | (in-memory)  |     | (rules/scoring|
  +---------+-----+     +-------+------+     +------+--------+
            |                   |                   |
            | JSON              | Steps              | Vendor choice
            v                   |                    v
        Safety / Escalation Decision          Quote / Scheduling
            |                                            |
            v                                            v
        Payment Agent (stub)  <------------------  Vendor A2A Stubs
            |
            v
        Incident Closure + Metrics
```

## 5. Components
| Component | Purpose |
|-----------|---------|
| `MaintenanceTriageAgent` | Gemini model invocation + tool (KB) usage returning strict JSON. |
| `Knowledge Base (kb_tools)` | Simple keyword lookup of troubleshooting steps (stub for future vector search / RAG). |
| `Vendor Catalog (vendors_df)` | Static CSV loaded once; used for scoring vendors. |
| `Golden Incidents` | Evaluation-first dataset defining expected ground-truth flows. |
| `LogsRecorder` | Captures states, structured outputs, messages for evaluation & replay. |
| `Flow Orchestrator` | Implements reference end-to-end scenario progression. |
| `Stubs (utils/stubs.py)` | Deterministic placeholder logic: vendor selection, quote, availability, booking, job status, payment. |
| `JSON Extraction Utility` | Cleans LLM fenced code blocks before parsing. |

## 6. Data Sets (Evaluation Gated Deployment)
- `golden_incidents_jsonl`: Canonical scenarios with expected state sequence and constraints.
- `vendors_df`: Service providers with pricing, rating, speed, geography.
Evaluation gating: A change (prompt, scoring rule, selection weight) must not regress golden scenario outcomes (sequence match, cost thresholds, safety decisions) before merging.

## 7. Evaluation Strategy
| Metric | Source | Purpose |
|--------|--------|---------|
| State sequence match | `logs_rec.states` vs ground truth | Ensures no unintended flow regressions. |
| Safety escalation correctness | Triaged label vs severity ground truth | Avoid misclassified emergencies. |
| Vendor acceptance | Vendor id ∈ acceptable_vendors | Maintains selection quality. |
| Cost compliance | Quote total ≤ max_budget | Prevent runaway pricing. |
| Self-help success handling | Branch correctness | Avoid unnecessary escalation. |

Automated test: `tests/test_flow_golden_incidents.py` (can be parametrized later) runs each golden scenario and asserts sequence parity.

## 8. Setup

### 8.1 Requirements
- Python 3.10+
- Poetry
- Google AI Studio API Key (Gemini) in `.env`

### 8.2 Install
```bash
poetry install
```

### 8.3 Environment (.env)
```
GOOGLE_API_KEY=YOUR_KEY
GOOGLE_VERTEX_PROJECT=optional-gcp-project
GOOGLE_VERTEX_LOCATION=us-central1
GOOGLE_VERTEXAI=false
```

### 8.4 Run Single Scenario
```bash
poetry run python -m src.main
```

### 8.5 Run Tests (Single golden scenario)
```bash
poetry run pytest -k test_run_scenario_single_golden -vv
```

## 9. Key Files
```
src/
  agents/
    maintenance_triage_agent.py     # LLM triage agent
  tools/
    kb_tools.py                      # In-memory KB
  flow/
    main_flow.py                     # Orchestration logic
  data/
    golden_incidents.py              # Golden JSONL loader
    vendors.py                       # vendors_df singleton
  utils/
    json_utils.py                    # extract_json_from_llm_output
    stubs.py                         # deterministic simulation functions
tests/
  test_flow_golden_incidents.py      # Evaluation tests
```

## 10. Extensibility / Generalization
The same pattern can generalize:
- IT Helpdesk (ticket triage + self-help + escalation).
- Field Equipment Maintenance (sensor anomaly → LLM triage → technician dispatch).
- Healthcare Non-emergency Triage (symptom intake → safe advice → clinician escalation).
Replace KB, vendor catalog, and rule heuristics; keep orchestration skeleton + evaluation gating.

## 11. Future Enhancements
| Area | Planned Improvement |
|------|---------------------|
| KB / RAG | Replace keyword matching with embeddings + semantic filters. |
| Vendor Selection | Multi-objective optimization (Pareto frontier: cost vs speed vs rating). |
| Safety Model | Dedicated classifier + structured hazard ontology. |
| Image Use | Add vision model call on `photo_tags` for richer context. |
| Streaming UX | Real-time tenant messaging endpoints (WebSocket). |
| Metrics | Persist evaluation runs (pass/fail diff) to a registry. |
| Prompt Versioning | Hash + semver stored alongside test outcomes. |
| Payment | Integrate real payment API and fraud checks. |

## 12. Deployment Gating Workflow
```
[Dev Branch Change] -> [Run Golden Scenario Tests] -> PASS?
     |                                    |
   FAIL                                   PASS
     |                                     v
[Revise Prompt / Logic]            [Record metrics + merge]
                                     |
                                [Stage Deployment]
                                     |
                             [Shadow / Canary Compare]
                                     |
                                [Full Production Rollout]
```

## 13. Running Without LLM (Offline Mode)
Set `USE_GEMINI=false` (add logic) and bypass triage agent, falling back to rules only—preserves evaluation determinism.

## 14. Security / Safety Considerations
- Emergency detection prioritized (gas leak, critical HVAC).
- JSON schema enforcement reduces prompt injection risk.
- API key loaded from environment; avoid committing secrets.

## 15. License
MIT (add LICENSE file as needed).

## 16. Quick Start Snippet
```python
from src.flow.main_flow import run_scenario_through_agents
from src.data.golden_incidents import load_golden_incidents
import asyncio

scenario = load_golden_incidents()[0]
logs = asyncio.run(run_scenario_through_agents(scenario))
print(logs.states)
```

## 17. Troubleshooting
| Issue | Fix |
|-------|-----|
| Missing API key | Ensure `.env` + `load_dotenv()` in entrypoint/test. |
| Parsing JSON fails | Check fenced ```json blocks; uses json_utils extractor. |
| Import errors | Run as module: `python -m src.main`. |
| Test regressions | Compare `logs_rec.states` vs golden expected sequence. |

## 18. Glossary
- Self-Help: Safe, guided tenant actions to resolve minor issues.
- Escalation: Moving incident to vendor / professional intervention.
- Golden Scenario: Canonical incident with fixed expected outcome.
- Evaluation Gating: Blocking deployment until tests over goldens pass.

Concise, evaluation-first, modular. Ready for incremental production hardening.