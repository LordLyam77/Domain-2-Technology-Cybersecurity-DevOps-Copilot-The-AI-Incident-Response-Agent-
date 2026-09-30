"""
Simulated DevOps Environment for incident response.

WHY THIS FILE EXISTS:
In real incident response, engineers use tools (like Datadog, Prometheus, ArgoCD, Jira)
to inspect logs, check service health, look at recent deployments, and query past incidents.
For this hackathon project, we simulate those tools completely locally using JSON data.
This allows our AI agent to perform real investigations, make changes (like rollback or restart),
and observe consequences—without needing cloud credentials or real server infrastructure.
"""

import json
import os
import copy
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Locate data directory relative to this file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data")


class SimulatedEnvironment:
    """
    Represents the simulated infrastructure.
    Holds mutable state in memory so actions like 'rollback' or 'restart'
    immediately change system health, version, error rate, and logs.
    """

    def __init__(self, scenario: str = "scenario_1"):
        self.scenario_id = scenario
        self.state: Dict[str, Any] = {}
        self.logs: List[Dict[str, Any]] = []
        self.deploys: List[Dict[str, Any]] = []
        self.past_incidents: List[Dict[str, Any]] = []
        self.action_history: List[Dict[str, Any]] = []
        
        # Load the selected scenario data and historical incidents
        self.reset_environment(scenario)

    def _get_timestamp(self) -> str:
        """Returns current simulated ISO timestamp for log injection."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def reset_environment(self, scenario: str = "scenario_1") -> Dict[str, Any]:
        """
        Resets the environment back to the start of an incident scenario.
        
        WHY:
        Allows users and tests to replay scenarios from scratch cleanly.
        Supports 'scenario_1' (bad deploy where rollback fixes it)
        and 'scenario_2' (underlying DB issue where rollback fails).
        """
        # Map shorthand names to actual JSON file names
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

        filename = scenario_map.get(scenario, "scenario_1_bad_deploy.json")
        filepath = os.path.join(DATA_DIR, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Scenario file not found: {filepath}")

        # Load fresh copy of scenario data
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Deep-copy everything so modifications during runs do not mutate the raw files
        self.scenario_id = data.get("scenario_id", scenario)
        self.title = data.get("title", "")
        self.description = data.get("description", "")
        self.service_name = data.get("service_name", "payment-service")
        self.state = copy.deepcopy(data.get("initial_state", {}))
        self.logs = copy.deepcopy(data.get("logs", []))
        self.deploys = copy.deepcopy(data.get("deploys", []))
        self.action_history = []

        # Load past incidents knowledge base
        past_incidents_path = os.path.join(DATA_DIR, "past_incidents.json")
        if os.path.exists(past_incidents_path):
            with open(past_incidents_path, "r", encoding="utf-8") as f:
                self.past_incidents = json.load(f)
        else:
            self.past_incidents = []

        return {
            "status": "success",
            "message": f"Environment reset to {self.scenario_id}.",
            "service": self.service_name,
            "current_state": self.state
        }

    def get_logs(
        self,
        service_name: Optional[str] = None,
        limit: Optional[int] = 50,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Simulates log aggregation tools (e.g., Elasticsearch / Datadog Logs).
        
        WHY:
        Logs are the primary evidence an SRE / DevOps engineer checks.
        Filters allow the agent to zoom in on ERRORs or inspect specific services.
        """
        filtered = self.logs

        # Filter by service if specified
        if service_name:
            filtered = [
                log for log in filtered
                if log.get("service", "").lower() == service_name.lower()
            ]

        # Filter by log level (e.g., ERROR, WARN, INFO, FATAL)
        if level:
            filtered = [
                log for log in filtered
                if log.get("level", "").upper() == level.upper()
            ]

        # Return most recent logs up to the limit
        if limit and limit > 0:
            return filtered[-limit:]
        return filtered

    def get_status(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulates health check & metrics endpoints (e.g., Prometheus / Kubernetes status).
        
        WHY:
        Provides high-level vital signs: Is the service UP? What is the error rate?
        What version is running? How is database connectivity?
        """
        target_service = service_name or self.service_name
        res = {
            "service": target_service,
            "scenario": self.scenario_id,
            "status": self.state.get("status", "UNKNOWN"),
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
        if "memory_usage_mb" in self.state:
            res["memory_usage_mb"] = self.state.get("memory_usage_mb")
            res["max_memory_mb"] = self.state.get("max_memory_mb")
            res["memory_pct"] = self.state.get("memory_pct")
        if "external_gateway" in self.state:
            res["external_gateway"] = self.state.get("external_gateway")
            res["external_gateway_status"] = self.state.get("external_gateway_status")
            res["fallback_provider_enabled"] = self.state.get("fallback_provider_enabled")
            res["cpu_usage"] = self.state.get("cpu_usage")
            res["db_health"] = self.state.get("db_health")
        if "failing_node" in self.state:
            res["failing_node"] = self.state.get("failing_node")
            res["db_health"] = self.state.get("db_health")
            res["replica_nodes"] = self.state.get("replica_nodes")
        return res

    def get_metrics_timeline(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generates timeseries data points of error rate over time from logs and state.
        
        WHY:
        Engineers need to see the shape of an outage over time:
        - When did normal traffic (0.1% - 0.2%) begin failing?
        - Did the spike coincide with the deployment?
        - Did the error rate drop after the remediation?
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

        # If an action has been taken, append the recovery or post-remediation points
        if self.action_history:
            last_act = self.action_history[-1]
            act_name = last_act.get("action", "remediation")
            success = last_act.get("success", False)

            if success and "scenario_3" in self.scenario_id:
                # Restart cured memory leak in Scenario 3
                timeline.extend([
                    {"time": "14:16", "error_rate": 8.5, "status": "RECOVERING", "event": f"{act_name} executed (heap cleared)"},
                    {"time": "14:17", "error_rate": 0.5, "status": "HEALTHY", "event": "Liveness probe OK"},
                    {"time": "14:18", "error_rate": 0.1, "status": "HEALTHY", "event": "Service Recovered (0.1%)"},
                ])
            elif success and "scenario_4" in self.scenario_id:
                # Fallback enabled cured issue in Scenario 4
                timeline.extend([
                    {"time": "14:19", "error_rate": 10.2, "status": "RECOVERING", "event": f"{act_name} executed"},
                    {"time": "14:20", "error_rate": 1.1, "status": "HEALTHY", "event": "StripeSecondary active"},
                    {"time": "14:21", "error_rate": 0.8, "status": "HEALTHY", "event": "Recovered (PayGate still down)"},
                ])
            elif success and "scenario_5" in self.scenario_id:
                # Failover replica cured issue in Scenario 5
                timeline.extend([
                    {"time": "14:16", "error_rate": 5.8, "status": "RECOVERING", "event": f"{act_name} executed"},
                    {"time": "14:17", "error_rate": 0.4, "status": "HEALTHY", "event": "Replica-02 drained"},
                    {"time": "14:18", "error_rate": 0.2, "status": "HEALTHY", "event": "Recovered (Replica-01 active)"},
                ])
            elif success and "1" in self.scenario_id:
                # Rollback cured the issue in Scenario 1
                timeline.extend([
                    {"time": "14:16", "error_rate": 18.2, "status": "RECOVERING", "event": f"{act_name} executed"},
                    {"time": "14:17", "error_rate": 1.5, "status": "RECOVERING", "event": "Pool restored"},
                    {"time": "14:18", "error_rate": 0.2, "status": "HEALTHY", "event": "Recovered (v2.3.9)"},
                ])
            else:
                # Rollback or restart failed
                fail_err = 32.4 if "5" in self.scenario_id else (41.8 if "4" in self.scenario_id else 52.4)
                fail_event = "Fix Failed (Replica lag)" if "5" in self.scenario_id else ("Fix Failed (Timeouts persist)" if "4" in self.scenario_id else "Fix Failed (DB Full)")
                timeline.extend([
                    {"time": "14:16", "error_rate": fail_err, "status": "CRITICAL", "event": f"{act_name} executed"},
                    {"time": "14:17", "error_rate": fail_err, "status": "CRITICAL", "event": fail_event},
                    {"time": "14:18", "error_rate": fail_err, "status": "CRITICAL", "event": "Errors persist"},
                ])

        return timeline

    def get_deploys(
        self,
        service_name: Optional[str] = None,
        limit: Optional[int] = 5
    ) -> List[Dict[str, Any]]:
        """
        Simulates deployment tracking systems (e.g., ArgoCD, GitHub Releases).
        
        WHY:
        In incident response, 80%+ of outages are caused by recent changes/deployments.
        Checking recent releases helps the AI correlate when errors began with what code changed.
        """
        deploys = self.deploys
        if service_name:
            deploys = [
                d for d in deploys
                if d.get("service", "").lower() == service_name.lower()
            ]

        # Returns newest deploys first, capped by limit
        sorted_deploys = sorted(
            deploys,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        if limit and limit > 0:
            return sorted_deploys[:limit]
        return sorted_deploys

    def get_past_incidents(
        self,
        limit: Optional[int] = 5,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Simulates past incident postmortems (e.g., Confluence / Jira postmortems).
        
        WHY:
        Experienced engineers consult past incident records to see if similar symptoms
        occurred before and what remediated them.
        """
        results = self.past_incidents

        # Optional keyword search across title, symptoms, root cause, and tags
        if query:
            q = query.lower()
            results = [
                inc for inc in results
                if q in inc.get("title", "").lower()
                or q in inc.get("symptoms", "").lower()
                or q in inc.get("root_cause", "").lower()
                or any(q in tag.lower() for tag in inc.get("tags", []))
            ]

        if limit and limit > 0:
            return results[:limit]
        return results

    def rollback(
        self,
        service_name: Optional[str] = None,
        target_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulates triggering an automated deployment rollback.
        
        STATE CHANGE BEHAVIOR:
        - In Scenario 1: Rollback to v2.3.9 fixes the pool configuration issue.
          Status transitions to HEALTHY, error rate drops to 0.2%, latency normalizes.
        - In Scenario 2: Rollback succeeds from a deployment perspective, BUT
          the database connections remain exhausted (500/500). Status remains CRITICAL!
        """
        target_service = service_name or self.service_name
        current_version = self.state.get("current_version", "v2.4.0")
        target_ver = target_version or self.state.get("previous_version", "v2.3.9")
        ts = self._get_timestamp()

        # Record deployment entry for the rollback
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

        # Append deployment logs
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
            # SCENARIO 2: Fix fails! Rollback happened, but DB connection exhaustion persists
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

        self.action_history.append(outcome)
        return outcome

    def restart_service(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulates restarting service pods/containers.
        
        WHY:
        Often suggested by engineers, but if bad configuration or DB saturation
        remains, a restart will not fix root causes.
        """
        target_service = service_name or self.service_name
        ts = self._get_timestamp()

        self.logs.append({
            "timestamp": ts,
            "level": "WARN",
            "service": target_service,
            "message": f"Restart initiated by operator. Terminating worker processes..."
        })
        self.logs.append({
            "timestamp": self._get_timestamp(),
            "level": "INFO",
            "service": target_service,
            "message": f"Service restarted. Listening on :8080."
        })

        if self.state.get("status") == "HEALTHY":
            # If already healthy, restart keeps it healthy
            outcome = {
                "success": True,
                "action": "restart_service",
                "service": target_service,
                "service_status": "HEALTHY",
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
            # Still on bad config v2.4.0
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
                "error_rate": self.state.get("error_rate"),
                "message": f"Service {target_service} restarted, but still running v2.4.0 with pool size 10. Errors resumed immediately."
            }
        else:
            # Scenario 2: DB exhausted
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
                "error_rate": self.state.get("error_rate"),
                "message": f"Service {target_service} restarted, but cannot connect to PostgreSQL database (connection pool exhausted)."
            }

        self.action_history.append(outcome)
        return outcome

    def escalate_and_enable_fallback(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulates escalating a third-party vendor outage and activating standby fallback provider.
        """
        target_service = service_name or self.service_name
        ts = self._get_timestamp()

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

        outcome = {
            "success": True,
            "action": "escalate_and_enable_fallback",
            "service": target_service,
            "service_status": "HEALTHY",
            "error_rate": "0.8%",
            "message": f"Escalated to vendor NOC (PayGate Global) and enabled secondary fallback provider (StripeSecondary). Error rate dropped from 41.8% to 0.8%. Primary vendor remains down; transactions successfully routed through fallback."
        }
        self.action_history.append(outcome)
        return outcome

    def failover_replica(self, service_name: Optional[str] = None, target_replica: str = "db-replica-02") -> Dict[str, Any]:
        """
        Simulates draining and failing over a degraded database read replica.
        """
        target_service = service_name or self.service_name
        ts = self._get_timestamp()

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

        outcome = {
            "success": True,
            "action": "failover_replica",
            "service": target_service,
            "service_status": "HEALTHY",
            "error_rate": "0.2%",
            "message": f"Successfully drained and failed over stale replica '{target_replica}'. Read traffic rerouted to healthy replica 'db-replica-01'. Error rate dropped to 0.2%. Service is HEALTHY."
        }
        self.action_history.append(outcome)
        return outcome


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


def reset_environment(scenario: str = "scenario_1") -> Dict[str, Any]:
    return _default_env.reset_environment(scenario=scenario)


def get_metrics_timeline(service_name: Optional[str] = None) -> List[Dict[str, Any]]:
    return _default_env.get_metrics_timeline(service_name=service_name)

