# 📘 DevOps Copilot: Complete Team Study Guide & Hackathon Defense Manual

Welcome, team! This document is our single source of truth for understanding, presenting, and defending **DevOps Copilot: The AI Incident Response Agent**. 

Whether you are walking judges through slides, demoing the web interface, or answering technical questions, this guide explains how every part of our system works in plain English without unexplained jargon.

---

## 1. What This Project Is

### The 3-Sentence Summary (For non-technical judges)
> **"DevOps Copilot is an AI-powered assistant that investigates and helps resolve software outages when critical cloud services fail. Instead of on-call engineers spending an hour manually searching through logs, release histories, and system metrics at 3:00 AM, our agent automatically inspects telemetry, pinpoints the root cause, and proposes a safe fix. For safety, high-risk actions are blocked until a human approves them, the system verifies recovery after the fix, and it automatically writes a complete incident postmortem report."**

### The Real Problem It Solves
When a website or payment processor crashes (an **outage**), downtime can cost thousands of dollars per minute. Engineers known as **Site Reliability Engineers (SREs)** or **DevOps Engineers** (the specialists who keep software infrastructure operational) must manually correlate data across multiple fragmented tools:
1. **Metrics dashboards** (e.g., Datadog, Prometheus, Grafana)
2. **Log aggregation systems** (e.g., Splunk, Elasticsearch)
3. **Deployment registries** (e.g., GitHub, ArgoCD)
4. **Historical incident documentation** (e.g., Jira, Confluence postmortems)

Manual triage often consumes 45 to 60 minutes. **DevOps Copilot reduces that initial investigation to under 15 seconds**, while maintaining safety by keeping a human engineer in the loop for high-risk actions.

---

## 2. High-Level Architecture (The 3 Layers)

```
   ┌─────────────────────────────────────────────────────────────┐
   │                   STREAMLIT FRONTEND (app.py)               │
   │  [Alert Banner] ➔ [Live Step Feed] ➔ [Approval Gate] ➔ [Postmortem]
   └──────────────────────────────┬──────────────────────────────┘
                                  │ (User clicks & triggers)
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │              INTELLIGENCE & REASONING CORE                  │
   │  • agent/coordinator.py (ReAct multi-turn loop)             │
   │  • agent/prompts.py     (Grounded prompting & JSON Schema)  │
   │  • agent/planner.py     (Risk tags: HIGH vs LOW + Fallback) │
   │  • agent/reporter.py    (Automated Markdown Postmortem)     │
   │  • agent/gemini_gateway.py (Resilience gateway & Cache)     │
   └──────────────────────────────┬──────────────────────────────┘
                                  │ (Tool calls: get_logs, rollback...)
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │           SIMULATED ENVIRONMENT (Local Backend)             │
   │  • simulation/environment.py                                │
   │  • data/scenario_1_bad_deploy.json                          │
   │  • data/scenario_2_fix_fails.json                           │
   │  • data/past_incidents.json                                 │
   └─────────────────────────────────────────────────────────────┘
```

---

## 3. Life of an Alert (Step by Step)

### Walkthrough of Scenario 1: "Bad Deploy" (The Primary Flow)

Here is the exact progression from an initial alert to postmortem generation:

1. **The Alert Fires (`app.py`)**:
   - The user selects `Scenario 1` and clicks **"🚨 Trigger Alert"** in the sidebar.
   - The app transitions from `stage = "idle"` to `stage = "investigating"`. The red alert banner displays the service name (`payment-service`), the initial error rate (`43.5%`), and the alert timestamp.
2. **The Coordinator Launches (`agent/coordinator.py` -> `investigate()`)**:
   - The coordinator starts an autonomous loop. It provides Gemini with the system prompt (`agent/prompts.py`) and declares the 4 diagnostic tools (`get_status`, `get_deploys`, `get_logs`, `get_past_incidents`).
   - The model chooses tools step-by-step based on observations returned from previous calls.
3. **Tool 1: Checking Vital Signs (`simulation/environment.py` -> `get_status()`)**:
   - Gemini requests `get_status(service_name="payment-service")`.
   - The simulated environment returns: Status `CRITICAL`, error rate `43.5%`, active DB connections `10/10` (max: 10), and version `v2.4.0`.
4. **Tool 2: Checking Recent Releases (`simulation/environment.py` -> `get_deploys()`)**:
   - Gemini queries recent deployment records.
   - The simulation returns deploy `dep-494` (`v2.4.0`) committed by `dave@company.com` with commit message: *"Updated DB connection pool config to tune memory usage (reduced pool size to 10)"*.
5. **Tool 3: Checking Error Logs (`simulation/environment.py` -> `get_logs()`)**:
   - Gemini requests `ERROR` level logs.
   - The simulation returns lines showing: *"ConnectionPoolExhaustedException: Timeout waiting for idle connection in pool (max=10, active=10, waiters=4)"* and *"POST /api/v1/charge 500 Internal Server Error - database connection timeout"*.
6. **Tool 4: Searching Historical Incidents (`simulation/environment.py` -> `get_past_incidents()`)**:
   - Gemini queries past postmortems for terms related to connection pools.
   - It finds past incident `INC-892`: *"Database connection pool size was inadvertently lowered... Rolled back deployment to restore pool size. Recovered in 3 minutes."*
7. **Structured JSON Diagnosis (`agent/coordinator.py`)**:
   - Evidence gathering concludes. Using Gemini's `response_mime_type="application/json"` mode, Gemini produces a structured JSON diagnosis:
     - **Root Cause**: Deployment v2.4.0 lowered DB pool size to 10, causing connection exhaustion.
     - **Confidence**: High confidence score (e.g., 90–95%) with an explanation of supporting evidence.
     - **Recommended Action**: Rollback to version `v2.3.9`.
8. **Risk Classification & Approval Gate (`agent/planner.py` -> `build_plan_from_diagnosis()`)**:
   - The planner notes the recommended action is `rollback`. It assigns **`HIGH RISK`** and sets `requires_approval = True`.
   - In `app.py`, execution halts at the **Approval Gate** showing a red `🚨 HIGH RISK` badge. The rollback **will not execute** until a human operator clicks **"✅ Approve Fix"**.
9. **Execution (`simulation/environment.py` -> `rollback()`)**:
   - When the user clicks "Approve Fix", `app.py` moves to `stage = "executing"` and calls `rollback(service_name="payment-service", target_version="v2.3.9")`.
   - The simulated environment updates version to `v2.3.9`, restores pool size to 50, switches status to `HEALTHY`, and drops the error rate to `0.2%`.
10. **Verification (`app.py` -> Stage: `verifying`)**:
    - `app.py` immediately queries `get_status()` to compare before vs. after telemetry.
    - Because status is `HEALTHY` and error rate dropped, the app triggers celebratory balloons (`st.balloons()`), displays a recovery banner, and advances to `stage = "done"`.
11. **Postmortem Report Generation (`agent/reporter.py` -> `generate_incident_report()`)**:
    - `reporter.py` takes the full session record and prompts Gemini to produce a standardized Markdown postmortem report.
    - The report renders on-screen with a working **"📥 Download Report (.md)"** button.

---

### Walkthrough of Scenario 2: "Fix Fails" (Edge-Case Flow)

Scenario 2 demonstrates what happens when the obvious initial hypothesis fails to resolve the incident:

1. **The Alert Fires**: `payment-service` experiences a **54.8%** error rate with database connection timeouts.
2. **Initial Investigation**: The agent notes that deploy `v2.4.0` (*"Refactor async payment receipt email dispatcher"*) occurred right before the spike.
3. **The Initial Proposal**: The agent initially suspects the deploy and proposes a `rollback` to `v2.3.9`.
4. **Approval & Execution**: The human clicks "Approve Fix". The simulated environment executes the rollback.
5. **The Verification Catch (`app.py`)**:
   - `app.py` queries `get_status()`.
   - **Status remains CRITICAL** and error rate is still **52.4%**.
   - The app detects that `after_status["status"] != "HEALTHY"` and displays: **"❌ VERIFICATION FAILED: Fix did NOT work!"**.
6. **Dropping the Hypothesis & Re-investigating**:
   - The UI reveals a button: **"🔍 Re-investigate Next Most Likely Cause"**.
   - When clicked, `coordinator.investigate()` runs again with context indicating that the rollback completed but errors persisted:
     - **In Live Mode**: Gemini receives the prompt with `previous_attempt_info` explicitly stating that the rollback failed. Gemini shifts its focus away from application deployment and queries deeper database logs and past incident `INC-650`. It discovers that **PostgreSQL connection slots are saturated (500/500 active)** with server logs showing: *"FATAL: remaining connection slots are reserved for non-replication superuser connections"*.
     - **In Demo / Offline Mode**: The system pulls the pre-recorded secondary investigation from `data/demo_cache/scenario_2_cache.json`, displaying the re-investigation steps without calling external APIs.
7. **Postmortem Documents the Failed Attempt**:
   - When the postmortem is generated, it includes a dedicated section: **"Failed Remediation Analysis & Learnings"**, recording that the rollback was ineffective because the root cause was database connection saturation rather than application code.

---

### Walkthrough of Scenario 3: "Memory Leak" (Gradual Degradation & Auto-Restart)

Scenario 3 proves that the agent can diagnose subtle infrastructure degradation that has **no recent deploy**:

1. **The Alert Fires**: `payment-service` has an error rate of **38.6%** and average latency spikes to **3450ms**.
2. **Tool 1 & 2 (Status & Deploys)**:
   - Status shows `memory_usage_mb: 1968 / 2048` (**96.1% heap capacity**), with uptime of 5 days (`432,000s`).
   - The deploy log shows **NO recent deployment** (last deploy was 5 days ago and ran fine).
3. **The Trap**: A naive script that assumes every outage is caused by a bad release would be completely lost or trigger a useless rollback.
4. **Tool 3 & 4 (Logs & Past Incidents)**:
   - Error logs reveal `java.lang.OutOfMemoryError: Java heap space` during batch ledger reconciliation (`ledger-reconcile-worker`).
   - The agent cross-references past incident `INC-402`, where a gradual memory leak in the batch worker caused heap exhaustion after 4+ days of continuous uptime.
5. **Low-Risk Action & Auto-Execution**:
   - The planner assigns **`LOW RISK`** to `restart_service`.
   - The action executes safely, flushing leaked memory.
6. **Verification & Postmortem**:
   - Status recovers to `HEALTHY`, memory drops to **240MB (11.7%)**, and error rate drops to **0.1%**.
   - Postmortem recommends adding automated JVM heap monitoring and scheduled worker recycling.

---

### Walkthrough of Scenario 4: "Third-Party Vendor Outage" (Upstream Failure & Failover)

Scenario 4 demonstrates that the agent **does not execute useless rollbacks** when the problem is an external partner:

1. **The Alert Fires**: `payment-service` experiences a **41.8%** error rate with high latency (3450ms).
2. **The Red Herring**: Deploy `v2.4.1` (*"Update checkout copy and footer disclaimers"*) occurred 12 minutes ago.
3. **The Trap**: An impulsive engineer would immediately roll back `v2.4.1`. However, that commit only changed HTML/text copy!
4. **Tool Investigation**:
   - Internal metrics show database health is completely normal (`db_health: HEALTHY`, pool 8/50).
   - But error logs are dominated by `504 Gateway Timeout` when calling `https://api.paygate-global.com/v2/charges`.
   - The agent detects: **PayGate Global (the external payment gateway) is down**.
5. **The Agent's Intelligence**:
   - The agent explicitly avoids a rollback. It warns that rolling back application code will not fix an external vendor outage.
   - It proposes: `escalate_and_enable_fallback` (switch payment routing to secondary provider `StripeSecondary` and page the vendor NOC).
6. **Human Approval Gate**:
   - Marked **`MEDIUM RISK`** (enabling a secondary provider incurs different transaction fees).
   - Human clicks **"✅ Approve Fix"**.
7. **Verification**:
   - `fallback_provider_enabled = true`.
   - Transactions reroute to the secondary provider, and the error rate drops from **41.8% ➔ 0.8%**.

---

### Walkthrough of Scenario 5: "Conflicting Evidence" (Low Confidence & 3 Operator Choices)

Scenario 5 highlights the system's honesty: **when data is ambiguous, the agent does NOT guess—it lowers its confidence and gives the operator choices**:

1. **The Alert Fires**: Error rate is **32.4%** on `payment-service`.
2. **Conflicting Telemetry**:
   - Deploy `v2.4.2` occurred 8 minutes ago (*"Add client telemetry analytics tag"*).
   - At the same time, database read replica `db-replica-02` shows replication lag spiking to **480 seconds** with `WAL_REPLAY_STALLED`.
3. **The Low Confidence Threshold**:
   - The agent correlates the symptoms and finds conflicting signals.
   - It calculates a **confidence score of 52%** (well below the 60% threshold).
4. **Honest Operator Choice Menu**:
   Instead of forcing a single automated action, the UI presents **3 operator choices**:
   - **Choice A (Recommended)**: *"Fail Over Replica"* — Drain stale `db-replica-02` and route reads to healthy `db-replica-01`.
   - **Choice B**: *"Rollback Anyway"* — Roll back deploy `v2.4.2` if the operator suspects the release.
   - **Choice C**: *"Gather More Info"* — Collect extended replica logs.
5. **Branching Outcomes**:
   - If operator clicks **Fail Over Replica**: Service immediately recovers to `HEALTHY` (error rate **0.2%**).
   - If operator clicks **Rollback Anyway**: The rollback succeeds, but verification catches that the error rate remains **32.4% CRITICAL**. The UI then offers **"🔍 Re-investigate"**, which correctly identifies the replica lag and performs the failover!

---

## 4. Human Rejection & Alternative Fallback Flow

What happens if an engineer looks at the proposed action and says "No"?

```
   [ Awaiting Approval ]
          │
          ├─────────────────────────────────────────────────┐
          │ (User clicks "Approve Fix")                     │ (User clicks "Reject Proposal")
          ▼                                                 ▼
   [ Executing Plan ]                               [ Fallback Generated ]
   (Applies rollback)                               (Planner creates low-risk fallback)
          │                                                 │
          ▼                                                 ▼
   [ Verification ]                                 [ Awaiting Approval for Fallback ]
   (Health check & metrics)                         (User can Approve alternative action)
                                                            │
                                                            ▼
                                                    [ Executing Fallback ]
                                                    (Applies soft restart)
                                                            │
                                                            ▼
                                                    [ Verification ]
                                                    (Health check & metrics)
```

1. If the AI proposes a **`HIGH RISK`** `rollback` and the operator clicks **"❌ Reject Proposal"**:
2. `app.py` calls `planner.get_fallback_plan()`.
3. The planner creates an alternative, lower-risk plan (e.g., `restart_service`: *"Perform safe restart of payment-service pods to clear hung sockets"*).
4. The UI stays in `awaiting_approval`, presents the new fallback plan with an explanation of why it was generated, and allows the operator to click **"✅ Approve Fix"** for the fallback.
5. Once approved, the fallback action executes in the simulated environment, and the verification step runs normally afterwards.

---

## 5. File-by-File Guide

| File | What It Does (2-3 sentences) | What It Connects To | The ONE Thing to Remember |
| :--- | :--- | :--- | :--- |
| `app.py` | The Streamlit web interface. Renders sidebar controls, alert banner, live investigation tool feed, approval gate, before/after metrics, and postmortem report. | Calls `simulation/environment.py` for status/actions and `agent/coordinator.py` & `agent/reporter.py` for AI workflows. | Uses `st.session_state` so user button clicks do not wipe active investigation data. |
| `agent/coordinator.py` | The autonomous agent coordinator. Registers the 4 tool schemas, runs the manual step-by-step ReAct loop (up to 8 iterations), and calls Gemini's structured JSON output mode. | Connects to `simulation/environment.py` (to run tools), `agent/prompts.py` (for instructions), and `agent/gemini_gateway.py` (for API calls). | Runs the tool loop manually so Streamlit can stream each step to the UI in real time. |
| `agent/planner.py` | The safety and risk evaluator. Classifies actions as `HIGH` risk (rollback) or `LOW` risk (restart), enforces approval requirements, and generates fallback plans if an action is rejected. | Takes diagnosis from `coordinator.py` and provides actionable plans and fallbacks to `app.py`. | If a user clicks "Reject", the planner generates the next-best alternative option. |
| `agent/prompts.py` | System instructions for Gemini. Enforces evidence grounding, requires exact citations, sets confidence calibration rules, and defines the final JSON schema. | Imported by `agent/coordinator.py` for tool-use loops and diagnosis synthesis. | Instructs the model not to invent telemetry that was not returned by tools. |
| `agent/reporter.py` | Generates a Markdown incident postmortem report using Gemini. Covers Summary, Timeline, Root Cause, Key Evidence, Actions, and Failed Remediations. | Takes the session record from `app.py` and requests report generation from Gemini (or local cache). | In Scenario 2, it automatically documents the failed fix attempt and key engineering learnings. |
| `agent/gemini_gateway.py` | Central resilience gateway and demo safety net. Handles API rate limits (`429`), retries, model switching, and local offline cache fallback. | Used by `coordinator.py` and `reporter.py` as the single point of contact for Gemini. | When `DEMO_MODE=true` or network drops, it returns local cached traces without crashing. |
| `simulation/environment.py` | The simulated cloud environment. Holds in-memory state and provides the 7 core functions (`get_status`, `get_deploys`, `get_logs`, `get_past_incidents`, `rollback`, `restart_service`, `reset_environment`). | Loads scenario files from `data/` and mutates state when actions like `rollback()` are called. | Actions actually change internal state: rolling back updates error rates, logs, and health status. |
| `data/scenario_1_bad_deploy.json` | Dataset for Scenario 1. Contains 67 log lines, 4 deployment records (Dave's pool reduction commit), and initial degraded status (43.5% error rate). | Loaded by `simulation/environment.py` during `reset_environment("scenario_1")`. | Contains log lines showing `ConnectionPoolExhaustedException` following deploy `v2.4.0`. |
| `data/scenario_2_fix_fails.json` | Dataset for Scenario 2. Contains 66 log lines showing PostgreSQL primary running out of connection slots (500/500 active). | Loaded by `simulation/environment.py` during `reset_environment("scenario_2")`. | Rollback does not fix the outage because the root cause is database connection saturation. |
| `data/past_incidents.json` | Historical incident knowledge base. Contains 4 postmortems (including INC-892 for pool reduction and INC-650 for DB connection exhaustion). | Queried by `get_past_incidents()` in `simulation/environment.py`. | Enables the AI to compare active incident patterns with past resolutions. |
| `data/demo_cache/scenario_1_cache.json` & `scenario_2_cache.json` | Pre-recorded verified traces for Scenarios 1 and 2 (investigation steps, diagnosis, plan, and final markdown report). | Loaded by `agent/gemini_gateway.py` when Demo Mode or fallback safety net is engaged. | Mirrors the simulation data so offline presentations run consistently. |
| `test_simulation.py` | Standalone verification script for the simulated environment. Tests all 7 environment functions and proves state mutations. | Directly imports and tests `simulation/environment.py`. | Validates that state mutations occur properly upon remediation. |
| `test_agent.py` | Terminal test runner for the agent. Runs Scenario 1 and Scenario 2 directly in the console. | Imports `agent/coordinator.py`, `agent/planner.py`, and `simulation/environment.py`. | Validates the multi-turn function calling loop and approval logic in pure Python. |
| `test_app.py` | Automated test suite for the Streamlit UI using Streamlit's official `AppTest` framework. | Tests button clicks and state transitions in `app.py` across 4 test modes. | Validates that buttons, approval gates, fallbacks, and reports work as intended. |
| `requirements.txt` | Package dependencies (`google-genai`, `streamlit`, `pandas`, `python-dotenv`). | Used by `pip install -r requirements.txt`. | Minimal set of dependencies for reliable installation. |
| `.env.example` & `.env` | Configuration files for API keys and demo mode flags. `.env` holds local values; `.env.example` provides a template. | Read by `python-dotenv` across the project. | `.env` is listed in `.gitignore` to prevent committing secrets. |
| `.gitignore` | Git ignore rules. Excludes `.env`, `__pycache__`, and virtual environments. | Git version control. | Prevents sensitive keys or temporary files from being tracked. |
| `README.md` | Public project documentation. Overview, architecture diagram, quickstart steps, and demo walkthrough. | Project landing page. | Provides a clear guide for judges and evaluators visiting the repository. |

---

## 6. How the Key Concepts Work

### 1. Tool Calling / Function Calling
- **In Plain English**: When an LLM is used for conversational chat, it simply outputs sentences. With **tool calling** (function calling), the model is given a catalog of real functions. When asked to diagnose an issue, rather than guessing, it returns structured function call requests (e.g., `get_logs(level="ERROR")`).
- **How It Works in Code**:
  In `agent/coordinator.py`, we define schemas using `google.genai.types.FunctionDeclaration`. When Gemini inspects the alert, it emits a `FunctionCall` part. Our coordinator intercepts this call, executes `environment.get_logs()` locally, and feeds the resulting JSON back to Gemini inside a `types.Part.from_function_response()` message. Gemini reads the actual output before deciding its next step.

### 2. Reducing Hallucination Through Tool Grounding
- **In Plain English**: If an incident response tool makes up phantom server names or fake errors, engineers waste critical time.
- **How It Works in Code**:
  We do not rely on an ungrounded model:
  1. The prompt in `agent/prompts.py` explicitly commands: *"Rely strictly on tool results. Do not invent timestamps, commit hashes, or error messages that tools did not return."*
  2. Telemetry is fed into the conversation history as verified `role="tool"` messages.
  3. Structured JSON synthesis forces the model to list explicit evidence citations from its prior tool observations.

### 3. Structured JSON Output & Reliability
- **In Plain English**: If an AI returns unstructured text or malformed markdown when the frontend expects data fields, the application can crash.
- **How It Works in Code**:
  In `agent/coordinator.py`, the final diagnosis step configures `response_mime_type="application/json"`. This makes valid JSON output very likely. As an additional backup, we wrap parsing in a `try...except` block with a single retry prompt, falling back to clean cached data if parsing ever fails.

### 4. The Human Approval Gate
- **In Plain English**: An automated agent should not have unilateral authority to execute destructive or high-risk operations on production systems.
- **Where It Is Enforced in Code**:
  1. In `agent/planner.py`, `classify_risk("rollback")` assigns `risk_level = "HIGH"` and sets `requires_approval = True`.
  2. In `app.py`, the UI checks `plan["requires_approval"]`. If true, it halts at `stage = "awaiting_approval"`.
  3. The execution code (`rollback()`) is located exclusively inside the `executing` stage block, which is unreachable until the user clicks `st.button("✅ Approve Fix")`.

### 5. Post-Action Verification
- **In Plain English**: SRE best practice requires verifying metrics *after* a fix is applied to confirm whether the service actually recovered.
- **How It Works in Code**:
  In `app.py`, applying a fix immediately transitions the app to `stage = "verifying"`. The app calls `get_status("payment-service")` to take a fresh snapshot:
  - If `status == "HEALTHY"` (Scenario 1), it confirms resolution.
  - If `status != "HEALTHY"` (Scenario 2), it alerts the operator that the fix was ineffective and offers the option to re-investigate deeper causes.

### 6. Resilience & Demo Mode
- **In Plain English**: Wi-Fi at hackathons can be unreliable, and free-tier API quotas can be exhausted. The resilience layer ensures the presentation never breaks unexpectedly.
- **How It Works in Code**:
  In `agent/gemini_gateway.py`, all calls flow through `GeminiGateway`. If `DEMO_MODE=true` is set, or if live API calls hit rate limits (`429`) or network timeouts, the gateway automatically falls back to verified pre-recorded traces in `data/demo_cache/`. The UI displays a `🏷️ DEMO MODE ACTIVE (OFFLINE)` badge to remain transparent about cache usage.

---

## 7. Data Values vs. Live Runtime Variability

When presenting the walkthrough, keep in mind which specific values come from the static data fixtures and which are generated by the model:

| Value | Source | Can It Differ in a Live Run? |
| :--- | :--- | :--- |
| **Service Name (`payment-service`)** | `data/scenario_*.json` | **No.** Defined in the scenario data file. |
| **Pre-remediation Error Rates (`43.5%`, `54.8%`)** | `data/scenario_*.json` | **No.** Set in `initial_state.error_rate`. |
| **Commit Author (`dave@company.com`, `emma@company.com`)** | `data/scenario_*.json` | **No.** Hardcoded in the deployment list. |
| **Commit Message & Deploy Time (`14:02 UTC`)** | `data/scenario_*.json` | **No.** Hardcoded in the deployment list. |
| **Historical Incident IDs (`INC-892`, `INC-650`)** | `data/past_incidents.json` | **No.** Fixed IDs in the past incident catalog. |
| **Agent's Confidence Score (e.g., `90%`, `92%`, `95%`)** | Gemini model output | **Yes.** In live mode, different model versions or sampling may evaluate confidence slightly differently (e.g., 90% vs 95%). In demo/offline mode, it is fixed at 95%. |
| **Diagnosis Phrasing & Reasoning text** | Gemini model output | **Yes.** In live mode, Gemini writes its own sentences explaining the reasoning. In demo/offline mode, it uses the cached phrasing. |
| **Post-remediation Error Rate (`0.02%` vs `0.2%`)** | `environment.py` / report cache | **Minor variance.** `environment.py` resets error rate to `"0.02%"`, while the pre-cached demo postmortem references `"0.2%"`. |

---

## 8. Glossary

- **Agent**: A software system that uses an AI model to perceive environment state via tools, reason through steps, and propose or execute actions toward a goal.
- **Tool Calling (Function Calling)**: A model capability where the LLM produces structured requests to run specific code functions with arguments, rather than free-form text.
- **Rollback**: Reverting an application from its current software version to a previously deployed, stable version when a regression is detected.
- **Deployment**: The automated process of packaging and releasing updated software code or configuration to servers.
- **Root Cause**: The fundamental underlying fault that triggered an incident (e.g., connection pool size configured too low), as opposed to just the outward symptom (e.g., HTTP 500 error).
- **Confidence Score**: A 0–100% assessment generated by the model reflecting how strongly its available evidence supports its conclusion.
- **Human-in-the-Loop (HITL)**: A system design pattern where AI assists with analysis and recommendations, but high-impact decisions require explicit human authorization.
- **Session State (`st.session_state`)**: A memory store in Streamlit that preserves variables across user button clicks and app reruns.
- **API Key**: A secret credential used to authenticate requests to external services like the Google Gemini API.
- **Rate Limit (`429 RESOURCE_EXHAUSTED`)**: A restriction imposed by API providers on request frequency or volume over a given time window.
- **Simulated Environment**: A local, in-memory Python representation of infrastructure services, logs, and databases used for testing without cloud costs or risks.
- **Incident Postmortem Report**: A formal document analyzing the cause, timeline, remediation actions, and preventative measures resulting from an outage.

---

## 9. Twelve Questions Judges Might Ask (With Short Honest Answers)

### 1. "Is this really using AI, or is it just hardcoded scripts?"
> *"It uses Google Gemini with function calling in `agent/coordinator.py`. In live mode, Gemini actively decides which tools to call, inspects the returned logs and metrics, reasons about the evidence, and generates structured JSON. The only scripted elements are the simulated data fixtures and the backup cache we created so presentations don't break if conference Wi-Fi drops."*

### 2. "What stops the AI from doing something dangerous to production?"
> *"Our Remediation Planner (`agent/planner.py`) acts as a safety gate. Actions are categorized by risk level: low-risk restarts can execute automatically, but high-risk actions like rollbacks lock the application in an `awaiting_approval` state. The execution function physically cannot run until an authorized operator clicks 'Approve Fix'."*

### 3. "What if the AI is wrong in its diagnosis?"
> *"Two safeguards protect the system: First, the AI must provide its evidence citations and confidence score so the human operator can verify the reasoning before approving anything. Second, our verification stage tests health metrics after the action. If the fix was wrong or ineffective (as demonstrated in Scenario 2), the system flags the failure and offers to re-investigate deeper causes."*

### 4. "What if the fix fails to resolve the incident?"
> *"That is the exact focus of Scenario 2. When the rollback executes but verification shows 500 errors persist, the system reports 'Fix did NOT work'. It drops the application deploy hypothesis and runs a secondary investigation that inspects database-level metrics to find the true bottleneck."*

### 5. "What are the limitations of your system?"
> *"Our agent is currently built for single-service investigations using predefined diagnostic tools. It does not yet diagnose complex multi-tier network partition failures, cannot modify Kubernetes manifests dynamically, and works with structured diagnostic telemetry rather than open-ended shell access."*

### 6. "What if the logs conflict or are incomplete?"
> *"Our system prompt in `agent/prompts.py` requires the model to actively identify missing or conflicting telemetry. If evidence is ambiguous, the model is instructed to lower its confidence score and populate the `conflicting_or_missing_info` field, which displays as a visible warning box in the UI."*

### 7. "Why did you use simulated data, and how would this work with real systems?"
> *"For a hackathon, running real multi-node Kubernetes clusters introduces cloud costs, credential risks, and latency. We abstracted the infrastructure into `simulation/environment.py`. In production, you would replace those 4 functions with API integrations for Datadog (metrics/logs), GitHub/ArgoCD (deploys), and Jira/Confluence (past postmortems). The coordinator and agent logic would remain identical."*

### 8. "How is this different from a normal monitoring alert like PagerDuty or Datadog?"
> *"Traditional monitoring tools are passive: they fire an alert saying 'Error rate is high', leaving an engineer to manually search logs, check recent commits, and write postmortems. DevOps Copilot actively pulls clues together across logs, deploys, and history in seconds, proposes an approved remediation, verifies the outcome, and drafts the postmortem report."*

### 9. "What happens if a human operator rejects the AI's proposal?"
> *"If the operator clicks 'Reject Proposal', the Remediation Planner intercepts the rejection and generates the next-best fallback action (e.g., proposing a safe service restart). The user can then review and approve the alternative action, which executes and goes through verification."*

### 10. "How would you make this production-ready?"
> *"We would implement:
> 1. Role-Based Access Control (RBAC) and OAuth so only authorized on-call engineers can approve high-risk remediations.
> 2. Live API connectors for Datadog, AWS CloudWatch, and GitHub Actions.
> 3. An immutable audit log stored in an encrypted database tracking all AI recommendations and human approvals for compliance."*

### 11. "Why use Gemini's JSON mode instead of regular text output?"
> *"Standard text generation can include markdown conversational filler, which risks failing `json.loads()`. Configuring Gemini's native `response_mime_type='application/json'` makes valid JSON output very likely. We also include a 1-retry fallback loop in `coordinator.py` to ensure the UI never crashes on malformed text."*

### 12. "What happens if the Gemini API experiences an outage or rate limit during your demo?"
> *"All API calls pass through `GeminiGateway` (`agent/gemini_gateway.py`). If the primary model hits a 429 quota limit, it switches across fallback models (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-3.6-flash`). If network connectivity fails completely, it engages our offline cache from `data/demo_cache/` and flags that demo mode is active."*

---

## 10. Honest Limitations (Know Your System's Scope)

1. **Simulated Infrastructure**: The system runs against local Python state and JSON datasets rather than live cloud servers.
2. **Defined Tool Boundary**: The agent queries 4 specific diagnostic tools. It does not run arbitrary bash shell commands (like `kill -9` or raw database queries).
3. **Single Service Focus**: It investigates `payment-service`. It does not yet model large microservice topologies with dozens of interdependent services.
4. **Predefined Remediation Scope**: It models rollbacks and restarts. It does not write, compile, and push custom application code patches.
5. **Session-Bound Persistence**: State lives in Streamlit's `session_state`. Hard-refreshing the browser tab resets the in-progress run to the start of the scenario.

---

## 11. Demo Cheat Sheet (3-Minute Presentation Flow)

### Scenario 1: Bad Deploy (60 seconds)
1. **Show the Problem**:
   - Open the web app at `http://localhost:8501`.
   - Ensure `Scenario 1: Bad Deploy` is selected.
   - Click **"🚨 Trigger Alert"**.
   - *Say*: *"An alert fired on payment-service with a 43.5% error rate. Instead of spending 45 minutes manually triaging logs, our AI agent begins an automated investigation."*
2. **Show the Tool Loop & Reasoning**:
   - Expand the live investigation container to show the tools running: `get_status`, `get_deploys`, `get_logs`, `get_past_incidents`.
   - *Say*: *"Notice the live step feed: the agent checks metrics, inspects deployments, and searches error logs. It identifies that deploy v2.4.0 lowered the connection pool to 10, causing connection timeouts matching past incident INC-892."*
3. **Show the Safety Gate & Verification**:
   - Point out the red `🚨 HIGH RISK` badge on the `rollback` proposal.
   - Click **"✅ Approve Fix"**.
   - *Say*: *"Because rolling back production is high risk, the AI cannot run it alone. Once I approve, the rollback executes, verification confirms error rates dropped to 0.2%, and the service returns to HEALTHY."*
4. **Show the Postmortem**:
   - Scroll to the generated postmortem report and highlight the **"📥 Download Report (.md)"** button.

---

### Scenario 2: Fix Fails (60 seconds)
1. **Trigger & Initial Approval**:
   - Select `Scenario 2: Fix Fails` in the sidebar and click **"🚨 Trigger Alert"**.
   - When the agent initially suspects deploy `v2.4.0` and proposes rollback, click **"✅ Approve Fix"**.
2. **Highlight the Verification Catch**:
   - Point out the error banner: **"❌ VERIFICATION FAILED: Fix did NOT work!"** (Status is still `CRITICAL`).
   - *Say*: *"In the real world, the obvious fix doesn't always work. The rollback succeeded, but error rates remain over 50%. Our system doesn't assume success—it catches the failure."*
3. **Re-investigate the Deeper Cause**:
   - Click **"🔍 Re-investigate Next Most Likely Cause"**.
   - *Say*: *"The agent drops its deployment assumption and investigates deeper infrastructure logs. It discovers the real root cause: PostgreSQL database connection saturation at 500/500 active connections. And the final postmortem report documents both the failed attempt and the true root cause."*

---

### Live Demo Backup Plan (If Network Stumbles)
- If the network lags or API quotas trigger:
  1. Flip the **"🛡️ Offline Demo Mode"** toggle in the sidebar.
  2. *Say*: *"We engineered a local demo safety net that runs 100% offline from verified telemetry traces, so network drops at the venue never crash our demo."*
  3. Click **"🚨 Trigger Alert"** and proceed smoothly.

---

## 12. The 5 Key Things Each Teammate Should Understand

1. **Tool Calling Over Static Prompts**: The AI uses genuine function calling to query status, deploys, logs, and incidents dynamically.
2. **Human-in-the-Loop Safety Gate**: High-risk actions (like rollbacks) cannot execute without explicit human approval.
3. **Closed-Loop Verification**: The system checks health metrics *after* applying a fix to verify recovery rather than assuming success.
4. **Handling Failed Fixes (Scenario 2)**: When a fix fails, the agent drops its initial hypothesis and searches for the deeper root cause.
5. **Resilience & Transparency**: The gateway handles rate limits and offline fallback automatically, while clearly displaying when demo mode is active.
