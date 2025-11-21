# Evaluation-Gated Multi-Agent Maintenance Orchestrator (Agents Capstone)

## 1. Problem
Rental property maintenance is slow and labor intensive:
- Unstructured tenant issue reports
- Manual severity & safety triage
- Missed self‑help opportunity
- Ad hoc vendor selection & scheduling
- Limited cost / outcome evaluation
- No gated deployment controls

## 2. Solution (High-Level)
A multi-agent, evaluation‑gated maintenance:
1. Ingest tenant incident
2. Hybrid triage (LLM + rules) → severity, safety, escalation label
3. Safe self‑help suggestion (KB tool) when allowed
4. Escalation → remote vendor agent via A2A protocol
5. Vendor selection (scoring tool) → quote → approval logic
6. Availability + booking (remote agent)
7. Job completion + payment (AP2‑style stubs)
8. Persistent or ephemeral session memory (Database vs InMemory)
9. Structured logs for evaluation gating (states, JSON outputs)

## 3. Core Flow States
REPORTED → TRIAGED → (SELF_HELP_PROPOSED → SELF_HELP_SUCCEEDED | SELF_HELP_FAILED) →  
ESCALATED → VENDOR_SELECTED → QUOTE_RECEIVED → QUOTE_APPROVED → SCHEDULED → WORK_DONE → PAID → CLOSED

## 4. Architecture Overview

```
                               +------------------------------+
                               |         Tenant / UI          |
                               |    (test scenarios / API)    |
                               +---------------+--------------+
                                               |
                                               v
+----------------------------------------------------------------------------------------------+
|                 Orchestration & Evaluation (flow/main_flow.py)                               |
|  - run_scenario_through_agents                                                               |
|  - LogsRecorder: states, messages, quote, booking, payment, vendor_logs                      |
|  - Hybrid triage: rule-based stub + LLM triage agent                                         |
|  - Evaluation-gated flow: asserts on states / outputs (tests/)                               |
+-----------------------------+------------------------------+---------------------------------+
                              |                              |
                              |                              |
                              v                              v
                +-------------+-------------+     +----------+-----------+
                |  Rule-based Triage Stub   |     |     Payment Agent    |
                |   (utils/stubs.py)        |     |  (AP2-style, stubs)  |
                +-------------+-------------+     +----------+-----------+
                              ^                              ^
                              |                              |
                              |                              |
+-----------------------------+------------------------------+---------------------------------+
|                      Maintenance Triage Agent (LLM)                                          |
|  (src/agents/maintenance_triage_agent.py + adk_agents/maintenance_triage/agent.py)          |
|                                                                                              |
|  - Root ADK Agent (Gemini)                                                                  |
|  - Tools:                                                                                    |
|      • lookup_troubleshooting_article (KB tool)                                             |
|      • select_best_vendor (vendor selection tool)                                           |
|  - Sub-agent:                                                                               |
|      • remote_vendor_agent : RemoteA2aAgent (A2A)                                           |
|  - Prompts (system_prompts.py):                                                             |
|      • MAINTENANCE_TRIAGE_PROMPT → triage JSON schema                                       |
|      • format_vendor_*_request → quote / availability / booking JSON schemas                |
|  - Session management via SessionService (session_manager.py)                               |
+----------------------------------------------------------------------------------------------+
                                               |
                                               |  A2A protocol (RemoteA2aAgent)
                                               v
+----------------------------------------------------------------------------------------------+
|                          Remote Vendor Agent (A2A)                                           |
|   (src/adk_agents/vendor/agent.py + src/a2a_servers/vendor_server.py)                        |
|                                                                                              |
|   - Runs as separate process (uvicorn on localhost:8001)                                     |
|   - Exposes agent card: /.well-known/agent-card.json                                         |
|   - Tools (vendor_service_tools.py):                                                         |
|       • request_quote(service_type, issue, zip, severity)                                    |
|       • get_availability(service_type, quote_id)                                             |
|       • book_slot(quote_id, slot_id, tenant_details, notes)                                 |
|   - Prompt (vendor_prompts.py): strict JSON schemas for:                                     |
|       • quote response                                                                       |
|       • availability options                                                                 |
|       • booking confirmation                                                                 |
+----------------------------------------------------------------------------------------------+

                                           |
                                           v

                            +-------------------------------+
                            |     External Integrations     |
                            |   (future / stubbed today)    |
                            |   - Real vendor APIs          |
                            |   - Real payment processor    |
                            +-------------------------------+
```

Remote A2A vendor agent runs as an independent process (uvicorn) exposing an agent card consumed by `RemoteA2aAgent`.

## 5. Components
| Component | Purpose |
|-----------|---------|
| `maintenance_triage_agent.py` | Root LLM agent with strict JSON prompts + sub-agent delegation. |
| `adk_agents/vendor/agent.py` | Remote vendor agent (LLM + service tools) published via A2A. |
| `remote_vendor_agent` | `RemoteA2aAgent` referencing vendor agent card (localhost). |
| `tools/kb_tools.py` | Troubleshooting lookup tool (extensible to vector RAG). |
| `tools/vendor_tools.py` | Vendor selection scoring tool. |
| `tools/vendor_service_tools.py` | Quote / availability / booking tool implementations. |
| `prompts/system_prompts.py` | Strict JSON schemas (triage, quote, availability, booking). |
| `prompts/vendor_prompts.py` | Vendor agent instruction with enforced schemas. |
| `utils/session_manager.py` | Session service factory (InMemorySessionService / DatabaseSessionService). |
| `utils/stubs.py` | Controlled simulation (job status, payment AP2-style). |
| `flow/main_flow.py` | Orchestration; updates states; interacts with both agents. |
| `tests/*` | Evaluation & regression safety (triage, quote collaboration). |
| `vendor-agent-start.ps1` | Windows startup script loading .env for remote agent. |

## 6. Multi-Agent & Protocols
- Primary LLM agent (Gemini) + remote vendor agent via A2A protocol.
- Sub-agent delegation: triage agent invokes remote vendor agent for quote / availability / booking.
- AP2-style payment mandate + conditional settlement (stubbed).

## 7. Tools
- Custom tools registered on both agents (KB lookup, vendor select, quote, availability, booking).
- Strict instruction: model must call tools or sub-agent; never fabricate tool output.

## 8. Sessions & Memory
- `InMemorySessionService` for fast tests.
- `DatabaseSessionService` (`sqlite+aiosqlite://`) for persistent replay & multi-turn continuity.
- Session ID recorded in `logs_rec.trace_id`.
- Supports future context compaction (truncate historical turns while retaining structured state).

## 9. Evaluation-Gated Development
- Golden scenarios (planned / extendable).
- Tests assert JSON schema integrity + flow state sequence.
- Any prompt / logic change must preserve expected state progression.
- Vendor collaboration tests ensure A2A functioning.

## 10. Setup

### 10.1 Requirements
- Python 3.12+
- Poetry
- Gemini API Key in `.env`
- Optional: `aiosqlite` for async DB persistence

### 10.2 Install
```bash
poetry install
```

### 10.3 Environment (.env)
```env
GOOGLE_API_KEY=YOUR_KEY
GOOGLE_VERTEX_PROJECT=optional-gcp-project-id
GOOGLE_VERTEX_LOCATION=us-central1
USE_SHARED_SQLITE=true   # Set false to use in-memory sessions
```

### 10.4 Start Remote Vendor Agent (A2A)
Windows (PowerShell):
```powershell
.\vendor-agent-start.ps1
```
Direct:
```bash
poetry run uvicorn src.a2a_servers.vendor_server:app --host localhost --port 8001
```
Verification:
```bash
curl http://localhost:8001/.well-known/agent-card.json
```

### 10.5 Run Single Scenario
```bash
poetry run python -m src.main
```

### 10.6 Run Tests
```bash
poetry run pytest -s
```

### 10.7 Run All Golden Incidents Tests
```bash
poetry run pytest -s tests/test_flow_golden_incidents.py -k test_run_scenario_all_golden
```

### 10.8 Run Evals for All Golden Incidents
```bash
poetry run pytest -s .\tests\test_eval_golden.py -k test_eval_all_golden
```

## 11. A2A Protocol Highlights
- Remote vendor agent publishes agent card at `/.well-known/agent-card.json`.
- Triage agent’s `RemoteA2aAgent` consumes card URL, enabling cross-process tool delegation.
- Quote → Availability → Booking executed through remote agent’s tool endpoints transparently.

## 12. AP2-style Payment Stub
- Mandate object with `max_amount`.
- Validation: job status, tenant confirmation (simulated), amount threshold.
- Payment record emitted if validated; reasons array if rejected.

## 13. Observability
- `LogsRecorder` captures states, messages, structured artifacts.
- Session ID bridging for trace correlation.
- ADK events (model/tool/sub-agent) visible via emitted console logs (extendable to ADK web UI).
- Metrics extension point: count JSON parse failures, quote approval rate, escalation frequency.

## 14. Future Enhancements
| Area | Planned |
|------|---------|
| Context Compaction | Summarize prior turns, retain tool outputs. |
| RAG | Replace KB with vector embeddings & semantic filters. |
| Vendor Optimization | Multi-objective scoring (cost/speed/rating). |
| Real AP2 | Integrate official AP2 libs (mandate + settlement pipeline). |
| Vision | Use photo tags for richer triage signal. |
| Metrics Persistence | Store evaluation runs (pass/fail diff). |
| Prompt Versioning | Hash prompt → tag test results. |
| Retry / Backoff | Adaptive tool call retries on transient errors. |
| Streaming UX | WebSocket event relay to UI frontend. |

## 15. Security / Safety Considerations
- Strict JSON schemas reduce injection surface.
- Emergency escalation rules prioritize gas/electrical hazards.
- API key loaded via environment; never hard-coded.
- Random approval logic only when ground truth absent (transparent in logs).
- Separation of concerns: remote agent isolation (future network boundary / auth).

## 16. Troubleshooting
| Issue | Resolution |
|-------|------------|
| `no such column: events.author` | Delete stale `adk_sessions.db` (schema migration) |
| Async SQLite error | Use `sqlite+aiosqlite:///` and install `aiosqlite` |
| JSON parse failure | Strip fenced ```json blocks; validate schema keys |
| Missing vendor quote | Ensure vendor server running & reachable at localhost:8001 |
| Env vars not loaded | Confirm `load_dotenv()` executed in entrypoint |
| Test session DB conflicts | Set `USE_SHARED_SQLITE=false` for isolation |

## 17. Glossary
| Term | Definition |
|------|------------|
| A2A Protocol | Standard for agent-to-agent structured interaction (remote delegation). |
| Sub-Agent | Remote or local agent invoked by parent agent for specialized tasks. |
| Mandate (AP2) | Authorization object granting capped payment authority. |
| Golden Scenario | Canonical test case guarding regression. |
| Evaluation Gating | Blocking changes unless critical scenario tests pass. |
| Tool | Deterministic or procedural function callable by agent. |
| Session Service | Persistence layer for multi-turn agent context. |
| Context Compaction | Strategy to shrink prior conversation while preserving key facts. |

## 18. Quick Start Code
```python
from src.flow.main_flow import run_scenario_through_agents
import asyncio

scenario = {
  "scenario_id": "T001",
  "tenant_input": {
      "title": "AC not cooling",
      "description": "Unit runs but no cold air.",
      "priority_hint": "high"
  },
  "property": {"property_id": "P123", "zip": "95054"},
  "ground_truth": {
      "self_help_should_succeed": False,
      "expected_vendor_service_type": "hvac",
      "max_budget": 500.0,
      "severity": "HIGH"
  }
}

logs = asyncio.run(run_scenario_through_agents(scenario))
print(logs.states)
```

## 19. License
MIT (add LICENSE file if distributing).

Evaluation-first, multi-agent, protocol-aware, extensible.