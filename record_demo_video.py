"""
Automated Demo Video Recorder for DevOps Copilot.
Uses Playwright to capture a smooth, 60-second live demonstration of:
1. Initial Healthy Dashboard
2. Triggering Alert & Autonomous Investigation
3. Root Cause Analysis & Human Approval Gate
4. Approved Rollback Execution & Closed-Loop Verification
5. Full Incident Postmortem Generation
Saves output as: DevOps_Copilot_Demo_Walkthrough.webm
"""

import os
import shutil
import time
from playwright.sync_api import sync_playwright

def record_demo():
    output_dir = "temp_demo_recordings"
    final_filename = "DevOps_Copilot_Demo_Walkthrough.webm"
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print("[1/6] Launching browser to record demo...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            record_video_dir=output_dir,
            record_video_size={'width': 1366, 'height': 768}
        )
        page = context.new_page()

        print("[2/6] Loading DevOps Copilot Dashboard...")
        page.goto('http://localhost:8501', wait_until='networkidle')
        page.wait_for_timeout(3000)

        # Ensure demo mode toggle is enabled for instant, ultra-smooth demo
        demo_toggle = page.query_selector('text="Offline Demo Mode"')
        if demo_toggle:
            print("Enabling Demo Mode for smooth video pacing...")
            demo_toggle.click()
            page.wait_for_timeout(1500)

        # Step 1: Trigger Alert
        print("[3/6] Triggering Incident Alert...")
        trigger_btn = page.query_selector('button:has-text("Trigger Alert")')
        if trigger_btn:
            trigger_btn.click()
        
        # Wait for investigation to complete
        page.wait_for_timeout(4000)

        # Smooth scroll down to highlight triage feed and approval card
        print("[4/6] Highlighting Autonomous Triage & Approval Gate...")
        page.evaluate("window.scrollBy({top: 320, behavior: 'smooth'})")
        page.wait_for_timeout(2500)

        # Step 2: Click Approve Fix
        approve_btn = page.query_selector('button:has-text("Approve Fix")')
        if approve_btn:
            print("[5/6] Human Operator clicks 'Approve Fix'...")
            approve_btn.click()
        
        # Wait for execution and verification
        page.wait_for_timeout(4000)

        # Scroll down to showcase Postmortem Report
        print("[6/6] Expanding Incident Postmortem Report...")
        expander = page.query_selector('text="Incident Postmortem Report"')
        if expander:
            expander.click()
            page.wait_for_timeout(1500)
            page.evaluate("window.scrollBy({top: 450, behavior: 'smooth'})")
            page.wait_for_timeout(3000)

        # Scroll back up to the healthy dashboard summary
        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        page.wait_for_timeout(2500)

        # Close and finalize video
        context.close()
        browser.close()

    # Move and rename the video
    recorded_files = [f for f in os.listdir(output_dir) if f.endswith('.webm')]
    if recorded_files:
        src = os.path.join(output_dir, recorded_files[0])
        shutil.copy(src, final_filename)
        shutil.rmtree(output_dir)
        print(f"\nDEMO VIDEO SAVED SUCCESSFULLY: {final_filename}")
        print(f"File size: {os.path.getsize(final_filename) / (1024*1024):.2f} MB")
    else:
        print("No video recorded.")

if __name__ == "__main__":
    record_demo()
