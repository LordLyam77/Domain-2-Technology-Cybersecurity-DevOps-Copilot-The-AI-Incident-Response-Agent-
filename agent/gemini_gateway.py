"""
Gemini Gateway & Demo Safety Net.

WHY THIS FILE EXISTS:
In hackathon presentations and live judging demos, Wi-Fi can drop, API quotas can run out,
or rate-limit spikes (429/503) can happen unexpectedly.
This gateway acts as a bulletproof safety net:
1. Every Gemini API call flows through this single module.
2. If DEMO_MODE=true in .env, it runs 100% locally with NO internet and NO API key required.
3. If an API call fails after retries (e.g. rate limit or network drop), it automatically
   falls back to high-fidelity cached responses from `data/demo_cache/`.
4. It sets an `is_demo_active` flag so the Streamlit UI can transparently display
   a 'Demo mode (Offline Cache)' badge to the user.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DEMO_CACHE_DIR = os.path.join(PROJECT_ROOT, "data", "demo_cache")


def is_demo_mode_env() -> bool:
    """Returns True if DEMO_MODE=true is set in the environment or .env."""
    val = os.getenv("DEMO_MODE", "false").strip().lower()
    return val in ("true", "1", "yes", "on")


def load_demo_cache(scenario: str) -> Dict[str, Any]:
    """Loads pre-recorded scenario data from data/demo_cache/."""
    sc_clean = "scenario_2" if "2" in scenario else "scenario_1"
    cache_file = os.path.join(DEMO_CACHE_DIR, f"{sc_clean}_cache.json")
    
    if not os.path.exists(cache_file):
        raise FileNotFoundError(f"Demo cache file not found at: {cache_file}")
        
    with open(cache_file, "r", encoding="utf-8") as f:
        return json.load(f)


class GeminiGateway:
    """Central gateway for all Gemini model interactions with fallback safety net."""

    def __init__(self, demo_mode: Optional[bool] = None):
        # Allow explicit override from UI toggle, defaulting to .env DEMO_MODE
        if demo_mode is not None:
            self.demo_mode = demo_mode
        else:
            self.demo_mode = is_demo_mode_env()
            
        self.used_fallback = False
        self.last_fallback_reason = ""

    def get_cached_investigation(self, scenario: str, is_secondary: bool = False) -> Dict[str, Any]:
        """Returns pre-recorded investigation steps, diagnosis, and plan from cache."""
        data = load_demo_cache(scenario)
        if is_secondary and "secondary_investigation" in data:
            sec = data["secondary_investigation"]
            return {
                "diagnosis": sec["diagnosis"],
                "plan": sec["plan"],
                "steps": sec["investigation_steps"],
                "is_demo": True
            }
        return {
            "diagnosis": data["diagnosis"],
            "plan": data["plan"],
            "steps": data["investigation_steps"],
            "is_demo": True
        }

    def get_cached_report(self, scenario: str) -> str:
        """Returns pre-recorded incident report markdown from cache."""
        data = load_demo_cache(scenario)
        return data.get("report_markdown", "# Incident Report (Demo Mode)")
