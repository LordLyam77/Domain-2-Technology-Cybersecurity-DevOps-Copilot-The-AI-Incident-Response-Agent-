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
        return {
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


def reset_environment(scenario: str = "scenario_1") -> Dict[str, Any]:
    return _default_env.reset_environment(scenario=scenario)
