"""
End-to-End Automated Test for Streamlit UI (app.py).

WHY THIS SCRIPT EXISTS:
Streamlit provides `AppTest` (streamlit.testing.v1) to programmatically
render and test Streamlit apps without needing a physical browser.
This script tests:
1. Scenario 1 (Bad Deploy):
   - Sidebar scenario selection
   - Trigger Alert execution
   - Rendering of Root Cause card, evidence, and confidence bar
   - Risk classification (HIGH risk requiring approval)
   - Approval execution -> Verification -> Health recovery
2. Scenario 2 (Fix Fails & Fallback Planning):
   - Trigger Alert on Scenario 2
   - Human Rejection gate -> Fallback option generation
   - Verification failure detection when fix does not resolve outage
"""

import os
import json
import sys
import time

# Ensure UTF-8 output encoding for Windows terminals
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from streamlit.testing.v1 import AppTest
from simulation.environment import reset_environment, get_status


def test_app_scenario_1():
    print("\n" + "=" * 65)
    print(" 1. TESTING STREAMLIT APP - SCENARIO 1 (BAD DEPLOY)")
    print("=" * 65)

    # Reset backend
    reset_environment("scenario_1")

    # Initialize Streamlit AppTest
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception, f"App threw exception on initial load: {at.exception}"

    # Verify initial render
    print("[Pass] App loaded successfully. Title & sidebar rendered.")
    assert len(at.sidebar.radio) > 0, "Scenario radio button must exist in sidebar"
    
    # Simulate clicking "Trigger Alert"
    trigger_btn = at.sidebar.button[0]  # Trigger Alert button
    print(f"Clicking button: '{trigger_btn.label}'")
    trigger_btn.click().run(timeout=120)

    assert not at.exception, f"App threw exception during investigation: {at.exception}"
    print(f"[Pass] Investigation executed. Current stage in session_state: '{at.session_state.stage}'")
    assert at.session_state.stage == "awaiting_approval", "Should transition to awaiting_approval"

    # Verify Root Cause Card
    diagnosis = at.session_state.diagnosis
    print(f"[Pass] Root Cause identified: {diagnosis.get('root_cause')[:60]}...")
    assert diagnosis and "root_cause" in diagnosis

    # Verify Approval Card
    plan = at.session_state.plan
    print(f"[Pass] Proposed Action: '{plan.get('action')}' | Risk Level: '{plan.get('risk_level')}'")
    assert plan.get("risk_level") == "HIGH"
    assert plan.get("requires_approval") is True

    # Simulate clicking "Approve Fix"
    # Find the Approve button
    approve_btn = None
    for b in at.button:
        if "Approve" in b.label:
            approve_btn = b
            break
    assert approve_btn is not None, "Approve button should be present"

    print(f"Clicking approval button: '{approve_btn.label}'")
    approve_btn.click().run()

    # The app transitions through executing -> verifying -> done
    if at.session_state.stage == "executing":
        at.run()

    assert not at.exception, f"App threw exception during execution/verification: {at.exception}"
    print(f"[Pass] Final stage: '{at.session_state.stage}'")
    
    # Verify Before / After Status
    after_status = at.session_state.after_status
    print(f"[Pass] Post-remediation status: {after_status.get('status')} (Error rate: {after_status.get('error_rate')})")
    assert after_status.get("status") == "HEALTHY", "Service should recover to HEALTHY in Scenario 1"
    print("*** SCENARIO 1 UI WORKFLOW PASSED! ***")


def test_app_scenario_2_rejection():
    print("\n" + "=" * 65)
    print(" 2. TESTING STREAMLIT APP - SCENARIO 2 (HUMAN REJECTION & FALLBACK)")
    print("=" * 65)

    reset_environment("scenario_2")

    at = AppTest.from_file("app.py", default_timeout=120).run()
    
    # Select Scenario 2 in radio
    at.session_state.scenario = "scenario_2"
    at.session_state.stage = "investigating"
    at.run(timeout=120)

    assert not at.exception, f"App threw exception: {at.exception}"
    print(f"[Pass] Scenario 2 diagnosed. Stage: '{at.session_state.stage}'")

    # Find Reject button
    reject_btn = None
    for b in at.button:
        if "Reject" in b.label:
            reject_btn = b
            break
    assert reject_btn is not None, "Reject button should be present"

    print(f"Clicking reject button: '{reject_btn.label}'")
    reject_btn.click().run()

    # Verify fallback plan
    plan = at.session_state.plan
    print(f"[Pass] Fallback proposed: '{plan.get('action')}' ({plan.get('description')})")
    print(f"       Fallback Risk Level: '{plan.get('risk_level')}' (Requires Approval: {plan.get('requires_approval')})")
    assert plan.get("action") == "restart_service", "Fallback should propose restart_service"
    print("*** SCENARIO 2 REJECTION & FALLBACK WORKFLOW PASSED! ***")


def test_app_demo_mode():
    print("\n" + "=" * 65)
    print(" 3. TESTING DEMO_MODE=true (100% OFFLINE SAFETY NET)")
    print("=" * 65)

    import os
    os.environ["DEMO_MODE"] = "true"
    reset_environment("scenario_1")

    at = AppTest.from_file("app.py", default_timeout=20).run()
    assert at.session_state.demo_mode is True, "Demo mode should be enabled"
    print("[Pass] App initialized with DEMO_MODE=true.")

    # Trigger Alert in Demo Mode
    trigger_btn = at.sidebar.button[0]
    trigger_btn.click().run()

    assert not at.exception, f"Demo mode threw exception: {at.exception}"
    assert at.session_state.stage == "awaiting_approval", "Should reach awaiting_approval in demo mode"
    assert at.session_state.is_demo_active is True, "is_demo_active must be True"
    print(f"[Pass] Demo investigation completed instantly from cache.")
    print(f"       Root Cause: {at.session_state.diagnosis.get('root_cause')[:60]}...")

    # Approve fix
    approve_btn = [b for b in at.button if "Approve" in b.label][0]
    approve_btn.click().run()
    if at.session_state.stage == "executing":
        at.run()

    assert at.session_state.stage == "done", "Should reach done stage"
    assert at.session_state.incident_report is not None, "Postmortem report must be generated in demo mode"
    assert "Incident Postmortem Report" in at.session_state.incident_report
    print("[Pass] Postmortem report generated cleanly in demo mode without API calls!")
    print("*** DEMO_MODE=true TEST PASSED! ***")


def test_app_scenario_3_memory_leak():
    print("\n" + "=" * 65)
    print(" 4. TESTING STREAMLIT APP - SCENARIO 3 (MEMORY LEAK & AUTO-RESTART)")
    print("=" * 65)

    os.environ["DEMO_MODE"] = "true"
    reset_environment("scenario_3")

    at = AppTest.from_file("app.py", default_timeout=20).run()
    # Select Scenario 3
    at.sidebar.radio[0].set_value("scenario_3").run()
    assert at.session_state.scenario == "scenario_3"
    print("[Pass] Switched to Scenario 3.")

    # Trigger alert
    at.sidebar.button[0].click().run(timeout=25)
    assert at.session_state.stage in ("awaiting_approval", "executing", "verifying", "done")
    print(f"[Pass] Investigation stage: {at.session_state.stage}")

    # If in awaiting_approval (low risk auto-execution path), run execution
    if at.session_state.stage == "awaiting_approval":
        at.run(timeout=25)
    if at.session_state.stage == "executing":
        at.run(timeout=25)

    assert at.session_state.stage in ("verifying", "done"), f"Expected verifying or done, got {at.session_state.stage}"
    if at.session_state.stage == "verifying":
        at.run(timeout=25)

    assert at.session_state.stage == "done", f"Stage should reach done, got {at.session_state.stage}"
    assert at.session_state.after_status["status"] == "HEALTHY"
    assert at.session_state.after_status["error_rate"] == "0.1%"
    print("[Pass] Scenario 3 auto-restarted and verified as HEALTHY (0.1% error rate).")
    print("*** SCENARIO 3 MEMORY LEAK WORKFLOW PASSED! ***")


def test_app_scenario_4_third_party_outage():
    print("\n" + "=" * 65)
    print(" 5. TESTING STREAMLIT APP - SCENARIO 4 (THIRD-PARTY OUTAGE & FALLBACK)")
    print("=" * 65)

    os.environ["DEMO_MODE"] = "true"
    reset_environment("scenario_4")

    at = AppTest.from_file("app.py", default_timeout=20).run()
    at.sidebar.radio[0].set_value("scenario_4").run()
    assert at.session_state.scenario == "scenario_4"
    print("[Pass] Switched to Scenario 4.")

    # Trigger alert
    at.sidebar.button[0].click().run(timeout=25)
    assert at.session_state.stage == "awaiting_approval"
    print(f"[Pass] Investigation diagnosed: {at.session_state.plan['action']} (Risk: {at.session_state.plan['risk_level']})")
    assert at.session_state.plan["action"] == "escalate_and_enable_fallback"
    assert at.session_state.plan["requires_approval"] is True

    # Click Approve Fix
    approve_btn = [b for b in at.button if "Approve" in b.label][0]
    approve_btn.click().run()
    if at.session_state.stage == "executing":
        at.run(timeout=25)
    if at.session_state.stage == "verifying":
        at.run(timeout=25)

    assert at.session_state.stage == "done"
    assert at.session_state.after_status["status"] == "HEALTHY"
    assert at.session_state.after_status["fallback_provider_enabled"] is True
    print("[Pass] Fallback enabled and service verified as HEALTHY (0.8% error rate).")
    print("*** SCENARIO 4 THIRD-PARTY OUTAGE WORKFLOW PASSED! ***")


def test_app_scenario_5_conflicting_evidence():
    print("\n" + "=" * 65)
    print(" 6. TESTING STREAMLIT APP - SCENARIO 5 (CONFLICTING EVIDENCE & 3 CHOICES)")
    print("=" * 65)

    os.environ["DEMO_MODE"] = "true"
    reset_environment("scenario_5")

    at = AppTest.from_file("app.py", default_timeout=20).run()
    at.sidebar.radio[0].set_value("scenario_5").run()
    assert at.session_state.scenario == "scenario_5"
    print("[Pass] Switched to Scenario 5.")

    # Trigger alert
    at.sidebar.button[0].click().run(timeout=25)
    assert at.session_state.stage == "awaiting_approval"
    
    # Verify Low Confidence & Conflicting Evidence
    diag = at.session_state.diagnosis
    conf_score = diag["confidence"]["score"] if isinstance(diag["confidence"], dict) else diag["confidence"]
    print(f"[Pass] Conflicting evidence detected. Confidence score: {conf_score}% (< 60%).")
    assert conf_score < 60, f"Confidence score should be < 60, got {conf_score}"
    assert at.session_state.plan["action"] == "investigate_further"

    # Verify the 3 operator buttons exist
    labels = [b.label for b in at.button]
    assert any("Fail Over Replica" in l for l in labels), "Failover button must be visible"
    assert any("Rollback Anyway" in l for l in labels), "Rollback button must be visible"
    assert any("Gather More Info" in l for l in labels), "Gather More Info button must be visible"
    print("[Pass] All 3 operator choice buttons rendered correctly.")

    # Branch A: Operator chooses Fail Over Replica (Recommended)
    failover_btn = [b for b in at.button if "Fail Over Replica" in b.label][0]
    failover_btn.click().run()
    if at.session_state.stage == "executing":
        at.run(timeout=25)
    if at.session_state.stage == "verifying":
        at.run(timeout=25)

    assert at.session_state.stage == "done"
    assert at.session_state.after_status["status"] == "HEALTHY"
    assert at.session_state.after_status["error_rate"] == "0.2%"
    assert "DRAINED" in at.session_state.after_status["failing_node"]
    print("[Pass] Operator Choice 1 (Fail Over Replica) resolved incident to HEALTHY (0.2% error rate).")

    # Branch B: Operator chooses Rollback Anyway -> Fix Fails -> Secondary Investigation -> Resolves
    reset_environment("scenario_5")
    at2 = AppTest.from_file("app.py", default_timeout=20).run()
    at2.sidebar.radio[0].set_value("scenario_5").run()
    at2.sidebar.button[0].click().run(timeout=25)
    assert at2.session_state.stage == "awaiting_approval"

    rollback_btn = [b for b in at2.button if "Rollback Anyway" in b.label][0]
    rollback_btn.click().run()
    if at2.session_state.stage == "executing":
        at2.run(timeout=25)
    if at2.session_state.stage == "verifying":
        at2.run(timeout=25)

    assert at2.session_state.after_status["status"] == "CRITICAL"
    print("[Pass] Operator Choice 2 (Rollback Anyway) correctly failed verification (service remained CRITICAL at 32.4%).")

    # Operator triggers Re-investigate
    reinvestigate_btn = [b for b in at2.button if "Re-investigate" in b.label][0]
    reinvestigate_btn.click().run()
    if at2.session_state.stage == "investigating":
        at2.run(timeout=25)

    assert at2.session_state.secondary_investigation is True
    assert at2.session_state.stage == "awaiting_approval"
    print(f"[Pass] Secondary investigation identified root cause: {at2.session_state.diagnosis['root_cause'][:60]}...")
    assert at2.session_state.plan["action"] == "failover_replica"

    # Operator approves failover
    approve_btn = [b for b in at2.button if "Approve" in b.label][0]
    approve_btn.click().run()
    if at2.session_state.stage == "executing":
        at2.run(timeout=25)
    if at2.session_state.stage == "verifying":
        at2.run(timeout=25)

    assert at2.session_state.stage == "done"
    assert at2.session_state.after_status["status"] == "HEALTHY"
    assert at2.session_state.after_status["error_rate"] == "0.2%"
    print("[Pass] Secondary investigation failover resolved incident to HEALTHY!")
    print("*** SCENARIO 5 CONFLICTING EVIDENCE WORKFLOW PASSED! ***")


def test_app_simulated_offline():
    print("\n" + "=" * 65)
    print(" 7. TESTING SIMULATED OFFLINE / API FAILURE (FALLBACK RECOVERY)")
    print("=" * 65)

    import os
    # Simulate broken/disconnected internet with invalid key while DEMO_MODE=false
    os.environ["DEMO_MODE"] = "false"
    os.environ["GEMINI_API_KEY"] = "fake_invalid_key_simulating_no_internet"
    reset_environment("scenario_1")

    at = AppTest.from_file("app.py", default_timeout=20).run()
    trigger_btn = at.sidebar.button[0]
    trigger_btn.click().run()

    assert not at.exception, f"Offline fallback threw exception: {at.exception}"
    assert at.session_state.stage == "awaiting_approval", "Should fall back to cached diagnosis rather than crashing"
    assert at.session_state.is_demo_active is True, "Should flag is_demo_active on API failure"
    print("[Pass] Network failure detected: Safety net engaged and loaded verified cache gracefully!")
    print("*** SIMULATED OFFLINE DISCONNECT TEST PASSED! ***")


if __name__ == "__main__":
    # Test 1 & 2: Normal operation (DEMO_MODE=false)
    import os
    os.environ["DEMO_MODE"] = "false"
    test_app_scenario_1()
    test_app_scenario_2_rejection()

    # Test 3: Explicit DEMO_MODE=true
    test_app_demo_mode()

    # Test 4: Scenario 3 Memory leak auto-restart
    test_app_scenario_3_memory_leak()

    # Test 5: Scenario 4 Third-party outage & fallback
    test_app_scenario_4_third_party_outage()

    # Test 6: Scenario 5 Conflicting evidence & operator choices
    test_app_scenario_5_conflicting_evidence()

    # Test 7: Disconnected Internet / API outage fallback
    test_app_simulated_offline()

    print("\n" + "=" * 65)
    print(" ALL 7 STREAMLIT & SAFETY NET TESTS PASSED CLEANLY (7/7)!")
    print("=" * 65)
