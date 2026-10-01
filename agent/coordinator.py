"""
Incident Investigation Coordinator using Google GenAI SDK.

WHY THIS FILE EXISTS:
This is the core autonomous engine of DevOps Copilot. It coordinates the investigation loop:
1. It registers the 4 diagnostic tools (get_status, get_deploys, get_logs, get_past_incidents)
   with explicit descriptions and parameter schemas.
2. It runs the ReAct (Reasoning + Acting) loop MANUALLY step-by-step:
   - Call Gemini with conversation history.
   - Detect if Gemini called a tool.
   - Execute the tool locally against our simulated environment.
   - Return the tool output to Gemini.
   - Repeat (up to 8 iterations).
   Running manually gives us complete visibility so we can stream each step to the Streamlit UI.
3. Once evidence is gathered, it prompts Gemini for a guaranteed structured JSON diagnosis
   using Gemini's native `response_mime_type="application/json"` mode.
4. It includes retry logic with exponential backoff to handle free-tier rate limits and 503s.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Callable
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

from simulation.environment import (
    get_environment,
    SimulatedEnvironment
)
from .prompts import INVESTIGATION_SYSTEM_PROMPT, FINAL_SYNTHESIS_PROMPT
from .planner import RemediationPlanner, RemediationPlan
from .gemini_gateway import GeminiGateway, is_demo_mode_env


class IncidentCoordinator:
    """Coordinates the autonomous AI incident response investigation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        env: Optional[SimulatedEnvironment] = None,
        demo_mode: Optional[bool] = None
    ):
        self.gateway = GeminiGateway(demo_mode=demo_mode)
        self.demo_mode = self.gateway.demo_mode
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        # Primary model and fallbacks if one encounters capacity limits or rate limits
        self.primary_model = model_name or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.fallback_models = [
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.8-flash",
            "gemini-3.5-flash"
        ]
        
        # Only initialize client if not in explicit offline demo mode or if key exists
        self.client = None
        if self.api_key and not self.demo_mode:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Coordinator] Client init warning: {e}. Demo fallback ready.", flush=True)

        self.env = env or get_environment()
        self.planner = RemediationPlanner()

        # Build tool definitions for Gemini function calling
        self.tools = self._build_tool_declarations()
        
        # Tool dispatch map
        self.tool_handlers: Dict[str, Callable] = {
            "get_status": self.env.get_status,
            "get_deploys": self.env.get_deploys,
            "get_logs": self.env.get_logs,
            "get_past_incidents": self.env.get_past_incidents,
        }

    def _build_tool_declarations(self) -> Optional[Any]:
        """Declares the 4 diagnostic tools with schema descriptions."""
        if not GENAI_AVAILABLE or types is None:
            return None

        get_status_decl = types.FunctionDeclaration(
            name="get_status",
            description="Fetches the live health metrics, status (HEALTHY, CRITICAL, DEGRADED), error rate, active connections, and version of a service.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "service_name": types.Schema(
                        type="STRING",
                        description="Optional name of the service to check (e.g. 'payment-service'). Defaults to active service."
                    )
                }
            )
        )

        get_deploys_decl = types.FunctionDeclaration(
            name="get_deploys",
            description="Inspects recent deployment records including version tag, commit author, commit message, and deployment timestamp.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "service_name": types.Schema(
                        type="STRING",
                        description="Optional service name to filter deploys."
                    ),
                    "limit": types.Schema(
                        type="INTEGER",
                        description="Max number of recent deploys to retrieve (default: 5)."
                    )
                }
            )
        )

        get_logs_decl = types.FunctionDeclaration(
            name="get_logs",
            description="Retrieves application log lines with optional filtering by log level (ERROR, WARN, INFO, FATAL) and service.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "service_name": types.Schema(
                        type="STRING",
                        description="Optional service name to filter logs."
                    ),
                    "limit": types.Schema(
                        type="INTEGER",
                        description="Number of most recent log lines to fetch (default: 50)."
                    ),
                    "level": types.Schema(
                        type="STRING",
                        description="Optional log level filter, such as 'ERROR' or 'WARN'."
                    )
                }
            )
        )

        get_past_incidents_decl = types.FunctionDeclaration(
            name="get_past_incidents",
            description="Searches historical postmortem incident reports by keyword (e.g. 'pool', 'timeout', 'postgres', 'rollback') to see how previous outages were resolved.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "query": types.Schema(
                        type="STRING",
                        description="Search keyword to find relevant past postmortems."
                    ),
                    "limit": types.Schema(
                        type="INTEGER",
                        description="Max number of past incidents to return (default: 5)."
                    )
                }
            )
        )

        return types.Tool(
            function_declarations=[
                get_status_decl,
                get_deploys_decl,
                get_logs_decl,
                get_past_incidents_decl
            ]
        )

    def _call_gemini_with_retry(
        self,
        contents: Any,
        config: types.GenerateContentConfig,
        retries: int = 2,
        base_delay: float = 2.0
    ) -> Any:
        """
        Executes a Gemini generate_content call with retries and exponential backoff.
        
        WHY:
        Free-tier Gemini API keys can experience momentary 429 (rate limit)
        or 503 (high demand) errors. Retrying with a brief pause makes the
        agent resilient without crashing the user session.
        """
        candidate_models = [self.primary_model] + [
            m for m in self.fallback_models if m != self.primary_model
        ]

        last_error = None
        for model in candidate_models:
            for attempt in range(retries + 1):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=config
                    )
                    return response
                except Exception as e:
                    last_error = e
                    err_msg = str(e)
                    is_transient = (
                        "503" in err_msg
                        or "429" in err_msg
                        or "UNAVAILABLE" in err_msg
                        or "RESOURCE_EXHAUSTED" in err_msg
                    )
                    if is_transient and attempt < retries:
                        # On 429 / RESOURCE_EXHAUSTED, switch immediately to the next fallback model
                        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                            print(
                                f"[{model}] Model quota reached (429). Instantly switching to next fallback model...",
                                flush=True
                            )
                            break  # Move to next model in candidate_models immediately
                        else:
                            sleep_time = base_delay * (2 ** attempt)
                            print(
                                f"[{model}] Temporary 503 busy ({err_msg[:50]}...). Retrying in {sleep_time:.1f}s...",
                                flush=True
                            )
                            time.sleep(sleep_time)
                    else:
                        break  # Try next model if retries exhausted

        raise RuntimeError(
            f"Failed to communicate with Gemini API after retries across models: {last_error}"
        )

    def investigate(
        self,
        alert_description: str = "Payment-service is reporting elevated 500 error rates and failing transactions.",
        on_step_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        previous_attempt_info: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs the full autonomous incident investigation loop.
        
        Parameters:
        - alert_description: Description of the incoming alert.
        - on_step_callback: Optional hook called whenever a tool is invoked or result received.
                            Used by the Streamlit UI to display live step-by-step progress.
        - previous_attempt_info: Details of an earlier remediation attempt that failed (used in Scenario 2).
        
        Returns:
        - Dict with 'diagnosis', 'plan', 'steps', and 'execution_summary'.
        """
        steps: List[Dict[str, Any]] = []

        def log_step(step_type: str, data: Dict[str, Any]):
            entry = {
                "step_number": len(steps) + 1,
                "type": step_type,
                "timestamp": time.strftime("%H:%M:%S"),
                **data
            }
            steps.append(entry)
            if on_step_callback:
                on_step_callback(entry)

        # Initial user instruction to begin the investigation
        user_prompt = (
            f"ALERT TRIGGERED:\n{alert_description}\n\n"
            "Investigate this incident using your available tools. Find the true root cause, "
            "verify evidence, check recent deployments, inspect logs, and consult past incidents. "
            "Proceed step-by-step."
        )

        if previous_attempt_info:
            user_prompt += (
                f"\n\nIMPORTANT - PREVIOUS REMEDIATION FAILED:\n"
                f"{previous_attempt_info}\n"
                "The previous hypothesis was already tested and did NOT resolve the outage. "
                "Drop that previous assumption. Investigate the deeper root cause."
            )

        log_step("INVESTIGATION_STARTED", {
            "alert": alert_description,
            "message": "DevOps Copilot agent initiated incident triage loop."
        })

        # ---------------------------------------------------------------------
        # 0. DEMO MODE OR NO CLIENT: PLAYBACK VERIFIED CACHE
        # ---------------------------------------------------------------------
        scenario_id = getattr(self.env, "scenario_id", "scenario_1")
        if self.demo_mode or self.client is None or not GENAI_AVAILABLE or types is None:
            print(f"[Coordinator] Executing via Demo Safety Net (scenario: {scenario_id}).", flush=True)
            cached_res = self.gateway.get_cached_investigation(
                scenario=scenario_id,
                is_secondary=bool(previous_attempt_info)
            )
            for step in cached_res.get("steps", []):
                time.sleep(0.1)  # Brief pause for realistic animation
                if on_step_callback:
                    on_step_callback(step)
            
            remediation_plan = self.planner.build_plan_from_diagnosis(cached_res["diagnosis"])
            return {
                "diagnosis": cached_res["diagnosis"],
                "plan": remediation_plan.to_dict(),
                "remediation_plan_obj": remediation_plan,
                "steps": cached_res.get("steps", []),
                "iterations_used": len(cached_res.get("steps", [])),
                "is_demo": True
            }

        # Initialize conversation contents with system prompt and alert
        tool_config = types.GenerateContentConfig(
            system_instruction=INVESTIGATION_SYSTEM_PROMPT,
            tools=[self.tools],
            temperature=0.1
        )

        contents: List[types.Content] = [
            types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
        ]

        try:
            # -----------------------------------------------------------------
            # STEP 1: Manual Multi-Turn Tool Execution Loop (Max 8 Iterations)
            # -----------------------------------------------------------------
            max_iterations = 8
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                response = self._call_gemini_with_retry(
                    contents=contents,
                    config=tool_config
                )

                # Check if Gemini wants to call any tool
                function_calls = response.function_calls

                if not function_calls:
                    log_step("INVESTIGATION_CONCLUDED", {
                        "iteration": iteration,
                        "message": "Agent finished gathering evidence. Moving to diagnosis synthesis."
                    })
                    break

                # Add the model's response candidate to the conversation history
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)

                # Execute each requested function call locally and gather parts
                tool_parts = []
                for fc in function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}

                    log_step("TOOL_CALL", {
                        "iteration": iteration,
                        "tool": tool_name,
                        "arguments": tool_args,
                        "message": f"Invoking tool `{tool_name}` with parameters: {tool_args}"
                    })

                    # Execute the simulated function
                    if tool_name in self.tool_handlers:
                        try:
                            tool_result = self.tool_handlers[tool_name](**tool_args)
                        except Exception as ex:
                            tool_result = {"error": f"Tool execution failed: {str(ex)}"}
                    else:
                        tool_result = {"error": f"Unknown tool: {tool_name}"}

                    # Build human-readable summary for live UI feed
                    if tool_name == "get_logs":
                        if isinstance(tool_result, list):
                            sample_err = ""
                            for log_entry in reversed(tool_result):
                                if log_entry.get("level") in ("ERROR", "FATAL"):
                                    sample_err = f" ({log_entry.get('message', '')[:50]}...)"
                                    break
                            summary_txt = f"Found {len(tool_result)} log entries{sample_err}"
                        else:
                            summary_txt = "Fetched logs"
                    elif tool_name == "get_status":
                        st = tool_result.get("status", "UNKNOWN")
                        er = tool_result.get("error_rate", "0%")
                        ver = tool_result.get("current_version", "")
                        summary_txt = f"Status: {st} | Error rate: {er} | Version: {ver}"
                    elif tool_name == "get_deploys":
                        if isinstance(tool_result, list) and len(tool_result) > 0:
                            latest = tool_result[0]
                            summary_txt = f"Found {len(tool_result)} recent deployments (latest: {latest.get('version')} - '{latest.get('commit_msg', '')[:45]}...')"
                        else:
                            summary_txt = f"Found {len(tool_result)} deployments"
                    elif tool_name == "get_past_incidents":
                        if isinstance(tool_result, list):
                            ids = [inc.get("id") for inc in tool_result if "id" in inc]
                            summary_txt = f"Found {len(tool_result)} past incident(s) {', '.join(ids) if ids else ''}"
                        else:
                            summary_txt = "Queried past incidents"
                    else:
                        summary_txt = f"Received {len(tool_result) if isinstance(tool_result, list) else 1} items"

                    log_step("TOOL_RESULT", {
                        "iteration": iteration,
                        "tool": tool_name,
                        "result_summary": summary_txt,
                        "result": tool_result
                    })

                    tool_parts.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={"result": tool_result}
                        )
                    )

                # Append single tool turn containing all responses
                contents.append(
                    types.Content(
                        role="tool",
                        parts=tool_parts
                    )
                )

            # -----------------------------------------------------------------
            # STEP 2: Guaranteed Structured JSON Synthesis (With 1-Retry on Malformed JSON)
            # -----------------------------------------------------------------
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=FINAL_SYNTHESIS_PROMPT)]
                )
            )

            synthesis_config = types.GenerateContentConfig(
                system_instruction=INVESTIGATION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1
            )

            diagnosis_data = None
            for json_attempt in range(2):
                synthesis_response = self._call_gemini_with_retry(
                    contents=contents,
                    config=synthesis_config
                )
                raw_json = synthesis_response.text or "{}"
                try:
                    clean_text = raw_json.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text[7:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]
                    diagnosis_data = json.loads(clean_text)
                    break
                except json.JSONDecodeError as jde:
                    print(f"[Coordinator] JSON parse attempt {json_attempt+1} failed: {jde}. Retrying JSON generation...", flush=True)
                    contents.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text="Your previous output was malformed. Please return ONLY a valid, parsable JSON object.")]
                        )
                    )

            if not diagnosis_data:
                # If still malformed after retry, use clean cache for this scenario
                print("[Coordinator] JSON generation unrecoverable. Loading cached diagnosis.", flush=True)
                cached = self.gateway.get_cached_investigation(scenario_id, is_secondary=bool(previous_attempt_info))
                diagnosis_data = cached["diagnosis"]

            # -----------------------------------------------------------------
            # STEP 3: Build Remediation Plan using Planner
            # -----------------------------------------------------------------
            remediation_plan = self.planner.build_plan_from_diagnosis(diagnosis_data)

            log_step("DIAGNOSIS_COMPLETE", {
                "root_cause": diagnosis_data.get("root_cause"),
                "confidence": diagnosis_data.get("confidence"),
                "recommended_action": diagnosis_data.get("recommended_action"),
                "risk_level": remediation_plan.risk_level,
                "requires_approval": remediation_plan.requires_approval
            })

            return {
                "diagnosis": diagnosis_data,
                "plan": remediation_plan.to_dict(),
                "remediation_plan_obj": remediation_plan,
                "steps": steps,
                "iterations_used": iteration,
                "is_demo": False
            }

        except Exception as e:
            # SAFETY NET: Gracefully fall back to demo cache instead of crashing
            print(f"[Coordinator] Investigation API failed ({e}). Engaging Demo Safety Net.", flush=True)
            cached_res = self.gateway.get_cached_investigation(
                scenario=scenario_id,
                is_secondary=bool(previous_attempt_info)
            )
            for step in cached_res.get("steps", []):
                if on_step_callback:
                    on_step_callback(step)
            
            remediation_plan = self.planner.build_plan_from_diagnosis(cached_res["diagnosis"])
            return {
                "diagnosis": cached_res["diagnosis"],
                "plan": remediation_plan.to_dict(),
                "remediation_plan_obj": remediation_plan,
                "steps": cached_res.get("steps", []),
                "iterations_used": len(cached_res.get("steps", [])),
                "is_demo": True
            }
