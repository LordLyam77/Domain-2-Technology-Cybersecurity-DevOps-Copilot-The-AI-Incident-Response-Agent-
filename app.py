"""
DevOps Copilot: Streamlit Web UI.

WHY THIS FILE EXISTS:
This is the user interface where human operators and SREs collaborate with the AI agent.
Incident response is a high-stakes team effort:
1. SREs need full visibility into what the AI is checking in real time (Investigation Feed).
2. SREs need clear evidence, confidence scores, and reasoning (Root-Cause Card).
3. Dangerous actions (like rolling back production) must NOT run without explicit human consent (Approval Gate).
4. After any remediation, the system must verify recovery and handle failures gracefully (Verification & Fallbacks).
"""

import os
import json
import time
import streamlit as st
from dotenv import load_dotenv

from simulation.environment import (
    reset_environment,
    get_environment,
    get_status,
    get_logs,
    rollback,
    restart_service
)
from agent.coordinator import IncidentCoordinator
from agent.planner import RemediationPlanner, RemediationPlan
from agent.reporter import generate_incident_report
from agent.gemini_gateway import is_demo_mode_env

# Load environment configuration
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="DevOps Copilot: AI Incident Response",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 1. SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
# WHY: Streamlit reruns the whole script from top to bottom on every user click.
# st.session_state acts like the browser's persistent memory so we don't lose
# the active investigation, steps, diagnosis, or approval status when buttons are pressed.
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

if "secondary_investigation" not in st.session_state:
    st.session_state.secondary_investigation = False

if "incident_report" not in st.session_state:
    st.session_state.incident_report = None


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
    st.session_state.secondary_investigation = False
    st.session_state.incident_report = None
    st.session_state.is_demo_active = st.session_state.demo_mode


# -----------------------------------------------------------------------------
# 2. SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🛡️ DevOps Copilot")
    st.caption("Autonomous AI Incident Response Agent")
    st.markdown("---")

    st.subheader("1. Select Outage Scenario")
    scenario_option = st.radio(
        "Choose test scenario:",
        options=[
            ("scenario_1", "Scenario 1: Bad Deploy (Rollback recovers)"),
            ("scenario_2", "Scenario 2: Fix Fails (Underlying DB exhaustion)")
        ],
        format_func=lambda x: x[1],
        index=0 if st.session_state.scenario == "scenario_1" else 1,
        help="Scenario 1 tests a deployment bug. Scenario 2 tests deeper database saturation where rollback fails."
    )
    chosen_scenario = scenario_option[0]

    # If the user switches scenario radio button, re-initialize
    if chosen_scenario != st.session_state.scenario:
        reset_app_state(chosen_scenario)
        st.rerun()

    st.markdown("---")
    st.subheader("2. Demo Mode (Safety Net)")
    demo_toggle = st.toggle(
        "🛡️ Offline Demo Mode",
        value=st.session_state.demo_mode,
        help="When enabled, runs 100% locally with NO internet and NO API key required, using pre-recorded verified responses."
    )
    if demo_toggle != st.session_state.demo_mode:
        st.session_state.demo_mode = demo_toggle
        st.session_state.is_demo_active = demo_toggle
        st.rerun()

    if st.session_state.is_demo_active or st.session_state.demo_mode:
        st.markdown(
            "<span style='background-color:#fff8c5; color:#9a6700; border:1px solid #d4a72c; padding:3px 8px; border-radius:10px; font-size:12px; font-weight:bold;'>🏷️ DEMO MODE ACTIVE (OFFLINE)</span>",
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.subheader("3. Simulation Controls")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        trigger_clicked = st.button("🚨 Trigger Alert", type="primary", use_container_width=True)
    with col_btn2:
        reset_clicked = st.button("🔄 Reset", use_container_width=True)

    if reset_clicked:
        reset_app_state(st.session_state.scenario)
        st.toast(f"Reset environment to {st.session_state.scenario}", icon="🔄")
        st.rerun()

    if trigger_clicked:
        reset_app_state(st.session_state.scenario)
        st.session_state.stage = "investigating"
        st.rerun()

    st.markdown("---")
    st.markdown("### System Telemetry")
    env = get_environment()
    st.text(f"Service: {env.service_name}")
    st.text(f"Environment: {env.scenario_id}")
    mode_label = "Local Cache (Offline)" if st.session_state.demo_mode else os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview')
    st.text(f"Active Engine: {mode_label}")


# -----------------------------------------------------------------------------
# 3. TOP ALERT BANNER & DEMO STATUS
# -----------------------------------------------------------------------------
current_status = get_status("payment-service")
status_label = current_status.get("status", "UNKNOWN")
error_rate = current_status.get("error_rate", "0%")
current_ver = current_status.get("current_version", "unknown")
alert_time = current_status.get("timestamp", "2026-09-30 14:15:30 UTC")

if st.session_state.is_demo_active or st.session_state.demo_mode:
    st.info("💡 **DEMO MODE SAFETY NET ACTIVE**: Operating with high-fidelity pre-recorded responses. No live API quota or internet required.")

# The alert banner only displays once an incident has been triggered (not in idle state)
if st.session_state.stage != "idle":
    if status_label == "CRITICAL":
        st.error(
            f"🚨 **CRITICAL OUTAGE ALERT**: Service `{current_status['service']}` (v{current_ver}) is reporting **{error_rate}** HTTP 500 errors! | "
            f"Alert Time: `{alert_time}` | Health Status: **{status_label}**"
        )
    elif status_label == "HEALTHY":
        st.success(
            f"✅ **SYSTEM HEALTHY**: Service `{current_status['service']}` is running smoothly on `{current_ver}` with **{error_rate}** error rate."
        )
    else:
        st.warning(f"⚠️ Service `{current_status['service']}` status: **{status_label}** (Error rate: {error_rate})")



# -----------------------------------------------------------------------------
# 4. MAIN WORKFLOW CONTROLLER
# -----------------------------------------------------------------------------

# STAGE: IDLE
if st.session_state.stage == "idle":
    st.info("👈 Click **'🚨 Trigger Alert'** in the sidebar to simulate an incoming production incident.")
    
    # Display preview of active service state
    st.subheader("Current Environment State")
    st.json(current_status)


# STAGE: INVESTIGATING (Live execution of agent ReAct loop)
elif st.session_state.stage == "investigating":
    st.subheader("🕵️ Autonomous AI Investigation in Progress")

    # Live Streamlit Status container to stream tool calls one by one
    with st.status("Agent actively investigating live infrastructure...", expanded=True) as status_box:
        def on_step_callback(step: dict):
            # Save step to session state so it persists across reruns
            st.session_state.investigation_steps.append(step)
            stype = step.get("type")
            tool_name = step.get("tool")

            if stype == "INVESTIGATION_STARTED":
                status_box.write("🚀 **Agent started incident investigation triage.**")
            elif stype == "TOOL_CALL":
                status_box.write(f"🔍 **Checking `{tool_name}`** with parameters: `{step.get('arguments', {})}`")
            elif stype == "TOOL_RESULT":
                status_box.write(f"📥 **`{tool_name}` output**: {step.get('result_summary')}")
            elif stype == "INVESTIGATION_CONCLUDED":
                status_box.write("✅ **Evidence collection complete. Synthesizing root-cause determination...**")

        try:
            coordinator = IncidentCoordinator(demo_mode=st.session_state.demo_mode)
            
            # If this is a secondary investigation because the first fix failed (Scenario 2):
            if st.session_state.secondary_investigation:
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

            # Execute the agent investigation
            result = coordinator.investigate(
                alert_description=alert_text,
                on_step_callback=on_step_callback,
                previous_attempt_info=prev_info
            )

            status_box.update(label="Investigation Finished!", state="complete", expanded=False)

            # Save diagnosis, plan, and demo flag to session state
            st.session_state.diagnosis = result["diagnosis"]
            st.session_state.plan = result["plan"]
            st.session_state.is_demo_active = result.get("is_demo", False) or st.session_state.demo_mode
            st.session_state.before_status = get_status("payment-service")
            st.session_state.stage = "awaiting_approval"
            st.rerun()

        except Exception as e:
            status_box.update(label="Investigation encountered an issue", state="error")
            st.error(f"⚠️ Error communicating with Gemini API: {str(e)}")
            st.info("The API may be experiencing high demand. Please try clicking 'Trigger Alert' again.")


# STAGE: AWAITING APPROVAL, EXECUTING, VERIFYING, OR DONE
if st.session_state.stage in ("awaiting_approval", "executing", "verifying", "done"):

    # -------------------------------------------------------------------------
    # A. INVESTIGATION FEED (PERSISTENT ACCORDION)
    # -------------------------------------------------------------------------
    with st.expander("📋 View Live Investigation Tool Trace", expanded=False):
        for s in st.session_state.investigation_steps:
            stype = s.get("type")
            ts = s.get("timestamp")
            if stype == "TOOL_CALL":
                st.markdown(f"**[{ts}] 🔍 Tool Called:** `{s.get('tool')}` — Parameters: `{s.get('arguments')}`")
            elif stype == "TOOL_RESULT":
                st.markdown(f"**[{ts}] 📥 Tool Output:** {s.get('result_summary')}")
            elif stype == "INVESTIGATION_CONCLUDED":
                st.markdown(f"**[{ts}] ✅ Agent concluded evidence gathering.**")

    # -------------------------------------------------------------------------
    # B. ROOT-CAUSE CARD
    # -------------------------------------------------------------------------
    if st.session_state.diagnosis:
        diag = st.session_state.diagnosis
        st.markdown("### 🔍 Root-Cause Analysis")

        # Main Root Cause Box
        st.info(f"**Root Cause:** {diag.get('root_cause', 'Under investigation')}")

        col_diag1, col_diag2 = st.columns([3, 2])

        with col_diag1:
            st.markdown("**Verifiable Evidence:**")
            for ev in diag.get("evidence", []):
                st.markdown(f"- {ev}")

            st.markdown("**Reasoning:**")
            st.write(diag.get("reasoning", ""))

        with col_diag2:
            # Confidence Progress Bar
            conf_data = diag.get("confidence", {})
            if isinstance(conf_data, dict):
                score = conf_data.get("score", 85)
                exp = conf_data.get("explanation", "")
            else:
                score = int(conf_data) if str(conf_data).isdigit() else 85
                exp = ""

            st.markdown(f"**Confidence Level: {score}%**")
            st.progress(score / 100.0)
            if exp:
                st.caption(f"_{exp}_")

            # Conflicting or Missing Info Warning Box
            missing = diag.get("conflicting_or_missing_info", "")
            if missing and missing.lower() not in ("none", "none.", "n/a"):
                st.warning(f"⚠️ **Conflicting or Missing Telemetry:**\n{missing}")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # C. APPROVAL CARD (HUMAN-IN-THE-LOOP SAFETY GATE)
    # -------------------------------------------------------------------------
    if st.session_state.stage == "awaiting_approval" and st.session_state.plan:
        plan = st.session_state.plan
        st.markdown("### 🛡️ Remediation Plan & Approval Gate")

        # Risk Badge
        risk = plan.get("risk_level", "HIGH").upper()
        if risk == "HIGH":
            badge_html = "<span style='background-color:#ffebe9; color:#cf222e; border:1px solid #ff8182; padding:4px 10px; border-radius:12px; font-weight:bold;'>🚨 HIGH RISK</span>"
        else:
            badge_html = "<span style='background-color:#dafbe1; color:#1a7f37; border:1px solid #4ac26b; padding:4px 10px; border-radius:12px; font-weight:bold;'>🟢 LOW RISK</span>"

        st.markdown(f"**Proposed Action:** `{plan.get('action')}` &nbsp; {badge_html}", unsafe_allow_html=True)
        st.write(f"**Description:** {plan.get('description')}")

        if plan.get("requires_approval"):
            st.warning("⚠️ **Safety Policy Enforcement:** This action modifies production versions and requires explicit human approval before execution.")
        else:
            st.success("ℹ️ **Low Risk Action:** This operation does not alter binaries and can execute safely.")

        col_app1, col_app2 = st.columns([1, 1])

        with col_app1:
            if st.button("✅ Approve Fix", type="primary", use_container_width=True):
                st.session_state.stage = "executing"
                st.rerun()

        with col_app2:
            if st.button("❌ Reject Proposal", use_container_width=True):
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

        # If user previously rejected, show message explaining fallback
        if st.session_state.rejected_plan:
            st.info(f"🔄 **Alternative Fallback Plan Proposed:** Previous action `{st.session_state.rejected_plan.get('action')}` was rejected.")


    # -------------------------------------------------------------------------
    # D. EXECUTING & VERIFYING STAGE
    # -------------------------------------------------------------------------
    if st.session_state.stage == "executing":
        st.subheader("⚡ Executing Remediation Action...")
        plan = st.session_state.plan
        action_name = plan.get("action")
        params = plan.get("parameters", {})

        with st.spinner(f"Applying action `{action_name}` to simulated infrastructure..."):
            time.sleep(1.0)  # Brief delay for realistic UI transition
            
            # Execute in simulation
            if action_name == "rollback":
                outcome = rollback(
                    service_name=params.get("service_name", "payment-service"),
                    target_version=params.get("target_version", "v2.3.9")
                )
            elif action_name == "restart_service":
                outcome = restart_service(
                    service_name=params.get("service_name", "payment-service")
                )
            else:
                outcome = restart_service(service_name="payment-service")

            st.session_state.remediation_outcome = outcome
            st.session_state.after_status = get_status("payment-service")
            st.session_state.stage = "verifying"
            st.rerun()


    # -------------------------------------------------------------------------
    # E. VERIFICATION & BEFORE/AFTER COMPARISON
    # -------------------------------------------------------------------------
    if st.session_state.stage in ("verifying", "done"):
        st.markdown("### 📊 Verification & Recovery Analysis")

        b_stat = st.session_state.before_status or {}
        a_stat = st.session_state.after_status or {}

        # Before / After Metrics Display
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        with col_m1:
            st.metric(
                label="Health Status",
                value=a_stat.get("status", "UNKNOWN"),
                delta="Recovered" if a_stat.get("status") == "HEALTHY" else "STILL UNHEALTHY",
                delta_color="normal" if a_stat.get("status") == "HEALTHY" else "inverse"
            )

        with col_m2:
            st.metric(
                label="Error Rate",
                value=a_stat.get("error_rate", "0%"),
                delta=f"Was {b_stat.get('error_rate', '0%')}",
                delta_color="inverse"
            )

        with col_m3:
            st.metric(
                label="Active Version",
                value=a_stat.get("current_version", "unknown"),
                delta=f"Was {b_stat.get('current_version', 'unknown')}"
            )

        with col_m4:
            st.metric(
                label="DB Connections",
                value=f"{a_stat.get('active_db_connections', 0)} / {a_stat.get('max_db_connections', 0)}",
                delta=a_stat.get("db_status", "ONLINE")
            )

        # SCENARIO 1 SUCCESS OUTCOME
        if a_stat.get("status") == "HEALTHY":
            st.balloons()
            st.success(
                f"🎉 **VERIFICATION SUCCEEDED**: {st.session_state.remediation_outcome.get('message', 'Service recovered.')}"
            )
            st.session_state.stage = "done"

        # SCENARIO 2 FAILURE OUTCOME: Rollback did NOT work!
        else:
            st.error(
                f"❌ **VERIFICATION FAILED: Fix did NOT work!**\n\n"
                f"{st.session_state.remediation_outcome.get('message', 'Service still returning errors.')}"
            )

            # If we haven't already done the secondary investigation, show button or automatically trigger it
            if not st.session_state.secondary_investigation:
                st.warning(
                    "⚠️ **Hypothesis Disproven**: Rolling back the application version did not resolve the 500 errors. "
                    "The true root cause is NOT the code deployment. Re-running agent to investigate deeper infrastructure..."
                )
                if st.button("🔍 Re-investigate Next Most Likely Cause", type="primary"):
                    st.session_state.secondary_investigation = True
                    st.session_state.stage = "investigating"
                    st.rerun()
            else:
                st.session_state.stage = "done"

    # -------------------------------------------------------------------------
    # F. INCIDENT POSTMORTEM REPORT
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📄 Automated Incident Postmortem Report")

    if st.session_state.stage == "done":
        if st.session_state.incident_report is None:
            with st.spinner("Generating professional SRE Incident Postmortem Report..."):
                failed_attempt = None
                if st.session_state.secondary_investigation:
                    failed_attempt = (
                        "Initial rollback to v2.3.9 completed successfully, but service remained CRITICAL "
                        "(error rate 52.4%) because the PostgreSQL primary database connection pool was saturated."
                    )

                incident_record = {
                    "incident_id": f"INC-20260930-{1 if '1' in st.session_state.scenario else 2:02d}",
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
                st.markdown(st.session_state.incident_report)
                
                col_dl1, col_dl2 = st.columns([1, 4])
                with col_dl1:
                    st.download_button(
                        label="📥 Download Report (.md)",
                        data=st.session_state.incident_report,
                        file_name=f"postmortem_{st.session_state.scenario}.md",
                        mime="text/markdown",
                        type="primary",
                        use_container_width=True
                    )
    else:
        st.info("ℹ️ Complete the investigation, approval, and verification stages to automatically generate the postmortem report.")
