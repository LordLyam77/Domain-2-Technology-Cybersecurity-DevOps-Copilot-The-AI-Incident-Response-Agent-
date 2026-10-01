"""
DevOps Copilot: Modern Observability & Incident Response Dashboard.

Redesigned with a clean, dark, Datadog/Grafana aesthetic:
- Clear visual hierarchy with unified dark theme (#0E1117 / #161B22 / #30363D)
- Typography: Inter for UI text and JetBrains Mono for logs, telemetry, and code
- Horizontal incident lifecycle progress stepper (Alert -> Investigate -> Root Cause -> Approval -> Fix -> Verify/Report)
- Two-column incident layout: Story & human approval on the left (60%), live evidence & telemetry on the right (40%)
- Prominent approval card with risk-colored borders
- Live monospace log stream viewer with log-level color tagging
"""

import os
import json
import time
import pandas as pd
import streamlit as st
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from simulation.environment import (
    reset_environment,
    get_environment,
    get_status,
    get_logs,
    get_metrics_timeline,
    rollback,
    restart_service,
    escalate_and_enable_fallback,
    failover_replica
)
from agent.coordinator import IncidentCoordinator
from agent.planner import RemediationPlanner, RemediationPlan
from agent.reporter import generate_incident_report
from agent.gemini_gateway import is_demo_mode_env
from styles import CUSTOM_CSS

# Page configuration
st.set_page_config(
    page_title="DevOps Copilot | Incident Response",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern dark theme & observability styling
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = "idle"  # idle -> investigating -> awaiting_approval -> executing -> verifying -> done

if "scenario" not in st.session_state:
    st.session_state.scenario = "scenario_1"

if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = is_demo_mode_env()

if "is_demo_active" not in st.session_state:
    st.session_state.is_demo_active = st.session_state.demo_mode

if "investigation_steps" not in st.session_state:
    st.session_state.investigation_steps = []

if "diagnosis" not in st.session_state:
    st.session_state.diagnosis = None

if "plan" not in st.session_state:
    st.session_state.plan = None

if "rejected_plan" not in st.session_state:
    st.session_state.rejected_plan = None

if "before_status" not in st.session_state:
    st.session_state.before_status = None

if "after_status" not in st.session_state:
    st.session_state.after_status = None

if "remediation_outcome" not in st.session_state:
    st.session_state.remediation_outcome = None

if "auto_executed" not in st.session_state:
    st.session_state.auto_executed = False

if "secondary_investigation" not in st.session_state:
    st.session_state.secondary_investigation = False

if "incident_report" not in st.session_state:
    st.session_state.incident_report = None

if "show_deep_info" not in st.session_state:
    st.session_state.show_deep_info = False


def reset_app_state(scenario_name: str):
    """Resets both the simulated backend and the Streamlit frontend state."""
    reset_environment(scenario_name)
    st.session_state.stage = "idle"
    st.session_state.scenario = scenario_name
    st.session_state.investigation_steps = []
    st.session_state.diagnosis = None
    st.session_state.plan = None
    st.session_state.rejected_plan = None
    st.session_state.before_status = None
    st.session_state.after_status = None
    st.session_state.remediation_outcome = None
    st.session_state.auto_executed = False
    st.session_state.secondary_investigation = False
    st.session_state.incident_report = None
    st.session_state.show_deep_info = False
    st.session_state.is_demo_active = st.session_state.demo_mode


# -----------------------------------------------------------------------------
# 2. MINIMAL OBSERVE-FIRST SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<div style='display:flex; align-items:center; gap:0.5rem; margin-bottom:0.2rem;'>"
        "<span style='font-size:1.2rem;'>🛡️</span>"
        "<span style='font-weight:700; font-size:1.05rem; color:#F0F6FC;'>DevOps Copilot</span>"
        "</div>"
        "<div style='font-size:0.75rem; color:#8B949E; margin-bottom:1rem;'>Autonomous Incident SRE Agent</div>",
        unsafe_allow_html=True
    )

    st.markdown("<div class='sidebar-section-title'>SCENARIO</div>", unsafe_allow_html=True)
    scenario_labels = {
        "scenario_1": "Scenario 1 · Bad Deploy (Rollback)",
        "scenario_2": "Scenario 2 · Fix Fails (DB Pool)",
        "scenario_3": "Scenario 3 · Memory Leak (OOM)",
        "scenario_4": "Scenario 4 · Vendor Fallback",
        "scenario_5": "Scenario 5 · Low Confidence (Triage)"
    }
    options_keys = list(scenario_labels.keys())
    cur_idx = options_keys.index(st.session_state.scenario) if st.session_state.scenario in options_keys else 0

    chosen_scenario = st.radio(
        "Select scenario",
        options=options_keys,
        format_func=lambda x: scenario_labels.get(x, x),
        index=cur_idx,
        label_visibility="collapsed"
    )

    if chosen_scenario != st.session_state.scenario:
        reset_app_state(chosen_scenario)
        st.rerun()

    st.markdown("<div class='sidebar-section-title'>EXECUTION MODE</div>", unsafe_allow_html=True)
    demo_toggle = st.toggle(
        "Offline Demo Mode",
        value=st.session_state.demo_mode,
        help="Runs locally with verified cached responses. No live internet or Gemini API quota required."
    )
    if demo_toggle != st.session_state.demo_mode:
        st.session_state.demo_mode = demo_toggle
        st.session_state.is_demo_active = demo_toggle
        st.rerun()

    st.markdown("<div class='sidebar-section-title'>ACTIONS</div>", unsafe_allow_html=True)
    col_sb1, col_sb2 = st.columns([1.2, 1.0])
    with col_sb1:
        trigger_clicked = st.button("Trigger Alert", type="primary", use_container_width=True)
    with col_sb2:
        reset_clicked = st.button("Reset", use_container_width=True)

    if reset_clicked:
        reset_app_state(st.session_state.scenario)
        st.toast(f"Reset environment to {st.session_state.scenario}", icon="🔄")
        st.rerun()

    if trigger_clicked:
        reset_app_state(st.session_state.scenario)
        st.session_state.stage = "investigating"
        st.rerun()

    st.markdown("<div style='margin-top:1.5rem; padding-top:1rem; border-top:1px solid #21262D;'></div>", unsafe_allow_html=True)
    env = get_environment()
    active_engine = "Verified Cache (Offline)" if st.session_state.demo_mode else os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    st.markdown(
        f"<div style='font-size:0.72rem; color:#8B949E; line-height:1.6; font-family:JetBrains Mono, monospace;'>"
        f"Target: <span style='color:#C9D1D9;'>{env.service_name}</span><br>"
        f"Env: <span style='color:#C9D1D9;'>{env.scenario_id}</span><br>"
        f"Engine: <span style='color:#58A6FF;'>{active_engine}</span>"
        f"</div>",
        unsafe_allow_html=True
    )


# -----------------------------------------------------------------------------
# 3. TOP OBSERVABILITY HEADER & STATUS PILL
# -----------------------------------------------------------------------------
current_status = get_status("payment-service")
status_label = current_status.get("status", "UNKNOWN")
error_rate = current_status.get("error_rate", "0%")
current_ver = current_status.get("current_version", "unknown")
alert_time = current_status.get("timestamp", "2026-09-30 14:15:30 UTC")

col_head_left, col_head_right = st.columns([2.8, 1.2])

with col_head_left:
    st.markdown(
        "<div class='header-bar'>"
        "<div class='header-title-container'>"
        "<span class='header-icon'>🛡️</span>"
        "<span class='header-title'>DevOps Copilot</span>"
        "<span class='header-divider'>/</span>"
        "<span class='header-subtitle'>Autonomous Incident Response & Observability</span>"
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )

with col_head_right:
    is_offline = st.session_state.is_demo_active or st.session_state.demo_mode
    pill_mode = "DEMO MODE" if is_offline else "LIVE AGENT"
    pill_class = "pill-demo" if is_offline else "pill-live"
    engine_name = "Offline Cache" if is_offline else os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    
    st.markdown(
        f"<div class='header-bar' style='justify-content:flex-end;'>"
        f"<div class='header-pill-container'>"
        f"<span class='header-pill {pill_class}'>● {pill_mode}</span>"
        f"<span class='header-model-pill'>{engine_name}</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True
    )


# -----------------------------------------------------------------------------
# 4. HORIZONTAL PROGRESS STEPPER (6 STAGES)
# -----------------------------------------------------------------------------
def render_stepper(current_stage: str):
    stages = [
        ("Alert", "1"),
        ("Investigate", "2"),
        ("Root Cause", "3"),
        ("Approval", "4"),
        ("Fix", "5"),
        ("Verify / Report", "6")
    ]
    
    if current_stage == "idle":
        completed_up_to = 0
        active_idx = 1
    elif current_stage == "investigating":
        completed_up_to = 1
        active_idx = 2
    elif current_stage == "awaiting_approval":
        completed_up_to = 3
        active_idx = 4
    elif current_stage == "executing":
        completed_up_to = 4
        active_idx = 5
    elif current_stage == "verifying":
        completed_up_to = 5
        active_idx = 6
    elif current_stage == "done":
        completed_up_to = 6
        active_idx = 6
    else:
        completed_up_to = 0
        active_idx = 1

    items_html = []
    for i, (name, num) in enumerate(stages, 1):
        is_completed = i <= completed_up_to
        is_active = (i == active_idx) and not is_completed
        
        state_class = "completed" if is_completed else ("active" if is_active else "")
        bubble_text = "✓" if is_completed else num
        
        items_html.append(
            f"<div class='step-item {state_class}'>"
            f"<div class='step-bubble'>{bubble_text}</div>"
            f"<span>{name}</span>"
            f"</div>"
        )
        if i < len(stages):
            connector_class = "completed" if i < completed_up_to else ""
            items_html.append(f"<div class='step-connector {connector_class}'></div>")

    stepper_html = f"<div class='stepper-container'>{''.join(items_html)}</div>"
    st.markdown(stepper_html, unsafe_allow_html=True)

render_stepper(st.session_state.stage)


# -----------------------------------------------------------------------------
# 5. WORKFLOW ROUTING & LAYOUT
# -----------------------------------------------------------------------------

# =============================================================================
# EMPTY STATE: BEFORE ALERT
# =============================================================================
if st.session_state.stage == "idle":
    st.markdown(
        "<div class='empty-state-card'>"
        "<div class='empty-state-pill'>● SYSTEM HEALTHY</div>"
        "<div class='empty-state-title'>System Operational — No Active Outage</div>"
        "<div class='empty-state-subtitle'>"
        "Production services are healthy and error rates are nominal. "
        "Select a test scenario from the sidebar and click <b>'Trigger Alert'</b> to launch autonomous AI triage."
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )

    # 4 Preview metric cards
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    with col_e1:
        st.metric(label="Target Service", value=current_status.get("service", "payment-service"), delta="Nominal")
    with col_e2:
        st.metric(label="Error Rate", value=current_status.get("error_rate", "0.0%"), delta="Healthy")
    with col_e3:
        st.metric(label="Avg Latency", value=f"{current_status.get('avg_latency_ms', 15)}ms", delta="Normal")
    with col_e4:
        st.metric(label="Deployed Version", value=current_status.get("current_version", "v2.4.0"), delta="Active")

    # Collapsed raw state for debugging
    with st.expander("Raw state (debug)", expanded=False):
        st.json(current_status)


# =============================================================================
# ACTIVE INCIDENT: TWO-COLUMN OBSERVE & RESPOND LAYOUT
# =============================================================================
else:
    # 60% Story (Alert, Feed, Root Cause, Approval) | 40% Evidence (Metrics, Timeline, Logs)
    col_story, col_telemetry = st.columns([1.35, 0.95], gap="medium")

    # -------------------------------------------------------------------------
    # LEFT COLUMN: THE INCIDENT STORY & HUMAN DECISION GATE
    # -------------------------------------------------------------------------
    with col_story:
        # A. Compact Alert Banner
        alert_desc = f"CRITICAL: {current_status['service']} error rate spiked to {error_rate} with 500 errors"
        st.markdown(
            f"<div class='alert-banner'>"
            f"<div>"
            f"<div class='alert-banner-title'>CRITICAL INCIDENT ALERT</div>"
            f"<div class='alert-banner-desc'>{alert_desc}</div>"
            f"</div>"
            f"<div class='alert-banner-meta'>"
            f"Service: {current_status['service']}<br>"
            f"Active Version: {current_ver}<br>"
            f"Time: {alert_time}"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True
        )

        # B. Autonomous AI Investigation in Progress
        if st.session_state.stage == "investigating":
            with st.status("Agent actively investigating live infrastructure...", expanded=True) as status_box:
                def on_step_callback(step: dict):
                    st.session_state.investigation_steps.append(step)
                    stype = step.get("type")
                    tool_name = step.get("tool")

                    if stype == "INVESTIGATION_STARTED":
                        status_box.write("Agent started incident investigation triage.")
                    elif stype == "TOOL_CALL":
                        status_box.write(f"Checking `{tool_name}`: `{step.get('arguments', {})}`")
                    elif stype == "TOOL_RESULT":
                        status_box.write(f"`{tool_name}` output: {step.get('result_summary')}")
                    elif stype == "INVESTIGATION_CONCLUDED":
                        status_box.write("Evidence collection complete. Synthesizing root-cause determination.")

                try:
                    coordinator = IncidentCoordinator(demo_mode=st.session_state.demo_mode)
                    
                    if st.session_state.secondary_investigation:
                        if st.session_state.scenario == "scenario_5":
                            alert_text = (
                                "payment-service is still CRITICAL with 32.4% error rate after rollback to v2.4.1 was completed. "
                                "The previous fix did NOT solve the outage. Investigate why errors persist."
                            )
                            prev_info = (
                                "Rollback to v2.4.1 was completed, but active error rate remains at 32.4%. "
                                "Application deployment was ruled out. Look at database replica nodes."
                            )
                        else:
                            alert_text = (
                                "payment-service is still CRITICAL with 500 errors after rollback was completed. "
                                "The previous fix did NOT solve the outage. Investigate why errors persist."
                            )
                            prev_info = (
                                "Rollback to v2.3.9 was deployed, but active error rate remains > 50%. "
                                "Application deployment was ruled out. Look at database and infrastructure logs."
                            )
                    else:
                        alert_text = f"CRITICAL: {current_status['service']} error rate spiked to {error_rate} with 500s."
                        prev_info = None

                    result = coordinator.investigate(
                        alert_description=alert_text,
                        on_step_callback=on_step_callback,
                        previous_attempt_info=prev_info
                    )

                    status_box.update(label="Investigation Finished", state="complete", expanded=False)

                    st.session_state.diagnosis = result["diagnosis"]
                    st.session_state.plan = result["plan"]
                    st.session_state.is_demo_active = result.get("is_demo", False) or st.session_state.demo_mode
                    st.session_state.before_status = get_status("payment-service")
                    st.session_state.stage = "awaiting_approval"
                    st.rerun()

                except Exception as e:
                    status_box.update(label="Investigation encountered an issue", state="error")
                    st.error(f"Error communicating with Gemini API: {str(e)}")
                    st.info("The API may be experiencing high demand. Please try clicking 'Trigger Alert' again.")

        # C. Completed Investigation Tool Trace (Persistent Expander)
        if st.session_state.stage in ("awaiting_approval", "executing", "verifying", "done"):
            step_count = len(st.session_state.investigation_steps)
            with st.expander(f"View Investigation Tool Trace ({step_count} actions)", expanded=False):
                for s in st.session_state.investigation_steps:
                    stype = s.get("type")
                    ts = s.get("timestamp")
                    if stype == "TOOL_CALL":
                        st.markdown(
                            f"<div class='investigation-step-row'>"
                            f"<span class='step-icon'>🔍</span>"
                            f"<span class='log-ts'>[{ts}]</span>"
                            f"<span class='step-tool'>{s.get('tool')}</span>"
                            f"<span class='step-args'>{json.dumps(s.get('arguments', {}))}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    elif stype == "TOOL_RESULT":
                        st.markdown(
                            f"<div class='investigation-step-row'>"
                            f"<span class='step-icon'>📥</span>"
                            f"<span class='log-ts'>[{ts}]</span>"
                            f"<span class='step-result'>{s.get('result_summary')}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    elif stype == "INVESTIGATION_CONCLUDED":
                        st.markdown(
                            f"<div class='investigation-step-row'>"
                            f"<span class='step-icon'>✓</span>"
                            f"<span class='log-ts'>[{ts}]</span>"
                            f"<span class='step-result'>Agent concluded diagnostic evidence collection.</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

        # D. Root-Cause Analysis Card
        if st.session_state.diagnosis:
            diag = st.session_state.diagnosis
            conf_data = diag.get("confidence", {})
            if isinstance(conf_data, dict):
                score = conf_data.get("score", 85)
                exp = conf_data.get("explanation", "")
            else:
                score = int(conf_data) if str(conf_data).isdigit() else 85
                exp = ""

            score_color = "#3FB950" if score >= 80 else ("#E3B341" if score >= 60 else "#FF7B72")

            with st.container():
                st.markdown("<div class='obs-card'>", unsafe_allow_html=True)
                st.markdown("<div class='obs-card-header'><span class='obs-card-title'>Root-Cause Analysis</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='root-cause-header'>{diag.get('root_cause', 'Under investigation')}</div>", unsafe_allow_html=True)

                col_rc1, col_rc2 = st.columns([1.6, 1.0])
                with col_rc1:
                    st.markdown("<div style='font-size:0.78rem; font-weight:600; color:#8B949E; text-transform:uppercase;'>Verifiable Evidence</div>", unsafe_allow_html=True)
                    for ev in diag.get("evidence", []):
                        st.markdown(f"<div class='evidence-item'>• <code>{ev}</code></div>", unsafe_allow_html=True)

                    st.markdown("<div style='font-size:0.78rem; font-weight:600; color:#8B949E; text-transform:uppercase; margin-top:0.5rem;'>Reasoning</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='reasoning-text'>{diag.get('reasoning', '')}</div>", unsafe_allow_html=True)

                with col_rc2:
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; align-items:baseline; margin-bottom:4px;'>"
                        f"<span style='font-size:0.78rem; font-weight:600; color:#8B949E; text-transform:uppercase;'>Confidence</span>"
                        f"<span style='font-size:0.95rem; font-weight:700; color:{score_color}; font-family:JetBrains Mono, monospace;'>{score}%</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    st.progress(score / 100.0)
                    if exp:
                        st.caption(f"_{exp}_")

                    # Conflicting or Missing Info Warning Box
                    missing = diag.get("conflicting_or_missing_info", "")
                    if missing and missing.lower() not in ("none", "none.", "n/a"):
                        st.markdown(f"<div class='amber-callout'>⚠️ <b>Telemetry Conflict Detected:</b><br>{missing}</div>", unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

        # E. Approval Card (Human-in-the-Loop Safety Gate)
        if st.session_state.stage == "awaiting_approval" and st.session_state.plan:
            plan = st.session_state.plan
            risk = plan.get("risk_level", "HIGH").upper()
            
            card_class = "approval-card-high" if risk == "HIGH" else ("approval-card-medium" if risk == "MEDIUM" else "approval-card-low")
            badge_class = "badge-risk-high" if risk == "HIGH" else ("badge-risk-medium" if risk == "MEDIUM" else "badge-risk-low")

            st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;'>"
                f"<span class='approval-title'>Proposed Remediation Plan</span>"
                f"<span class='approval-action-badge {badge_class}'>{risk} RISK</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            st.markdown(f"<div style='font-size:0.88rem; color:#F0F6FC; margin-bottom:0.3rem;'><b>Action:</b> <code>{plan.get('action')}</code> — {plan.get('description')}</div>", unsafe_allow_html=True)

            diag = st.session_state.diagnosis or {}
            conf_data = diag.get("confidence", {})
            score = conf_data.get("score", 100) if isinstance(conf_data, dict) else (int(conf_data) if str(conf_data).isdigit() else 100)
            is_conflicting = (plan.get("action") == "investigate_further" or score < 60) and plan.get("action") != "failover_replica"

            # Branch A: Scenario 5 Conflicting Evidence (3 Operator Choices)
            if is_conflicting:
                st.markdown(
                    "<div class='amber-callout' style='margin-bottom:0.8rem;'>"
                    "<b>Conflicting Telemetry Warning (< 60% Confidence):</b><br>"
                    "Temporal proximity suggests deployment v2.4.2, but logs show errors are strictly isolated to "
                    "replication lag on database node <code>db-replica-02</code> (480s delay). Select remediation path:"
                    "</div>",
                    unsafe_allow_html=True
                )

                col_cf1, col_cf2, col_cf3 = st.columns(3)
                with col_cf1:
                    if st.button("Fail Over Replica", type="primary", use_container_width=True, help="Recommended: Drains db-replica-02 and cuts over to db-replica-01."):
                        st.session_state.plan = {
                            "action": "failover_replica",
                            "risk_level": "medium",
                            "requires_approval": True,
                            "target_service": "payment-service",
                            "description": "Isolate lagging db-replica-02 and route all traffic to healthy db-replica-01.",
                            "parameters": {
                                "service_name": "payment-service",
                                "target_replica": "db-replica-01"
                            }
                        }
                        st.session_state.stage = "executing"
                        st.rerun()

                with col_cf2:
                    if st.button("Rollback Anyway", use_container_width=True, help="Force rollback to v2.4.1 despite conflicting telemetry."):
                        st.session_state.plan = {
                            "action": "rollback",
                            "risk_level": "high",
                            "requires_approval": True,
                            "target_service": "payment-service",
                            "description": "Rollback payment-service to v2.4.1 despite conflicting telemetry.",
                            "parameters": {
                                "service_name": "payment-service",
                                "target_version": "v2.4.1"
                            }
                        }
                        st.session_state.stage = "executing"
                        st.rerun()

                with col_cf3:
                    if st.button("Gather More Info", use_container_width=True, help="Inspect database node telemetry and commit diff."):
                        st.session_state.show_deep_info = not st.session_state.get("show_deep_info", False)
                        st.rerun()

                if st.session_state.get("show_deep_info", False):
                    with st.expander("Deep Telemetry & Code Inspection", expanded=True):
                        st.markdown("""
- **Node `db-replica-02`**: Lag `480.2s` (Threshold: 5.0s), IOPS `99.4%`, Active Connections `248/250`, Queries `waiting for lock`.
- **Node `db-replica-01`**: Lag `0.1s` (Healthy), IOPS `18.2%`, Active Connections `24/250`, Status `READY`.
- **Deploy `v2.4.2` Diff**: Commit `a9f201` adds Google Analytics 4 tags to payment receipt page template. No database queries, migrations, or backend logic modified.
- **Incident INC-780 Precedent**: Past incident with identical symptoms where premature rollback caused prolonged downtime before replica failover resolved it.
                        """)

            # Branch B: Standard Approval Required (High/Medium Risk)
            elif plan.get("requires_approval"):
                st.markdown("<div style='font-size:0.8rem; color:#8B949E; margin-bottom:0.75rem;'>Policy Enforcement: Action modifies production routing or versions and requires human verification.</div>", unsafe_allow_html=True)
                col_app1, col_app2 = st.columns([1, 1])
                with col_app1:
                    if st.button("Approve Fix", type="primary", use_container_width=True):
                        st.session_state.stage = "executing"
                        st.rerun()
                with col_app2:
                    if st.button("Reject Proposal", use_container_width=True):
                        planner = RemediationPlanner()
                        plan_obj = RemediationPlan(
                            action=plan.get("action"),
                            risk_level=plan.get("risk_level"),
                            target_service=plan.get("target_service"),
                            description=plan.get("description"),
                            parameters=plan.get("parameters", {})
                        )
                        fallback = planner.get_fallback_plan(plan_obj, reason_rejected_or_failed="Operator rejected the proposal.")
                        st.session_state.rejected_plan = plan
                        st.session_state.plan = fallback.to_dict()
                        st.toast("Proposal rejected. Planner generated next-best fallback option.", icon="⚠️")
                        st.rerun()

            # Branch C: Autonomous Policy (Low Risk)
            else:
                st.markdown("<div style='font-size:0.8rem; color:#3FB950;'>Autonomous Policy: Action is classified as LOW RISK (stateless restart). Running automatically.</div>", unsafe_allow_html=True)
                time.sleep(0.8)
                st.session_state.auto_executed = True
                st.session_state.stage = "executing"
                st.rerun()

            if st.session_state.rejected_plan:
                st.info(f"Alternative Fallback Plan Proposed: Previous action `{st.session_state.rejected_plan.get('action')}` was rejected.")

            st.markdown("</div>", unsafe_allow_html=True)

        # F. Executing Stage
        if st.session_state.stage == "executing":
            plan = st.session_state.plan
            action_name = plan.get("action")
            params = plan.get("parameters", {})

            with st.spinner(f"Applying remediation `{action_name}` to infrastructure..."):
                time.sleep(1.0)
                
                if action_name == "rollback":
                    target_ver = params.get("target_version")
                    if not target_ver:
                        target_ver = "v2.4.1" if st.session_state.scenario == "scenario_5" else "v2.3.9"
                    outcome = rollback(
                        service_name=params.get("service_name", "payment-service"),
                        target_version=target_ver
                    )
                elif action_name == "restart_service":
                    outcome = restart_service(service_name=params.get("service_name", "payment-service"))
                elif action_name == "escalate_and_enable_fallback":
                    outcome = escalate_and_enable_fallback(service_name=params.get("service_name", "payment-service"))
                elif action_name == "failover_replica":
                    outcome = failover_replica(
                        service_name=params.get("service_name", "payment-service"),
                        target_replica=params.get("target_replica", "db-replica-01")
                    )
                else:
                    outcome = restart_service(service_name="payment-service")

                st.session_state.remediation_outcome = outcome
                st.session_state.after_status = get_status("payment-service")
                st.session_state.stage = "verifying"
                st.rerun()

        # G. Verification Outcome Banners (No Flashy Balloons)
        if st.session_state.stage in ("verifying", "done"):
            a_stat = st.session_state.after_status or {}

            if a_stat.get("status") == "HEALTHY":
                msg = st.session_state.remediation_outcome.get("message", "Service recovered.") if st.session_state.remediation_outcome else "Service recovered."
                st.markdown(
                    f"<div style='background:rgba(46,160,67,0.12); border:1px solid rgba(46,160,67,0.4); border-left:4px solid #2EA043; border-radius:6px; padding:0.75rem 1rem; margin-bottom:1rem; color:#56D364;'>"
                    f"<b>Verification Succeeded:</b> {msg}"
                    f"</div>",
                    unsafe_allow_html=True
                )
                st.session_state.stage = "done"

            else:
                msg = st.session_state.remediation_outcome.get("message", "Service still returning errors.") if st.session_state.remediation_outcome else "Service still returning errors."
                st.markdown(
                    f"<div style='background:rgba(248,81,73,0.12); border:1px solid rgba(248,81,73,0.4); border-left:4px solid #F85149; border-radius:6px; padding:0.75rem 1rem; margin-bottom:1rem; color:#FF7B72;'>"
                    f"<b>Verification Failed:</b> {msg}"
                    f"</div>",
                    unsafe_allow_html=True
                )

                if not st.session_state.secondary_investigation:
                    st.markdown(
                        "<div style='font-size:0.82rem; color:#8B949E; margin-bottom:0.6rem;'>"
                        "Hypothesis Disproven: Executed remediation did not clear 500 error rates. True root cause lies deeper in infrastructure."
                        "</div>",
                        unsafe_allow_html=True
                    )
                    if st.button("Re-investigate Next Most Likely Cause", type="primary"):
                        st.session_state.secondary_investigation = True
                        st.session_state.stage = "investigating"
                        st.rerun()
                else:
                    st.session_state.stage = "done"

        # H. Incident Postmortem Report
        if st.session_state.stage == "done":
            if st.session_state.incident_report is None:
                with st.spinner("Compiling incident postmortem report..."):
                    failed_attempt = None
                    if st.session_state.secondary_investigation:
                        if st.session_state.scenario == "scenario_5":
                            failed_attempt = (
                                "Initial rollback to v2.4.1 completed, but service remained CRITICAL "
                                "(error rate 32.4%) because the true root cause was replication lag on db-replica-02, not the application deploy."
                            )
                        else:
                            failed_attempt = (
                                "Initial rollback to v2.3.9 completed successfully, but service remained CRITICAL "
                                "(error rate 52.4%) because the PostgreSQL primary database connection pool was saturated."
                            )

                    scenario_num = int(st.session_state.scenario.split("_")[-1]) if "_" in st.session_state.scenario else 1
                    incident_record = {
                        "incident_id": f"INC-20260930-{scenario_num:02d}",
                        "scenario": st.session_state.scenario,
                        "service": current_status.get("service", "payment-service"),
                        "alert": f"CRITICAL: {current_status.get('service')} error rate spiked to {current_status.get('error_rate')} with 500 errors",
                        "root_cause": st.session_state.diagnosis.get("root_cause") if st.session_state.diagnosis else "",
                        "evidence": st.session_state.diagnosis.get("evidence", []) if st.session_state.diagnosis else [],
                        "confidence": st.session_state.diagnosis.get("confidence") if st.session_state.diagnosis else {},
                        "action_taken": st.session_state.plan.get("action") if st.session_state.plan else "",
                        "action_description": st.session_state.plan.get("description") if st.session_state.plan else "",
                        "who_approved": "On-call SRE (Human Operator)",
                        "before_status": st.session_state.before_status,
                        "after_status": st.session_state.after_status,
                        "remediation_result": st.session_state.remediation_outcome,
                        "failed_remediation_attempt": failed_attempt,
                        "timeline_steps": [
                            {"timestamp": s.get("timestamp"), "event": s.get("message") or f"{s.get('tool')} ({s.get('result_summary', '')})"}
                            for s in st.session_state.investigation_steps
                            if s.get("type") in ("INVESTIGATION_STARTED", "TOOL_RESULT", "INVESTIGATION_CONCLUDED", "DIAGNOSIS_COMPLETE")
                        ]
                    }
                    rep_res = generate_incident_report(
                        incident_record=incident_record,
                        demo_mode=st.session_state.demo_mode
                    )
                    st.session_state.incident_report = rep_res["report_markdown"]
                    st.session_state.is_demo_active = st.session_state.is_demo_active or rep_res.get("is_demo", False)

            if st.session_state.incident_report:
                with st.container():
                    st.markdown("<div class='obs-card'>", unsafe_allow_html=True)
                    col_rp1, col_rp2 = st.columns([2.5, 1.2])
                    with col_rp1:
                        st.markdown("<div class='obs-card-title'>Incident Postmortem Report</div>", unsafe_allow_html=True)
                    with col_rp2:
                        st.download_button(
                            label="Download Report (.md)",
                            data=st.session_state.incident_report,
                            file_name=f"postmortem_{st.session_state.scenario}.md",
                            mime="text/markdown",
                            use_container_width=True
                        )
                    st.markdown("<hr style='border:none; border-top:1px solid #21262D; margin:0.5rem 0 1rem 0;'>", unsafe_allow_html=True)
                    st.markdown(st.session_state.incident_report)
                    st.markdown("</div>", unsafe_allow_html=True)


    # -------------------------------------------------------------------------
    # RIGHT COLUMN: LIVE EVIDENCE & TELEMETRY PANEL
    # -------------------------------------------------------------------------
    with col_telemetry:
        # A. Live Status Metrics Panel
        st.markdown("<div class='obs-card-title' style='margin-bottom:0.5rem;'>Live Service Status</div>", unsafe_allow_html=True)
        
        stat_display = st.session_state.after_status if st.session_state.stage in ("verifying", "done") else current_status
        b_stat = st.session_state.before_status or {}

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(
                label="Health Status",
                value=stat_display.get("status", "UNKNOWN"),
                delta="Recovered" if stat_display.get("status") == "HEALTHY" and st.session_state.stage in ("verifying", "done") else None,
                delta_color="normal"
            )
        with col_m2:
            current_err = stat_display.get("error_rate", "0%")
            delta_val = f"Was {b_stat.get('error_rate')}" if b_stat.get("error_rate") and st.session_state.stage in ("verifying", "done") else None
            st.metric(
                label="Error Rate",
                value=current_err,
                delta=delta_val,
                delta_color="inverse"
            )

        col_m3, col_m4 = st.columns(2)
        with col_m3:
            st.metric(
                label="Deployed Version",
                value=stat_display.get("current_version", "unknown"),
                delta=f"Was {b_stat.get('current_version')}" if b_stat.get("current_version") and st.session_state.stage in ("verifying", "done") else None
            )
        with col_m4:
            if "fallback_provider_enabled" in stat_display:
                is_fb = stat_display.get("fallback_provider_enabled")
                st.metric(
                    label="Payment Route",
                    value="StripeFallback" if is_fb else "PayGate Primary",
                    delta="Cutover Complete" if is_fb else "Primary Down",
                    delta_color="normal" if is_fb else "inverse"
                )
            elif "failing_node" in stat_display or "replica_lag_sec" in stat_display:
                failing = stat_display.get("failing_node")
                st.metric(
                    label="Active Replica",
                    value="db-replica-01" if "DRAINED" in str(failing) else "db-replica-02",
                    delta="Failover Complete" if "DRAINED" in str(failing) else "480s Lag Detected",
                    delta_color="normal" if "DRAINED" in str(failing) else "inverse"
                )
            elif "memory_pct" in stat_display:
                st.metric(
                    label="Memory Usage",
                    value=f"{stat_display.get('memory_usage_mb', 0)}MB ({stat_display.get('memory_pct')})",
                    delta=f"Was {b_stat.get('memory_pct')}" if b_stat.get("memory_pct") and st.session_state.stage in ("verifying", "done") else None,
                    delta_color="inverse"
                )
            else:
                st.metric(
                    label="DB Connections",
                    value=f"{stat_display.get('active_db_connections', 0)} / {stat_display.get('max_db_connections', 0)}",
                    delta=stat_display.get("db_status", "ONLINE")
                )

        st.markdown("<div style='margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)

        # B. Incident Error Rate Timeline Chart
        st.markdown("<div class='obs-card-title' style='margin-bottom:0.4rem;'>Error Rate Over Time</div>", unsafe_allow_html=True)
        timeline_data = get_metrics_timeline("payment-service")
        if timeline_data:
            df_timeline = pd.DataFrame(timeline_data)
            chart_df = df_timeline.set_index("time")[["error_rate"]]
            st.line_chart(chart_df, color="#F85149", height=200)

            annotated_events = [d for d in timeline_data if d.get("event")]
            if annotated_events:
                st.markdown("<div style='display:flex; flex-wrap:wrap; gap:0.5rem; margin-top:0.25rem;'>", unsafe_allow_html=True)
                for ev in annotated_events:
                    st.caption(f"📍 `{ev['time']}`: {ev['event']} ({ev['error_rate']}%)")
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)

        # C. Live Monospace Log Stream Viewer (Datadog / Grafana Style)
        st.markdown("<div class='obs-card-title' style='margin-bottom:0.4rem;'>Live Infrastructure Logs</div>", unsafe_allow_html=True)
        logs_data = get_logs(service_name="payment-service", limit=25)
        
        log_html_lines = []
        for entry in logs_data:
            lvl = entry.get("level", "INFO").upper()
            ts = entry.get("timestamp", "").split("T")[-1].replace("Z", "")
            msg = entry.get("message", "")
            is_err = lvl in ("ERROR", "FATAL")
            highlight_class = "highlight" if is_err else ""
            lvl_class = f"log-level-{lvl.lower()}"
            
            log_html_lines.append(
                f"<div class='log-stream-line {highlight_class}'>"
                f"<span class='log-ts'>[{ts}]</span> "
                f"<span class='{lvl_class}'>[{lvl}]</span> "
                f"<span class='log-msg'>{msg}</span>"
                f"</div>"
            )
        
        logs_html = f"<div class='log-stream-container'>{''.join(log_html_lines)}</div>"
        st.markdown(logs_html, unsafe_allow_html=True)

        # D. Collapsed Raw State Debug Expander
        with st.expander("Raw state (debug)", expanded=False):
            st.json(current_status)
