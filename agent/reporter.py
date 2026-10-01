"""
Incident Postmortem Report Generator.

WHY THIS FILE EXISTS:
After an outage is mitigated, SRE teams write an Incident Postmortem Report
to document what happened, why it happened, the remediation steps taken,
and action items to prevent recurrence.
This module uses Gemini to generate a professional, standardized Markdown postmortem
strictly grounded in the telemetry and action history gathered during the incident.
"""

import os
import json
import time
from typing import Dict, Any, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False

from .gemini_gateway import GeminiGateway, is_demo_mode_env


REPORT_SYSTEM_PROMPT = """You are a Principal Site Reliability Engineer (SRE).
Your task is to write a concise, professional Incident Postmortem Report in GitHub Flavored Markdown based strictly on the provided incident record.

STRICT INSTRUCTIONS:
1. ONLY use verifiable facts provided in the incident record. DO NOT hallucinate or invent timestamps, metrics, authors, commit messages, or events.
2. Structure the report with these exact section headers:
   # Incident Postmortem Report: [Incident ID / Service Name]
   ## 1. Summary
   ## 2. Timeline
   ## 3. Root Cause Analysis
   ## 4. Key Evidence
   ## 5. Action Taken & Approval Audit
   ## 6. Verification & Result
   ## 7. Failed Remediation Analysis & Learnings (Include ONLY if a remediation attempt failed, e.g., in Scenario 2)
   ## 8. Follow-up Recommendations
3. In the Timeline section, list bullet points with exact timestamps and descriptions.
4. In Action Taken & Approval Audit, explicitly state what action was executed and WHO approved it (e.g., 'Approved by Human Operator').
5. Keep the tone factual, blameless, and precise.
"""


def generate_incident_report(
    incident_record: Dict[str, Any],
    demo_mode: Optional[bool] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a structured Markdown incident postmortem report.
    
    Parameters:
    - incident_record: Comprehensive dictionary containing alert, root cause, evidence,
                       timeline steps, actions, approval status, before/after metrics.
    - demo_mode: If True, returns pre-cached high-fidelity postmortem without API calls.
    
    Returns:
    - Dict with 'report_markdown' (str), 'is_demo' (bool), and 'model' (str).
    """
    scenario = incident_record.get("scenario", "scenario_1")
    gateway = GeminiGateway(demo_mode=demo_mode)

    # 1. DEMO MODE SAFETY NET: If demo mode is active or SDK unavailable, return cached report immediately
    if gateway.demo_mode or not GENAI_AVAILABLE or genai is None:
        print("[Reporter] DEMO_MODE active or SDK unavailable. Returning verified cached incident report.", flush=True)
        return {
            "report_markdown": gateway.get_cached_report(scenario),
            "is_demo": True,
            "model": "cached-demo-safety-net"
        }

    # 2. LIVE GEMINI GENERATION
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        print("[Reporter] No API key detected. Falling back to cached report.", flush=True)
        return {
            "report_markdown": gateway.get_cached_report(scenario),
            "is_demo": True,
            "model": "cached-demo-fallback"
        }

    primary_model = model_name or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    candidate_models = [
        primary_model,
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.8-flash"
    ]

    client = genai.Client(api_key=key)

    # Build prompt payload containing all facts
    prompt_payload = (
        "Generate an incident postmortem report using ONLY the following facts:\n\n"
        f"INCIDENT RECORD:\n{json.dumps(incident_record, indent=2)}\n\n"
        "Generate the complete Markdown report now."
    )

    config = types.GenerateContentConfig(
        system_instruction=REPORT_SYSTEM_PROMPT,
        temperature=0.1
    )

    # Retry loop across candidate models
    for model in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt_payload,
                    config=config
                )
                if response.text:
                    return {
                        "report_markdown": response.text.strip(),
                        "is_demo": False,
                        "model": model
                    }
            except Exception as e:
                err_msg = str(e)
                print(f"[Reporter] Model {model} attempt {attempt+1} failed: {err_msg[:60]}", flush=True)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    break  # Switch to next model immediately on quota
                time.sleep(1.5)

    # 3. AUTOMATIC FALLBACK: If all API attempts fail, return cache rather than crashing
    print("[Reporter] All API attempts failed. Falling back to verified cached report.", flush=True)
    return {
        "report_markdown": gateway.get_cached_report(scenario),
        "is_demo": True,
        "model": "cached-demo-fallback"
    }
