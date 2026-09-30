"""
Simulation package for DevOps Copilot.
Contains the simulated infrastructure environment (services, deploys, logs, incidents).
"""
from .environment import (
    SimulatedEnvironment,
    get_environment,
    get_status,
    get_logs,
    get_deploys,
    get_past_incidents,
    get_metrics_timeline,
    rollback,
    restart_service,
    escalate_and_enable_fallback,
    failover_replica,
    reset_environment,
    verify_remediation,
    trigger_incident,
    get_healthy_state,
    get_action_history
)

__all__ = [
    "SimulatedEnvironment",
    "get_environment",
    "get_status",
    "get_logs",
    "get_deploys",
    "get_past_incidents",
    "get_metrics_timeline",
    "rollback",
    "restart_service",
    "escalate_and_enable_fallback",
    "failover_replica",
    "reset_environment",
    "verify_remediation",
    "trigger_incident",
    "get_healthy_state",
    "get_action_history"
]
