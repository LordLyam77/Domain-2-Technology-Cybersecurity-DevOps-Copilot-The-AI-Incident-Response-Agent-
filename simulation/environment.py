"""
Simulated DevOps Infrastructure Environment for Incident Response.

WHY THIS MODULE EXISTS:
In production incident response, Site Reliability Engineers (SREs) query diagnostic
tools (Datadog, Prometheus, ArgoCD, Jira, Elasticsearch) to inspect logs, health metrics,
deployment histories, and past incident postmortems.
For this hackathon project, this simulation layer models a realistic distributed
infrastructure sandbox completely locally using stateful data structures and JSON traces.

It allows the autonomous AI agent to:
1. Query vital signs (service status, error rates, latencies, resource metrics, dependency health)
2. Stream structured application and infrastructure logs
3. Inspect version histories and commit diffs
4. Search historical incident postmortems
5. Execute realistic remediation actions (rollback, restart, fallback cutover, replica failover)
6. Enforce realistic consequences: state changes realistically, and actions intentionally FAIL
   when they do not target the true underlying root cause (e.g. rollback failing on DB saturation or vendor outages)
7. Perform rigorous, multi-point verification comparing pre-remediation and post-remediation telemetry.
"""

import json
import os
import copy
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

# Set up dedicated backend logger
logger = logging.getLogger("devops_copilot.simulation")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] [Simulation] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# Locate data directory relative to this file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data")


class SimulatedEnvironment:
    """
    Represents the simulated distributed infrastructure.
    Holds mutable state in memory so actions like 'rollback' or 'restart'
    immediately change system health, version, error rate, dependency state, and logs.
    """

    def __init__(self, scenario: str = "scenario_1"):
        self.scenario_id = scenario
        self.service_name = "payment-service"
        self.title = ""
        self.description = ""
        self.lifecycle_state = "INCIDENT"  # HEALTHY -> INCIDENT -> INVESTIGATING -> REMEDIATING -> VERIFIED
        self.state: Dict[str, Any] = {}
        self.healthy_baseline: Dict[str, Any] = {}
        self.incident_snapshot: Dict[str, Any] = {}
        self.logs: List[Dict[str, Any]] = []
        self.deploys: List[Dict[str, Any]] = []
        self.past_incidents: List[Dict[str, Any]] = []
        self.action_history: List[Dict[str, Any]] = []
        
        # Load the selected scenario data and historical incidents
        self.reset_environment(scenario)

    def _get_timestamp(self) -> str:
        """Returns current simulated ISO timestamp for log injection."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _parse_error_rate_float(self, rate_str: Any) -> float:
        """Helper to parse error rate string (e.g. '43.5%') into a float (0.435)."""
        if isinstance(rate_str, (int, float)):
            return float(rate_str)
        if isinstance(rate_str, str):
            clean = rate_str.replace("%", "").strip()
            try:
                return float(clean) / 100.0
            except ValueError:
                return 0.0
        return 0.0

    def reset_environment(self, scenario: str = "scenario_1", start_in_incident: bool = True) -> Dict[str, Any]:
        """
        Resets the environment back to a clean scenario baseline.
        
        WHY:
        Allows users, tests, and demo presenters to replay scenarios from scratch cleanly
        and deterministically without leaving orphaned state.
        
        Supports all 5 hackathon scenarios:
        - scenario_1: Bad Deploy / Pool Misconfiguration (Rollback fixes)
        - scenario_2: Fix Fails / PostgreSQL Connection Saturation (Rollback fails, secondary DB restart fixes)
        - scenario_3: Memory Leak / OOM (Stateless restart flushes heap and recovers)
        - scenario_4: Upstream Third-Party Vendor Outage (Rollback fails, fallback cutover recovers)
        - scenario_5: Conflicting Evidence / Replica Lag (Rollback fails, failover replica recovers)
        """
        scenario_map = {
            "scenario_1": "scenario_1_bad_deploy.json",
            "scenario_1_bad_deploy": "scenario_1_bad_deploy.json",
            "scenario_2": "scenario_2_fix_fails.json",
            "scenario_2_fix_fails": "scenario_2_fix_fails.json",
            "scenario_3": "scenario_3_memory_leak.json",
            "scenario_3_memory_leak": "scenario_3_memory_leak.json",
            "scenario_4": "scenario_4_third_party_outage.json",
            "scenario_4_third_party_outage": "scenario_4_third_party_outage.json",
            "scenario_5": "scenario_5_conflicting_evidence.json",
            "scenario_5_conflicting_evidence": "scenario_5_conflicting_evidence.json",
        }

        filename = scenario_map.get(str(scenario).strip().lower(), "scenario_1_bad_deploy.json")
        filepath = os.path.join(DATA_DIR, filename)

        if not os.path.exists(filepath):
            logger.warning(f"Scenario file not found: {filepath}. Falling back to scenario_1.")
            filepath = os.path.join(DATA_DIR, "scenario_1_bad_deploy.json")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading scenario file {filepath}: {e}")
            data = {"scenario_id": "scenario_1_bad_deploy", "initial_state": {}}

        # Deep-copy everything so mutations during investigations do not alter raw JSON files
        self.scenario_id = data.get("scenario_id", scenario)
        self.title = data.get("title", "")
        self.description = data.get("description", "")
        self.service_name = data.get("service_name", "payment-service")
        
        # Load incident initial state
        raw_initial = data.get("initial_state", {})
        self.incident_snapshot = copy.deepcopy(raw_initial)
        
        # Synthesize a realistic healthy baseline for pre-incident comparison
        self.healthy_baseline = self._create_healthy_baseline(self.scenario_id, raw_initial)
        
        if start_in_incident:
            self.state = copy.deepcopy(self.incident_snapshot)
            self.lifecycle_state = "INCIDENT"
        else:
            self.state = copy.deepcopy(self.healthy_baseline)
            self.lifecycle_state = "HEALTHY"

        self.logs = copy.deepcopy(data.get("logs", []))
        self.deploys = copy.deepcopy(data.get("deploys", []))
        self.action_history = []

        # Load past incidents knowledge base
        past_incidents_path = os.path.join(DATA_DIR, "past_incidents.json")
        if os.path.exists(past_incidents_path):
            try:
                with open(past_incidents_path, "r", encoding="utf-8") as f:
                    self.past_incidents = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load past_incidents.json: {e}")
                self.past_incidents = []
        else:
            self.past_incidents = []

        logger.info(f"Environment reset successfully: scenario='{self.scenario_id}', service='{self.service_name}', state='{self.lifecycle_state}'")

        return {
            "status": "success",
            "message": f"Environment reset to {self.scenario_id}.",
            "service": self.service_name,
            "scenario": self.scenario_id,
            "lifecycle_state": self.lifecycle_state,
            "current_state": copy.deepcopy(self.state)
        }

    def _create_healthy_baseline(self, scenario_id: str, raw_initial: Dict[str, Any]) -> Dict[str, Any]:
        """Constructs the healthy baseline state corresponding to a scenario before outage onset."""
        base = {
            "status": "HEALTHY",
            "current_version": raw_initial.get("previous_version") or raw_initial.get("healthy_version") or "v2.3.9",
            "previous_version": "v2.3.8",
            "healthy_version": raw_initial.get("healthy_version") or "v2.3.9",
            "error_rate": "0.1%",
            "avg_latency_ms": 16,
            "active_db_connections": 8,
            "max_db_connections": 50,
            "db_status": "ONLINE",
            "uptime_seconds": 3600,
            "last_action": "none",
            "timestamp": self._get_timestamp()
        }
        if "scenario_3" in scenario_id:
            base["memory_usage_mb"] = 240
            base["max_memory_mb"] = 2048
            base["memory_pct"] = "11.7%"
        elif "scenario_4" in scenario_id:
            base["external_gateway"] = "PayGate Global (api.paygate-global.com)"
            base["external_gateway_status"] = "HEALTHY (HTTP 200, latency 42ms)"
            base["fallback_provider_enabled"] = False
            base["cpu_usage"] = "12.0%"
            base["db_health"] = "HEALTHY (latency 3.1ms, pool 8/50)"
        elif "scenario_5" in scenario_id:
            base["failing_node"] = "NONE"
            base["db_health"] = "HEALTHY (All replicas in sync)"
            base["replica_nodes"] = {
                "db-replica-01": {"status": "HEALTHY", "lag_seconds": 0.3, "qps": 125},
                "db-replica-02": {"status": "HEALTHY", "lag_seconds": 0.4, "qps": 120}
            }
        return base

    def trigger_incident(self) -> Dict[str, Any]:
        """
        Explicitly triggers the incident state for the active scenario.
        Moves lifecycle from HEALTHY -> INCIDENT with telemetry spike.
        """
        self.state = copy.deepcopy(self.incident_snapshot)
        self.lifecycle_state = "INCIDENT"
        ts = self._get_timestamp()
        
        alert_log = {
            "timestamp": ts,
            "level": "FATAL",
            "service": self.service_name,
            "message": f"ALARM_TRIGGERED: HTTP 5xx error rate spiked to {self.state.get('error_rate', 'unknown')} (threshold > 5.0%)."
        }
        self.logs.append(alert_log)
        logger.warning(f"Incident triggered for {self.service_name} in {self.scenario_id}: Error rate = {self.state.get('error_rate')}")
        
        return {
            "status": "triggered",
            "scenario": self.scenario_id,
            "service": self.service_name,
            "lifecycle_state": self.lifecycle_state,
            "incident_state": copy.deepcopy(self.state)
        }

    def get_healthy_state(self) -> Dict[str, Any]:
        """Returns the healthy baseline state for reference or before-and-after comparison."""
        return copy.deepcopy(self.healthy_baseline)

    def get_logs(
        self,
        service_name: Optional[str] = None,
        limit: Optional[int] = 50,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Simulates structured log aggregation endpoints (Elasticsearch / Datadog Logs).
        Supports filtering by service and log level (INFO, WARN, ERROR, FATAL).
        Safely handles boundary limits and missing keys.
        """
        filtered = self.logs

        # Filter by service if specified
        if service_name and isinstance(service_name, str):
            tgt = service_name.strip().lower()
            filtered = [
                log for log in filtered
                if log.get("service", "").lower() == tgt
            ]

        # Filter by log level
        if level and isinstance(level, str):
            lvl = level.strip().upper()
            filtered = [
                log for log in filtered
                if log.get("level", "").upper() == lvl
            ]

        # Safe limit slicing
        if limit is not None:
            try:
                lim = max(0, int(limit))
                if lim > 0:
                    return filtered[-lim:]
                return []
            except (ValueError, TypeError):
                pass
                
        return filtered

    def get_status(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulates Prometheus / Kubernetes service health and telemetry vital signs.
        Guarantees complete, strongly typed fields for downstream AI and UI consumption.
        """
        target_service = service_name or self.service_name
        
        res: Dict[str, Any] = {
            "service": target_service,
            "scenario": self.scenario_id,
            "status": self.state.get("status", "UNKNOWN"),
            "lifecycle_state": self.lifecycle_state,
            "current_version": self.state.get("current_version", "unknown"),
            "previous_version": self.state.get("previous_version", "unknown"),
            "error_rate": self.state.get("error_rate", "0%"),
            "avg_latency_ms": self.state.get("avg_latency_ms", 0),
            "db_status": self.state.get("db_status", "UNKNOWN"),
            "active_db_connections": self.state.get("active_db_connections", 0),
            "max_db_connections": self.state.get("max_db_connections", 0),
            "uptime_seconds": self.state.get("uptime_seconds", 0),
            "last_action": self.state.get("last_action", "none"),
            "timestamp": self._get_timestamp()
        }

        # Scenario 3: Memory & JVM telemetry
        if "memory_usage_mb" in self.state:
            res["memory_usage_mb"] = self.state.get("memory_usage_mb")
            res["max_memory_mb"] = self.state.get("max_memory_mb")
            res["memory_pct"] = self.state.get("memory_pct")

        # Scenario 4: External vendor and gateway telemetry
        if "external_gateway" in self.state:
            res["external_gateway"] = self.state.get("external_gateway")
            res["external_gateway_status"] = self.state.get("external_gateway_status")
            res["fallback_provider_enabled"] = self.state.get("fallback_provider_enabled")
            res["cpu_usage"] = self.state.get("cpu_usage")
            res["db_health"] = self.state.get("db_health")

        # Scenario 5: Database replica nodes and WAL lag telemetry
        if "failing_node" in self.state:
            res["failing_node"] = self.state.get("failing_node")
            res["db_health"] = self.state.get("db_health")
            res["replica_nodes"] = self.state.get("replica_nodes")

        return res

    def get_deploys(
        self,
        service_name: Optional[str] = None,
        limit: Optional[int] = 5
    ) -> List[Dict[str, Any]]:
        """
        Simulates deployment tracking systems (ArgoCD, GitHub Deployments).
        Returns deployments sorted newest-first up to the requested limit.
        """
        deploys = self.deploys
        if service_name and isinstance(service_name, str):
            tgt = service_name.strip().lower()
            deploys = [
                d for d in deploys
                if d.get("service", "").lower() == tgt
            ]

        def _sort_key(d: Dict[str, Any]) -> str:
            return str(d.get("timestamp", ""))

        sorted_deploys = sorted(deploys, key=_sort_key, reverse=True)
        
        if limit is not None:
            try:
                lim = max(0, int(limit))
                return sorted_deploys[:lim]
            except (ValueError, TypeError):
                pass
                
        return sorted_deploys

    def get_past_incidents(
        self,
        limit: Optional[int] = 5,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Simulates knowledge base postmortem repository (Jira / Confluence incident postmortems).
        Allows full-text search across incident ID, title, symptoms, root cause, and tags.
        """
        results = self.past_incidents

        if query and isinstance(query, str) and query.strip():
            q = query.strip().lower()
            results = [
                inc for inc in results
                if q in inc.get("id", "").lower()
                or q in inc.get("title", "").lower()
                or q in inc.get("symptoms", "").lower()
                or q in inc.get("root_cause", "").lower()
                or q in inc.get("resolution", "").lower()
                or any(q in str(tag).lower() for tag in inc.get("tags", []))
            ]

        if limit is not None:
            try:
                lim = max(0, int(limit))
                return results[:lim]
            except (ValueError, TypeError):
                pass

        return results

    def get_metrics_timeline(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generates timeseries data points of error rate over time from logs and state.
        Reflects outage progression, deployment annotations, and post-remediation recovery.
        """
        if "scenario_3" in self.scenario_id:
            timeline = [
                {"time": "10:00", "error_rate": 0.05, "status": "HEALTHY", "event": "Normal baseline (heap 54%)"},
                {"time": "11:00", "error_rate": 0.10, "status": "HEALTHY", "event": ""},
                {"time": "12:00", "error_rate": 0.15, "status": "HEALTHY", "event": "Latency rising (45ms)"},
                {"time": "13:00", "error_rate": 0.80, "status": "DEGRADED", "event": "Heap at 82%"},
                {"time": "13:30", "error_rate": 2.40, "status": "DEGRADED", "event": "Full GC cycles (920ms)"},
                {"time": "14:00", "error_rate": 18.5, "status": "CRITICAL", "event": "First OutOfMemoryError"},
                {"time": "14:05", "error_rate": 31.0, "status": "CRITICAL", "event": "Heap at 96%"},
                {"time": "14:15", "error_rate": 38.6, "status": "CRITICAL", "event": "Alert Triggered (38.6%)"},
            ]
        elif "scenario_4" in self.scenario_id:
            timeline = [
                {"time": "14:00", "error_rate": 0.05, "status": "HEALTHY", "event": "Normal traffic"},
                {"time": "14:03", "error_rate": 0.08, "status": "HEALTHY", "event": ""},
                {"time": "14:06", "error_rate": 0.10, "status": "HEALTHY", "event": "v2.4.1 deployed (UI text)"},
                {"time": "14:09", "error_rate": 0.12, "status": "HEALTHY", "event": "Checkout normal"},
                {"time": "14:12", "error_rate": 1.80, "status": "DEGRADED", "event": "PayGate latency >2500ms"},
                {"time": "14:13", "error_rate": 12.5, "status": "DEGRADED", "event": "First 504 Timeout"},
                {"time": "14:15", "error_rate": 34.0, "status": "CRITICAL", "event": "CircuitBreaker OPEN"},
                {"time": "14:18", "error_rate": 41.8, "status": "CRITICAL", "event": "Alert Triggered (41.8%)"},
            ]
        elif "scenario_5" in self.scenario_id:
            timeline = [
                {"time": "14:00", "error_rate": 0.05, "status": "HEALTHY", "event": "Normal baseline"},
                {"time": "14:03", "error_rate": 0.08, "status": "HEALTHY", "event": ""},
                {"time": "14:05", "error_rate": 0.10, "status": "HEALTHY", "event": "v2.4.2 deployed (GA4 tags)"},
                {"time": "14:08", "error_rate": 0.12, "status": "HEALTHY", "event": "Verifications normal"},
                {"time": "14:11", "error_rate": 2.10, "status": "DEGRADED", "event": "Replica-02 lag > 300s"},
                {"time": "14:13", "error_rate": 14.5, "status": "DEGRADED", "event": "Stale read RecordNotFound"},
                {"time": "14:14", "error_rate": 28.0, "status": "CRITICAL", "event": "Conflict with recovery"},
                {"time": "14:15", "error_rate": 32.4, "status": "CRITICAL", "event": "Alert Triggered (32.4%)"},
            ]
        else:
            timeline = [
                {"time": "13:50", "error_rate": 0.05, "status": "HEALTHY", "event": ""},
                {"time": "13:55", "error_rate": 0.10, "status": "HEALTHY", "event": ""},
                {"time": "14:00", "error_rate": 0.12, "status": "HEALTHY", "event": ""},
                {"time": "14:01", "error_rate": 0.18, "status": "HEALTHY", "event": ""},
                {"time": "14:02", "error_rate": 0.20, "status": "HEALTHY", "event": "v2.4.0 deployed"},
                {"time": "14:03", "error_rate": 14.5, "status": "DEGRADED", "event": "Pool capacity warning"},
                {"time": "14:04", "error_rate": 38.2, "status": "CRITICAL", "event": "ConnectionPoolExhausted"},
                {"time": "14:05", "error_rate": 42.1, "status": "CRITICAL", "event": ""},
                {"time": "14:10", "error_rate": 44.0, "status": "CRITICAL", "event": ""},
                {"time": "14:15", "error_rate": 43.5 if "1" in self.scenario_id else 54.8, "status": "CRITICAL", "event": "Alert Triggered"},
            ]

        # Append post-remediation points if actions were taken
        if self.action_history:
            last_act = self.action_history[-1]
            act_name = last_act.get("action", "remediation")
            success = last_act.get("success", False)

            if success:
                if "scenario_3" in self.scenario_id:
                    timeline.extend([
                        {"time": "14:16", "error_rate": 8.5, "status": "RECOVERING", "event": f"{act_name} executed (heap cleared)"},
                        {"time": "14:17", "error_rate": 0.5, "status": "HEALTHY", "event": "Liveness probe OK"},
                        {"time": "14:18", "error_rate": 0.1, "status": "HEALTHY", "event": "Service Recovered (0.1%)"},
                    ])
                elif "scenario_4" in self.scenario_id:
                    timeline.extend([
                        {"time": "14:19", "error_rate": 10.2, "status": "RECOVERING", "event": f"{act_name} executed"},
                        {"time": "14:20", "error_rate": 1.1, "status": "HEALTHY", "event": "StripeSecondary active"},
                        {"time": "14:21", "error_rate": 0.8, "status": "HEALTHY", "event": "Recovered (PayGate still down)"},
                    ])
                elif "scenario_5" in self.scenario_id:
                    timeline.extend([
                        {"time": "14:16", "error_rate": 5.8, "status": "RECOVERING", "event": f"{act_name} executed"},
                        {"time": "14:17", "error_rate": 0.4, "status": "HEALTHY", "event": "Replica-02 drained"},
                        {"time": "14:18", "error_rate": 0.2, "status": "HEALTHY", "event": "Recovered (Replica-01 active)"},
                    ])
                elif "scenario_2" in self.scenario_id:
                    timeline.extend([
                        {"time": "14:17", "error_rate": 12.0, "status": "RECOVERING", "event": f"{act_name} executed (idle conns cleared)"},
                        {"time": "14:18", "error_rate": 0.8, "status": "HEALTHY", "event": "DB connections pool normalized"},
                        {"time": "14:19", "error_rate": 0.2, "status": "HEALTHY", "event": "Service Recovered (0.2%)"},
                    ])
                else:
                    timeline.extend([
                        {"time": "14:16", "error_rate": 18.2, "status": "RECOVERING", "event": f"{act_name} executed"},
                        {"time": "14:17", "error_rate": 1.5, "status": "RECOVERING", "event": "Pool restored (50)"},
                        {"time": "14:18", "error_rate": 0.2, "status": "HEALTHY", "event": "Recovered (v2.3.9)"},
                    ])
            else:
                fail_err = 32.4 if "5" in self.scenario_id else (41.8 if "4" in self.scenario_id else 52.4)
                fail_event = "Fix Failed (Replica lag)" if "5" in self.scenario_id else ("Fix Failed (Vendor timeouts persist)" if "4" in self.scenario_id else "Fix Failed (DB Pool full)")
                timeline.extend([
                    {"time": "14:16", "error_rate": fail_err, "status": "CRITICAL", "event": f"{act_name} executed"},
                    {"time": "14:17", "error_rate": fail_err, "status": "CRITICAL", "event": fail_event},
                    {"time": "14:18", "error_rate": fail_err, "status": "CRITICAL", "event": "500 errors persist"},
                ])

        return timeline

    # -------------------------------------------------------------------------
    # REMEDIATION ACTIONS
    # -------------------------------------------------------------------------

    def rollback(
        self,
        service_name: Optional[str] = None,
        target_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulates executing an automated deployment rollback to a previous version.
        
        STATE CHANGE BEHAVIOR & REALISTIC DIVERGENCE:
        - In Scenario 1: Rollback to v2.3.9 fixes the pool configuration regression.
          Pool size restored to 50, error rate drops to 0.2%, status transitions to HEALTHY.
        - In Scenario 2: Rollback to v2.3.9 succeeds at the deploy layer, BUT the database
          connection table remains saturated (500/500). Status remains CRITICAL.
        - In Scenario 4: Rollback to v2.4.0 succeeds at the deploy layer, BUT PayGate
          external timeouts persist. Status remains CRITICAL.
        - In Scenario 5: Rollback to v2.4.1 succeeds at the deploy layer, BUT db-replica-02
          replication lag persists. Status remains CRITICAL.
        """
        target_service = service_name or self.service_name
        current_version = self.state.get("current_version", "v2.4.0")
        target_ver = target_version or self.state.get("previous_version") or "v2.3.9"
        ts = self._get_timestamp()
        self.lifecycle_state = "REMEDIATING"

        # Record deployment entry
        new_deploy = {
            "deploy_id": f"dep-rollback-{len(self.deploys) + 1}",
            "version": target_ver,
            "service": target_service,
            "timestamp": ts,
            "author": "devops-copilot-agent",
            "commit_hash": "rollback",
            "commit_msg": f"Automated rollback from {current_version} to {target_ver}",
            "status": "DEPLOYED"
        }
        self.deploys.append(new_deploy)

        # Log deployment pipeline execution
        self.logs.append({
            "timestamp": ts,
            "level": "INFO",
            "service": "deployer",
            "message": f"Initiating automated rollback of {target_service} to {target_ver}."
        })

        if "scenario_1" in self.scenario_id:
            # SCENARIO 1: Rollback cures the issue!
            self.state["current_version"] = target_ver
            self.state["status"] = "HEALTHY"
            self.state["error_rate"] = "0.2%"
            self.state["avg_latency_ms"] = 18
            self.state["max_db_connections"] = 50
            self.state["active_db_connections"] = 8
            self.state["uptime_seconds"] = 30
            self.state["last_action"] = f"Rolled back to {target_ver}"
            self.lifecycle_state = "VERIFIED"

            recovery_log = {
                "timestamp": self._get_timestamp(),
                "level": "INFO",
                "service": target_service,
                "message": f"Rollback to {target_ver} completed successfully. DB connection pool restored to default (50). Service healthy."
            }
            self.logs.append(recovery_log)

            outcome = {
                "success": True,
                "action": "rollback",
                "service": target_service,
                "previous_version": current_version,
                "new_version": target_ver,
                "service_status": "HEALTHY",
                "error_rate": "0.2%",
                "message": f"Successfully rolled back {target_service} to {target_ver}. Error rate dropped to 0.2%. Service is HEALTHY."
            }

        elif "scenario_4" in self.scenario_id:
            # SCENARIO 4: Rollback does NOT fix third-party outage
            self.state["current_version"] = target_ver
            self.state["status"] = "CRITICAL"
            self.state["error_rate"] = "41.8%"
            self.state["last_action"] = f"Rolled back to {target_ver} (INEFFECTIVE: Vendor outage persists)"

            self.logs.append({
                "timestamp": self._get_timestamp(),
                "level": "ERROR",
                "service": target_service,
                "message": f"Rollback to {target_ver} completed, but 504 Gateway Timeout errors persist. Primary gateway api.paygate-global.com is still unresponsive."
            })
            outcome = {
                "success": False,
                "action": "rollback",
                "service": target_service,
                "previous_version": current_version,
                "new_version": target_ver,
                "service_status": "CRITICAL",
                "error_rate": "41.8%",
                "message": f"Rollback to {target_ver} deployed, but {target_service} remains CRITICAL. The recent deploy was an unrelated UI copy change; errors are upstream third-party timeouts."
            }

        elif "scenario_5" in self.scenario_id:
            # SCENARIO 5: Rollback does NOT fix database replica lag
            self.state["current_version"] = target_ver
            self.state["status"] = "CRITICAL"
            self.state["error_rate"] = "32.4%"
            self.state["last_action"] = f"Rolled back to {target_ver} (INEFFECTIVE: Replica lag persists)"

            self.logs.append({
                "timestamp": self._get_timestamp(),
                "level": "ERROR",
                "service": target_service,
                "message": f"Rollback to {target_ver} completed, but 500 errors persist on /v1/accounts/verify. Replica db-replica-02 is still lagging by 480s."
            })
            outcome = {
                "success": False,
                "action": "rollback",
                "service": target_service,
                "previous_version": current_version,
                "new_version": target_ver,
                "service_status": "CRITICAL",
                "error_rate": "32.4%",
                "message": f"Rollback to {target_ver} deployed, but {target_service} remains CRITICAL. The deployment was an unrelated client analytics tag; the root cause is database replication lag on db-replica-02."
            }

        else:
            # SCENARIO 2: Fix fails! Rollback deployed, but DB connection exhaustion persists
            self.state["current_version"] = target_ver
            self.state["status"] = "CRITICAL"
            self.state["error_rate"] = "52.4%"
            self.state["avg_latency_ms"] = 2750
            self.state["last_action"] = f"Rolled back to {target_ver} (FAILED TO RESOLVE)"

            fail_log = {
                "timestamp": self._get_timestamp(),
                "level": "FATAL",
                "service": "postgres-primary",
                "message": "FATAL: remaining connection slots are reserved for non-replication superuser connections (500/500 active)"
            }
            error_log = {
                "timestamp": self._get_timestamp(),
                "level": "ERROR",
                "service": target_service,
                "message": f"Rollback to {target_ver} finished, but {target_service} still failing health checks. Database connection refused."
            }
            self.logs.append(fail_log)
            self.logs.append(error_log)

            outcome = {
                "success": False,
                "action": "rollback",
                "service": target_service,
                "previous_version": current_version,
                "new_version": target_ver,
                "service_status": "CRITICAL",
                "error_rate": "52.4%",
                "message": f"Rollback to {target_ver} deployed, BUT {target_service} remains CRITICAL. 500 errors persist due to underlying database connection exhaustion."
            }

        logger.info(f"Rollback completed: target={target_ver}, success={outcome['success']}, status={outcome['service_status']}")
        self.action_history.append(outcome)
        return outcome

    def restart_service(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulates soft restarting service pods or worker processes.
        
        BEHAVIOR:
        - In Scenario 3 (Memory Leak): Restart clears exhausted JVM heap (1968MB -> 240MB). Service recovers to HEALTHY.
        - In Scenario 2:
          * If called BEFORE rollback: Fails, because PostgreSQL pool is saturated.
          * If called AFTER rollback (secondary remediation): Succeeds! Pod restart drops hung sockets
            and cleans up orphaned connections, restoring database connectivity and recovering service to HEALTHY.
        - In Scenario 1 / 4 / 5: Fails safely because restarting stateless pods does not fix misconfigured pool size,
          upstream vendor outages, or asynchronous database replica lag.
        """
        target_service = service_name or self.service_name
        ts = self._get_timestamp()
        self.lifecycle_state = "REMEDIATING"

        self.logs.append({
            "timestamp": ts,
            "level": "WARN",
            "service": target_service,
            "message": "Restart initiated by operator. Terminating worker processes..."
        })
        self.logs.append({
            "timestamp": self._get_timestamp(),
            "level": "INFO",
            "service": target_service,
            "message": "Service restarted. Listening on :8080."
        })

        # Check if previous rollback was already attempted in Scenario 2
        has_prior_rollback = any(a.get("action") == "rollback" for a in self.action_history)

        if self.state.get("status") == "HEALTHY":
            outcome = {
                "success": True,
                "action": "restart_service",
                "service": target_service,
                "service_status": "HEALTHY",
                "error_rate": self.state.get("error_rate", "0.1%"),
                "message": f"Service {target_service} restarted successfully and is HEALTHY."
            }

        elif "scenario_3" in self.scenario_id:
            # SCENARIO 3: Service restart flushes exhausted heap memory and clears leak!
            self.state["status"] = "HEALTHY"
            self.state["error_rate"] = "0.1%"
            self.state["avg_latency_ms"] = 16
            self.state["memory_usage_mb"] = 240
            self.state["memory_pct"] = "11.7%"
            self.state["uptime_seconds"] = 15
            self.state["last_action"] = "restarted (heap memory flushed)"
            self.lifecycle_state = "VERIFIED"

            recovery_log = {
                "timestamp": self._get_timestamp(),
                "level": "INFO",
                "service": target_service,
                "message": "Service restart complete. JVM heap reset to 240MB / 2048MB. Error rate normalized to 0.1%."
            }
            self.logs.append(recovery_log)

            outcome = {
                "success": True,
                "action": "restart_service",
                "service": target_service,
                "service_status": "HEALTHY",
                "error_rate": "0.1%",
                "message": f"Successfully restarted {target_service}. Leaked memory cleared (heap: 11.7%). Service is HEALTHY."
            }

        elif "scenario_2" in self.scenario_id and has_prior_rollback:
            # SCENARIO 2 (Secondary Remediation): Rollback already done; pod restart + DB connection flush recovers system!
            self.state["status"] = "HEALTHY"
            self.state["error_rate"] = "0.2%"
            self.state["avg_latency_ms"] = 22
            self.state["db_status"] = "ONLINE"
            self.state["active_db_connections"] = 14
            self.state["max_db_connections"] = 50
            self.state["uptime_seconds"] = 15
            self.state["last_action"] = "restarted (hung sockets dropped, DB pool restored)"
            self.lifecycle_state = "VERIFIED"

            db_flush_log = {
                "timestamp": self._get_timestamp(),
                "level": "INFO",
                "service": "postgres-primary",
                "message": "Orphaned idle client connections terminated. Active DB connections reduced from 500 to 14/50."
            }
            app_recovery_log = {
                "timestamp": self._get_timestamp(),
                "level": "INFO",
                "service": target_service,
                "message": f"Service restart complete on {self.state.get('current_version')}. Database connectivity restored. Error rate 0.2%."
            }
            self.logs.append(db_flush_log)
            self.logs.append(app_recovery_log)

            outcome = {
                "success": True,
                "action": "restart_service",
                "service": target_service,
                "service_status": "HEALTHY",
                "error_rate": "0.2%",
                "message": f"Successfully restarted {target_service} and released orphaned database connections. DB status ONLINE (14/50 active). Service is HEALTHY."
            }

        elif "scenario_4" in self.scenario_id:
            # SCENARIO 4: Restart does NOT fix external vendor outage
            self.state["uptime_seconds"] = 15
            self.state["last_action"] = "restarted (timeouts persist)"
            self.logs.append({
                "timestamp": self._get_timestamp(),
                "level": "ERROR",
                "service": target_service,
                "message": "GatewayTimeoutException: Outbound calls to api.paygate-global.com continue timing out after service restart."
            })
            outcome = {
                "success": False,
                "action": "restart_service",
                "service": target_service,
                "service_status": "CRITICAL",
                "error_rate": "41.8%",
                "message": f"Service {target_service} restarted, but external gateway api.paygate-global.com is still unresponsive."
            }

        elif "scenario_5" in self.scenario_id:
            # SCENARIO 5: Restart does NOT fix database replica lag
            self.state["uptime_seconds"] = 15
            self.state["last_action"] = "restarted (replica lag persists)"
            self.logs.append({
                "timestamp": self._get_timestamp(),
                "level": "ERROR",
                "service": target_service,
                "message": "Restarting application pods did not clear 480s replication lag on db-replica-02."
            })
            outcome = {
                "success": False,
                "action": "restart_service",
                "service": target_service,
                "service_status": "CRITICAL",
                "error_rate": "32.4%",
                "message": f"Service {target_service} restarted, but db-replica-02 is still lagging by 480s. Stale read errors persist."
            }

        elif "scenario_1" in self.scenario_id:
            # SCENARIO 1: Still on misconfigured pool config in v2.4.0
            self.state["uptime_seconds"] = 15
            self.state["last_action"] = "restarted (errors resumed)"
            self.logs.append({
                "timestamp": self._get_timestamp(),
                "level": "ERROR",
                "service": target_service,
                "message": "ConnectionPoolExhaustedException: pool size 10 exceeded. Restart did not resolve pool size configuration."
            })
            outcome = {
                "success": False,
                "action": "restart_service",
                "service": target_service,
                "service_status": "CRITICAL",
                "error_rate": self.state.get("error_rate", "43.5%"),
                "message": f"Service {target_service} restarted, but still running v2.4.0 with pool size 10. Errors resumed immediately."
            }

        else:
            # SCENARIO 2 (Initial without rollback): DB exhausted
            self.state["uptime_seconds"] = 15
            self.state["last_action"] = "restarted (DB connection refused)"
            self.logs.append({
                "timestamp": self._get_timestamp(),
                "level": "FATAL",
                "service": "postgres-primary",
                "message": "FATAL: too many connections for role 'payment_app'"
            })
            outcome = {
                "success": False,
                "action": "restart_service",
                "service": target_service,
                "service_status": "CRITICAL",
                "error_rate": self.state.get("error_rate", "54.8%"),
                "message": f"Service {target_service} restarted, but cannot connect to PostgreSQL database (connection pool exhausted)."
            }

        logger.info(f"Restart completed: success={outcome['success']}, status={outcome['service_status']}")
        self.action_history.append(outcome)
        return outcome

    def escalate_and_enable_fallback(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulates escalating a third-party vendor outage and activating standby fallback provider.
        Bypasses degraded PayGate Global gateway and routes transactions to StripeSecondary.
        """
        target_service = service_name or self.service_name
        ts = self._get_timestamp()
        self.lifecycle_state = "REMEDIATING"

        self.logs.append({
            "timestamp": ts,
            "level": "INFO",
            "service": "devops-copilot-agent",
            "message": "Action 'escalate_and_enable_fallback' authorized. Escalating to PayGate NOC and enabling fallback."
        })
        self.logs.append({
            "timestamp": self._get_timestamp(),
            "level": "INFO",
            "service": "feature-flags",
            "message": "Feature flag 'payment.enable_secondary_fallback' set to TRUE. Rerouting traffic to StripeSecondary."
        })
        self.logs.append({
            "timestamp": self._get_timestamp(),
            "level": "INFO",
            "service": target_service,
            "message": "Traffic cutover complete. 100% of checkout transactions processing via StripeSecondary. Latency: 58ms. Primary vendor PayGate remains UNRESPONSIVE."
        })

        self.state["status"] = "HEALTHY"
        self.state["error_rate"] = "0.8%"
        self.state["avg_latency_ms"] = 58
        self.state["fallback_provider_enabled"] = True
        self.state["external_gateway_status"] = "UNRESPONSIVE (Bypassed via StripeSecondary)"
        self.state["last_action"] = "escalated & fallback enabled"
        self.lifecycle_state = "VERIFIED"

        outcome = {
            "success": True,
            "action": "escalate_and_enable_fallback",
            "service": target_service,
            "service_status": "HEALTHY",
            "error_rate": "0.8%",
            "message": f"Escalated to vendor NOC (PayGate Global) and enabled secondary fallback provider (StripeSecondary). Error rate dropped from 41.8% to 0.8%. Primary vendor remains down; transactions successfully routed through fallback."
        }
        
        logger.info(f"Fallback enabled: success={outcome['success']}, status={outcome['service_status']}")
        self.action_history.append(outcome)
        return outcome

    def failover_replica(self, service_name: Optional[str] = None, target_replica: str = "db-replica-02") -> Dict[str, Any]:
        """
        Simulates draining and failing over a degraded database read replica.
        Reroutes verification read traffic from lagging replica to healthy node db-replica-01.
        """
        target_service = service_name or self.service_name
        ts = self._get_timestamp()
        self.lifecycle_state = "REMEDIATING"

        self.logs.append({
            "timestamp": ts,
            "level": "INFO",
            "service": "devops-copilot-agent",
            "message": f"Action 'failover_replica' executed for {target_replica}."
        })
        self.logs.append({
            "timestamp": self._get_timestamp(),
            "level": "INFO",
            "service": "patroni-agent",
            "message": f"Draining query connections from {target_replica} (lag: 480s). Re-routing read traffic to healthy node db-replica-01."
        })
        self.logs.append({
            "timestamp": self._get_timestamp(),
            "level": "INFO",
            "service": target_service,
            "message": "Read traffic cutover complete. 100% of account verification queries succeeding on db-replica-01. Error rate normalized to 0.2%."
        })

        self.state["status"] = "HEALTHY"
        self.state["error_rate"] = "0.2%"
        self.state["avg_latency_ms"] = 15
        self.state["failing_node"] = f"DRAINED ({target_replica})"
        self.state["db_health"] = "HEALTHY (Read traffic routed exclusively to db-replica-01)"
        self.state["last_action"] = f"Failed over {target_replica}"
        self.lifecycle_state = "VERIFIED"

        outcome = {
            "success": True,
            "action": "failover_replica",
            "service": target_service,
            "service_status": "HEALTHY",
            "error_rate": "0.2%",
            "message": f"Successfully drained and failed over stale replica '{target_replica}'. Read traffic rerouted to healthy replica 'db-replica-01'. Error rate dropped to 0.2%. Service is HEALTHY."
        }
        
        logger.info(f"Failover completed: target={target_replica}, success={outcome['success']}, status={outcome['service_status']}")
        self.action_history.append(outcome)
        return outcome

    # -------------------------------------------------------------------------
    # VERIFICATION ENGINE
    # -------------------------------------------------------------------------

    def verify_remediation(
        self,
        action: Optional[str] = None,
        service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formal verification engine that verifies whether a remediation actually resolved the incident.
        
        LIFECYCLE FLOW:
        ACTION -> get current state -> compare with incident state -> check service health
        -> check error rate drop -> check subsystem health -> determine SUCCESS / FAILED / PARTIAL.
        
        Ensures the agent does NOT assume an action succeeded simply because the command finished without errors.
        """
        target_service = service_name or self.service_name
        current_status = self.get_status(target_service)
        
        if not self.action_history:
            return {
                "verdict": "NO_ACTION_TAKEN",
                "recovered": False,
                "service": target_service,
                "scenario": self.scenario_id,
                "service_status": current_status.get("status"),
                "error_rate": current_status.get("error_rate"),
                "message": "No remediation actions have been executed yet."
            }

        last_action = self.action_history[-1]
        act_name = action or last_action.get("action", "unknown")
        
        # Extract pre-incident / incident and current values
        before_err_str = self.incident_snapshot.get("error_rate", "0%")
        after_err_str = current_status.get("error_rate", "0%")
        before_err = self._parse_error_rate_float(before_err_str)
        after_err = self._parse_error_rate_float(after_err_str)
        
        is_healthy = (current_status.get("status") == "HEALTHY")
        err_dropped = (after_err < 0.05) and (after_err < before_err * 0.5)

        # Subsystem checks
        subsystem_checks = {}
        
        # 1. Database check
        db_stat = current_status.get("db_status", "UNKNOWN")
        active_db = current_status.get("active_db_connections", 0)
        max_db = current_status.get("max_db_connections", 0)
        if "CONNECTIONS_EXHAUSTED" in str(db_stat) or (max_db > 0 and active_db >= max_db):
            subsystem_checks["database"] = f"CRITICAL: Connections saturated ({active_db}/{max_db})"
        else:
            subsystem_checks["database"] = f"HEALTHY: Connections pool normal ({active_db}/{max_db or 50})"

        # 2. Memory check (Scenario 3)
        if "memory_pct" in current_status:
            mem_pct = current_status.get("memory_pct", "0%")
            if "9" in mem_pct:
                subsystem_checks["memory"] = f"CRITICAL: Heap saturation ({mem_pct})"
            else:
                subsystem_checks["memory"] = f"HEALTHY: Heap nominal ({mem_pct})"

        # 3. Third-party vendor check (Scenario 4)
        if "external_gateway_status" in current_status:
            gw_stat = current_status.get("external_gateway_status", "")
            if "Bypassed" in gw_stat or current_status.get("fallback_provider_enabled"):
                subsystem_checks["external_dependencies"] = "HEALTHY: Primary outage bypassed via StripeSecondary"
            else:
                subsystem_checks["external_dependencies"] = f"CRITICAL: PayGate Global is {gw_stat}"

        # 4. Replica lag check (Scenario 5)
        if "failing_node" in current_status:
            node = current_status.get("failing_node", "")
            if "DRAINED" in node:
                subsystem_checks["replica_health"] = "HEALTHY: Stale replica drained, read traffic on db-replica-01"
            else:
                subsystem_checks["replica_health"] = f"CRITICAL: Replica {node} has excessive replication lag"

        # Determine verdict
        if is_healthy and err_dropped:
            verdict = "SUCCESS"
            recovered = True
            msg = f"Remediation '{act_name}' succeeded. Service recovered to HEALTHY. Error rate dropped from {before_err_str} to {after_err_str}."
        elif current_status.get("status") == "DEGRADED" or (after_err < before_err * 0.6 and after_err < 0.15):
            verdict = "PARTIALLY_RECOVERED"
            recovered = False
            msg = f"Remediation '{act_name}' yielded partial recovery. Error rate decreased ({before_err_str} -> {after_err_str}), but service status remains {current_status.get('status')}."
        else:
            verdict = "FAILED"
            recovered = False
            msg = f"Remediation '{act_name}' failed to resolve incident. Service remains CRITICAL with error rate {after_err_str}. Underlying root cause persists."

        verification_result = {
            "verdict": verdict,
            "recovered": recovered,
            "service": target_service,
            "scenario": self.scenario_id,
            "action_evaluated": act_name,
            "service_status": current_status.get("status"),
            "error_rate": after_err_str,
            "before_error_rate": before_err_str,
            "latency_ms": current_status.get("avg_latency_ms"),
            "metrics_diff": {
                "error_rate_change": f"{before_err_str} -> {after_err_str}",
                "version_change": f"{self.incident_snapshot.get('current_version')} -> {current_status.get('current_version')}",
                "latency_change_ms": current_status.get("avg_latency_ms", 0) - self.incident_snapshot.get("avg_latency_ms", 0)
            },
            "subsystem_checks": subsystem_checks,
            "message": msg,
            "timestamp": self._get_timestamp()
        }

        logger.info(f"Verification result: verdict={verdict}, recovered={recovered}, err={after_err_str}")
        return verification_result

    def get_action_history(self) -> List[Dict[str, Any]]:
        """Returns the full log of remediation attempts and outcomes."""
        return copy.deepcopy(self.action_history)


# Module-level singleton instance for convenience
_default_env = SimulatedEnvironment("scenario_1")


def get_environment() -> SimulatedEnvironment:
    """Returns the active global simulation environment instance."""
    return _default_env


# Convenience top-level functions matching requirements
def get_logs(service_name: Optional[str] = None, limit: Optional[int] = 50, level: Optional[str] = None) -> List[Dict[str, Any]]:
    return _default_env.get_logs(service_name=service_name, limit=limit, level=level)


def get_status(service_name: Optional[str] = None) -> Dict[str, Any]:
    return _default_env.get_status(service_name=service_name)


def get_deploys(service_name: Optional[str] = None, limit: Optional[int] = 5) -> List[Dict[str, Any]]:
    return _default_env.get_deploys(service_name=service_name, limit=limit)


def get_past_incidents(limit: Optional[int] = 5, query: Optional[str] = None) -> List[Dict[str, Any]]:
    return _default_env.get_past_incidents(limit=limit, query=query)


def rollback(service_name: Optional[str] = None, target_version: Optional[str] = None) -> Dict[str, Any]:
    return _default_env.rollback(service_name=service_name, target_version=target_version)


def restart_service(service_name: Optional[str] = None) -> Dict[str, Any]:
    return _default_env.restart_service(service_name=service_name)


def escalate_and_enable_fallback(service_name: Optional[str] = None) -> Dict[str, Any]:
    return _default_env.escalate_and_enable_fallback(service_name=service_name)


def failover_replica(service_name: Optional[str] = None, target_replica: str = "db-replica-02") -> Dict[str, Any]:
    return _default_env.failover_replica(service_name=service_name, target_replica=target_replica)


def reset_environment(scenario: str = "scenario_1", start_in_incident: bool = True) -> Dict[str, Any]:
    return _default_env.reset_environment(scenario=scenario, start_in_incident=start_in_incident)


def trigger_incident() -> Dict[str, Any]:
    return _default_env.trigger_incident()


def get_healthy_state() -> Dict[str, Any]:
    return _default_env.get_healthy_state()


def verify_remediation(action: Optional[str] = None, service_name: Optional[str] = None) -> Dict[str, Any]:
    return _default_env.verify_remediation(action=action, service_name=service_name)


def get_action_history() -> List[Dict[str, Any]]:
    return _default_env.get_action_history()


def get_metrics_timeline(service_name: Optional[str] = None) -> List[Dict[str, Any]]:
    return _default_env.get_metrics_timeline(service_name=service_name)
