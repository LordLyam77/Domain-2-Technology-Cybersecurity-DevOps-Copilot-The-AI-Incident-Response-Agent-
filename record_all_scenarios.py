"""
Automated Demo Video Recorder for ALL 5 SCENARIOS of DevOps Copilot.
Smoothly steps through:
1. Scenario 1: Bad Deploy (Rollback & Verified Recovery)
2. Scenario 2: Fix Fails (Verification Catch & Secondary Triage)
3. Scenario 3: Memory Leak (OOM Detection & Pod Restart)
4. Scenario 4: Vendor Outage (Upstream 504s & Fallback Routing)
5. Scenario 5: Low Confidence (Ambiguous Telemetry & 3 Operator Choices)

Produces: DevOps_Copilot_All_Scenarios_Demo.webm
"""

import os
import shutil
import time
from playwright.sync_api import sync_playwright

def record_all_scenarios():
    output_dir = "temp_all_scenarios_rec"
    final_filename = "DevOps_Copilot_All_Scenarios_Demo.webm"

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print("=========================================================")
    print(" RECORDING COMPREHENSIVE 5-SCENARIO DEMO VIDEO")
    print("=========================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            record_video_dir=output_dir,
            record_video_size={'width': 1366, 'height': 768}
        )
        page = context.new_page()

        print("[Step 1] Loading Dashboard & Initializing...")
        page.goto('http://localhost:8501', wait_until='networkidle')
        page.wait_for_timeout(2500)

        # Ensure Offline Demo Mode is toggled ON for fast, reliable, smooth playback
        demo_toggle = page.query_selector('text="Offline Demo Mode"')
        if demo_toggle:
            demo_toggle.click()
            page.wait_for_timeout(1000)

        # -------------------------------------------------------------
        # SCENARIO 1: Bad Deploy (Rollback)
        # -------------------------------------------------------------
        print("\n--- [SCENARIO 1] Bad Deploy ---")
        options = page.query_selector_all('[data-testid="stSidebar"] [data-testid="stRadioOption"]')
        if len(options) > 0:
            options[0].click()
            page.wait_for_timeout(1200)

        trigger_btn = page.query_selector('button:has-text("Trigger Alert")')
        if trigger_btn:
            trigger_btn.click()
            print("Triggered Scenario 1 Alert...")
        page.wait_for_timeout(3500)

        page.evaluate("window.scrollBy({top: 300, behavior: 'smooth'})")
        page.wait_for_timeout(2000)

        approve_btn = page.query_selector('button:has-text("Approve Fix")')
        if approve_btn:
            print("Approving Rollback...")
            approve_btn.click()
        page.wait_for_timeout(3500)

        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        page.wait_for_timeout(2000)

        # -------------------------------------------------------------
        # SCENARIO 2: Fix Fails (PostgreSQL Pool Saturation)
        # -------------------------------------------------------------
        print("\n--- [SCENARIO 2] Fix Fails & Secondary Investigation ---")
        options = page.query_selector_all('[data-testid="stSidebar"] [data-testid="stRadioOption"]')
        if len(options) > 1:
            options[1].click()
            page.wait_for_timeout(1500)

        trigger_btn = page.query_selector('button:has-text("Trigger Alert")')
        if trigger_btn:
            trigger_btn.click()
            print("Triggered Scenario 2 Alert...")
        page.wait_for_timeout(3500)

        page.evaluate("window.scrollBy({top: 300, behavior: 'smooth'})")
        page.wait_for_timeout(1800)

        # Approve initial rollback
        approve_btn = page.query_selector('button:has-text("Approve Fix")')
        if approve_btn:
            print("Approving initial hypothesis...")
            approve_btn.click()
        page.wait_for_timeout(3500)

        # Verification catch appears: click Re-investigate
        reinvestigate_btn = page.query_selector('button:has-text("Re-investigate")')
        if reinvestigate_btn:
            print("Verification failed as expected! Clicking Re-investigate...")
            reinvestigate_btn.click()
            page.wait_for_timeout(3500)
            page.evaluate("window.scrollBy({top: 250, behavior: 'smooth'})")
            page.wait_for_timeout(2500)

        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        page.wait_for_timeout(1800)

        # -------------------------------------------------------------
        # SCENARIO 3: Memory Leak (OOM Auto-Restart)
        # -------------------------------------------------------------
        print("\n--- [SCENARIO 3] Memory Leak (OOM) ---")
        options = page.query_selector_all('[data-testid="stSidebar"] [data-testid="stRadioOption"]')
        if len(options) > 2:
            options[2].click()
            page.wait_for_timeout(1500)

        trigger_btn = page.query_selector('button:has-text("Trigger Alert")')
        if trigger_btn:
            trigger_btn.click()
            print("Triggered Scenario 3 Alert...")
        page.wait_for_timeout(4000)

        page.evaluate("window.scrollBy({top: 280, behavior: 'smooth'})")
        page.wait_for_timeout(2500)
        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        page.wait_for_timeout(1800)

        # -------------------------------------------------------------
        # SCENARIO 4: Third-Party Vendor Outage (Fallback Routing)
        # -------------------------------------------------------------
        print("\n--- [SCENARIO 4] Vendor Outage (PayGate 504) ---")
        options = page.query_selector_all('[data-testid="stSidebar"] [data-testid="stRadioOption"]')
        if len(options) > 3:
            options[3].click()
            page.wait_for_timeout(1500)

        trigger_btn = page.query_selector('button:has-text("Trigger Alert")')
        if trigger_btn:
            trigger_btn.click()
            print("Triggered Scenario 4 Alert...")
        page.wait_for_timeout(3500)

        page.evaluate("window.scrollBy({top: 300, behavior: 'smooth'})")
        page.wait_for_timeout(2000)

        approve_btn = page.query_selector('button:has-text("Approve Fix")')
        if approve_btn:
            print("Approving Fallback Provider routing...")
            approve_btn.click()
        page.wait_for_timeout(3500)

        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        page.wait_for_timeout(1800)

        # -------------------------------------------------------------
        # SCENARIO 5: Conflicting Evidence (Low Confidence & 3 Choices)
        # -------------------------------------------------------------
        print("\n--- [SCENARIO 5] Conflicting Evidence (Low Confidence) ---")
        options = page.query_selector_all('[data-testid="stSidebar"] [data-testid="stRadioOption"]')
        if len(options) > 4:
            options[4].click()
            page.wait_for_timeout(1500)

        trigger_btn = page.query_selector('button:has-text("Trigger Alert")')
        if trigger_btn:
            trigger_btn.click()
            print("Triggered Scenario 5 Alert...")
        page.wait_for_timeout(3500)

        page.evaluate("window.scrollBy({top: 320, behavior: 'smooth'})")
        page.wait_for_timeout(2200)

        # Operator selects Choice 1: Fail Over Replica
        failover_btn = page.query_selector('button:has-text("Fail Over Replica")')
        if failover_btn:
            print("Operator chooses: Fail Over Replica...")
            failover_btn.click()
        page.wait_for_timeout(3500)

        # Open Postmortem report for final showcase
        print("\nShowcasing Final Postmortem...")
        expander = page.query_selector('text="Incident Postmortem Report"')
        if expander:
            expander.click()
            page.wait_for_timeout(1500)
            page.evaluate("window.scrollBy({top: 400, behavior: 'smooth'})")
            page.wait_for_timeout(3000)

        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        page.wait_for_timeout(2500)

        # Close browser to finalize video
        context.close()
        browser.close()

    # Move video to final destination
    recorded_files = [f for f in os.listdir(output_dir) if f.endswith('.webm')]
    if recorded_files:
        src = os.path.join(output_dir, recorded_files[0])
        shutil.copy(src, final_filename)
        shutil.rmtree(output_dir)
        size_mb = os.path.getsize(final_filename) / (1024 * 1024)
        print("=========================================================")
        print(f" ALL-SCENARIOS DEMO VIDEO CREATED: {final_filename}")
        print(f" File Size: {size_mb:.2f} MB")
        print("=========================================================")
    else:
        print("Error: No recording file found.")

if __name__ == "__main__":
    record_all_scenarios()
