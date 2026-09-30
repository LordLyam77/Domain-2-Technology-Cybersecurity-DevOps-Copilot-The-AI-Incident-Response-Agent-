"""
Test script for Phase 2: Agent Core with Gemini Function Calling.

WHY THIS SCRIPT EXISTS:
This script demonstrates the full autonomous agent loop across both scenarios:
1. Runs Scenario 1 (Bad Deploy):
   - Agent inspects status, logs, deploys, and past incidents.
   - Diagnoses bad DB pool config in v2.4.0.
   - Produces structured JSON with evidence & confidence.
   - Proposes HIGH-risk rollback (requires human approval).
   - Executes approved rollback and confirms recovery.
2. Runs Scenario 2 (Fix Fails):
   - Agent inspects the environment and uncovers Postgres connection exhaustion.
   - Tests human rejection / fallback planning.
"""

import json
from simulation.environment import reset_environment, get_environment, rollback, restart_service
from agent.coordinator import IncidentCoordinator
from agent.planner import RemediationPlanner


def print_banner(title: str):
    print("\n" + "=" * 70, flush=True)
    print(f"  {title.upper()}", flush=True)
    print("=" * 70, flush=True)


def print_step(step: dict):
    stype = step.get("type")
    num = step.get("step_number")
    ts = step.get("timestamp")
    if stype == "INVESTIGATION_STARTED":
        print(f"[{ts}] [Step {num}] >> {step.get('message')}", flush=True)
    elif stype == "TOOL_CALL":
        print(f"[{ts}] [Step {num}] -> AGENT INVOKED TOOL: `{step.get('tool')}`", flush=True)
        print(f"                Parameters: {json.dumps(step.get('arguments', {}))}", flush=True)
    elif stype == "TOOL_RESULT":
        print(f"[{ts}] [Step {num}] <- TOOL RETURNED DATA: {step.get('result_summary')}", flush=True)
    elif stype == "INVESTIGATION_CONCLUDED":
        print(f"[{ts}] [Step {num}] >> {step.get('message')}", flush=True)
    elif stype == "DIAGNOSIS_COMPLETE":
        print(f"[{ts}] [Step {num}] ** FINAL DIAGNOSIS READY **", flush=True)


def test_agent_scenario_1():
    print_banner("RUNNING SCENARIO 1: BAD DEPLOY INVESTIGATION")
    
    # 1. Reset simulation to Scenario 1
    reset_environment("scenario_1")
    env = get_environment()
    print(f"Environment initialized: {env.scenario_id}")
    print(f"Active Service: {env.service_name} | Initial Status: {env.state.get('status')}")

    # 2. Instantiate Coordinator
    coordinator = IncidentCoordinator(env=env)

    # 3. Run Investigation
    print("\nStarting autonomous multi-turn tool investigation with Gemini...\n")
    result = coordinator.investigate(
        alert_description="CRITICAL ALERT: payment-service 500 error rate surged to 43.5% with database connection timeouts.",
        on_step_callback=print_step
    )

    diagnosis = result["diagnosis"]
    plan = result["plan"]

    print("\n" + "-" * 50)
    print("STRUCTURED JSON DIAGNOSIS:")
    print("-" * 50)
    print(json.dumps(diagnosis, indent=2))

    print("\n" + "-" * 50)
    print("PROPOSED REMEDIATION PLAN:")
    print("-" * 50)
    print(f"Action:             {plan.get('action')}")
    print(f"Risk Level:         {plan.get('risk_level')}")
    print(f"Requires Approval:  {plan.get('requires_approval')}")
    print(f"Description:        {plan.get('description')}")
    print(f"Fallback Action:    {plan.get('fallback_action')}")

    # Verify structured fields exist
    assert "root_cause" in diagnosis, "Diagnosis must contain root_cause"
    assert "evidence" in diagnosis and len(diagnosis["evidence"]) > 0, "Diagnosis must contain evidence"
    assert "confidence" in diagnosis, "Diagnosis must contain confidence"
    assert plan["risk_level"] == "HIGH", "Rollback should be classified as HIGH risk"
    assert plan["requires_approval"] is True, "HIGH risk plan must require approval"

    # 4. Simulate Human Approval Gate
    print("\n>>> SIMULATING HUMAN APPROVAL GATE: Operator reviews HIGH-risk rollback proposal.")
    print(">>> Operator Action: [APPROVED]")
    
    # Execute the approved remediation
    exec_result = rollback(service_name="payment-service", target_version="v2.3.9")
    print(f"\nExecution Result: {json.dumps(exec_result, indent=2)}")
    
    # Verify post-remediation health
    post_status = env.get_status("payment-service")
    print(f"\nPost-Remediation Status: {post_status['status']} (Error Rate: {post_status['error_rate']})")
    assert post_status["status"] == "HEALTHY", "Service should recover to HEALTHY in Scenario 1"
    print("\n*** SCENARIO 1 SUCCESSFULLY RESOLVED AND VERIFIED! ***")


def test_agent_scenario_2():
    print_banner("RUNNING SCENARIO 2: FIX FAILS (UNDERLYING DB OUTAGE)")

    # 1. Reset simulation to Scenario 2
    reset_environment("scenario_2")
    env = get_environment()
    print(f"Environment initialized: {env.scenario_id}")
    print(f"Active Service: {env.service_name} | Initial Status: {env.state.get('status')}")

    # 2. Instantiate Coordinator
    coordinator = IncidentCoordinator(env=env)

    # 3. Run Investigation
    print("\nStarting autonomous multi-turn tool investigation with Gemini...\n")
    result = coordinator.investigate(
        alert_description="CRITICAL ALERT: payment-service is experiencing 500 errors and DB acquisition timeouts.",
        on_step_callback=print_step
    )

    diagnosis = result["diagnosis"]
    plan = result["plan"]

    print("\n" + "-" * 50)
    print("STRUCTURED JSON DIAGNOSIS (SCENARIO 2):")
    print("-" * 50)
    print(json.dumps(diagnosis, indent=2))

    print("\n" + "-" * 50)
    print("PLAN & FALLBACK BEHAVIOR:")
    print("-" * 50)
    print(f"Initial Proposed Action: {plan.get('action')}")
    print(f"Risk Level:              {plan.get('risk_level')}")

    # Test what happens if the human REJECTS the high-risk rollback or if the rollback fails
    planner = RemediationPlanner()
    plan_obj = result["remediation_plan_obj"]
    
    print("\n>>> SIMULATING HUMAN REJECTION: Operator reviews proposal and clicks [REJECT].")
    fallback = planner.get_fallback_plan(plan_obj, reason_rejected_or_failed="Operator rejected production rollback")
    print(f"Fallback Action Proposed: {fallback.action} ({fallback.description})")
    print(f"Fallback Risk Level:      {fallback.risk_level} (Requires Approval: {fallback.requires_approval})")
    print(f"Fallback Reasoning:       {fallback.reasoning}")

    assert fallback.action == "restart_service", "Fallback for rejected rollback should be restart_service"
    print("\n*** SCENARIO 2 TEST COMPLETED SUCCESSFULLY! ***")


if __name__ == "__main__":
    import sys
    import time

    arg = sys.argv[1] if len(sys.argv) > 1 else "all"

    if arg in ("1", "scenario_1", "all"):
        test_agent_scenario_1()
    
    if arg in ("2", "scenario_2", "all"):
        if arg == "all":
            print("\nPausing 15 seconds to respect free-tier API rate limits...", flush=True)
            time.sleep(15)
        test_agent_scenario_2()
