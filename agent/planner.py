"""
Remediation Planner for DevOps Copilot.

WHY THIS FILE EXISTS:
In production environments, autonomous AI agents must NEVER execute dangerous,
service-disrupting commands without safety gates.
In real SRE practice:
- A container restart is considered LOW RISK: fast, low blast radius.
- A deployment rollback or database schema change is HIGH RISK: could drop user sessions,
  conflict with in-flight transactions, or affect upstream systems.
This planner classifies risk, enforces human approval for HIGH risk actions,
and provides alternative fallback remediation options if an action is rejected or fails.
"""

from typing import Dict, Any, List, Optional


class RemediationPlan:
    """Represents a proposed remediation action with risk assessment and safety flags."""

    def __init__(
        self,
        action: str,
        risk_level: str,
        target_service: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        reasoning: str = "",
        fallback_action: Optional[str] = None
    ):
        self.action = action  # 'rollback', 'restart_service', etc.
        self.risk_level = risk_level.upper()  # 'HIGH' or 'LOW'
        self.target_service = target_service
        self.description = description
        self.parameters = parameters or {}
        self.reasoning = reasoning
        self.fallback_action = fallback_action
        
        # Human approval is strictly required for HIGH and MEDIUM risk actions
        self.requires_approval = (self.risk_level in ["HIGH", "MEDIUM"])
        self.approved: Optional[bool] = None
        self.execution_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "target_service": self.target_service,
            "description": self.description,
            "parameters": self.parameters,
            "reasoning": self.reasoning,
            "fallback_action": self.fallback_action,
            "approved": self.approved,
            "execution_result": self.execution_result
        }


class RemediationPlanner:
    """Evaluates risks, builds actionable remediation plans, and manages fallbacks."""

    RISK_CLASSIFICATION = {
        "rollback": "HIGH",                      # Reverts production binaries/config
        "escalate_and_enable_fallback": "MEDIUM",# Switches payment routing provider
        "escalate": "MEDIUM",
        "failover_replica": "MEDIUM",            # Drains lagging database replica
        "failover": "MEDIUM",
        "investigate_further": "LOW",            # Requires operator decision
        "investigate": "LOW",
        "restart_service": "LOW",                # Soft restart of stateless containers
        "restart": "LOW",
        "scale_connections": "MEDIUM",
        "terminate_idle_conns": "HIGH"
    }

    @classmethod
    def classify_risk(cls, action_name: str) -> str:
        """Determines whether an action is HIGH, MEDIUM, or LOW risk."""
        act = action_name.lower().strip()
        for key, level in cls.RISK_CLASSIFICATION.items():
            if key in act:
                return level
        return "HIGH"  # Default to safety-first (HIGH risk) if unknown

    def build_plan_from_diagnosis(self, diagnosis: Dict[str, Any]) -> RemediationPlan:
        """
        Translates the coordinator's final structured JSON diagnosis
        into a concrete, executable RemediationPlan.
        """
        recommended = diagnosis.get("recommended_action", "").lower()
        root_cause = diagnosis.get("root_cause", "")
        service_name = "payment-service"
        conf = diagnosis.get("confidence", {})
        conf_score = conf.get("score", 100) if isinstance(conf, dict) else 100

        if conf_score < 60 or "investigate" in recommended:
            action = "investigate_further"
            risk_level = "MEDIUM"
            description = "Conflicting evidence detected between recent deploy and database replica lag. Operator decision required."
            parameters = {
                "conflicting_evidence": True,
                "options": ["failover_replica", "rollback", "gather_more_info"],
                "target_replica": "db-replica-02"
            }
            fallback = "failover_replica"
        elif "failover" in recommended or "replica" in recommended:
            action = "failover_replica"
            risk_level = "MEDIUM"
            description = f"Drain and fail over degraded database replica db-replica-02 to restore healthy read traffic."
            parameters = {"service_name": service_name, "target_replica": "db-replica-02"}
            fallback = "rollback"
        elif "escalat" in recommended or "fallback" in recommended:
            action = "escalate_and_enable_fallback"
            risk_level = "MEDIUM"
            description = f"Escalate vendor incident to third-party gateway NOC and enable secondary fallback provider for {service_name}."
            parameters = {"service_name": service_name, "vendor": "PayGate Global", "fallback_provider": "StripeSecondary"}
            fallback = "rollback"
        elif "rollback" in recommended:
            action = "rollback"
            target_version = "v2.3.9"  # Default previous version
            risk_level = "HIGH"
            description = f"Rollback {service_name} from current version to stable release {target_version}."
            parameters = {"service_name": service_name, "target_version": target_version}
            fallback = "restart_service"
        elif "restart" in recommended:
            action = "restart_service"
            risk_level = "LOW"
            description = f"Restart {service_name} container instances to clear hung threads."
            parameters = {"service_name": service_name}
            fallback = "investigate_database"
        elif "database" in recommended or "connection" in recommended:
            # For database connection exhaustion (Scenario 2)
            action = "rollback"
            parameters = {"service_name": service_name, "target_version": "v2.3.9"}
            risk_level = "HIGH"
            description = f"Rollback {service_name} to v2.3.9 (Caution: DB connections remain saturated)."
            fallback = "terminate_idle_connections"
        else:
            action = "restart_service"
            risk_level = "LOW"
            description = f"Restart {service_name} service instances."
            parameters = {"service_name": service_name}
            fallback = "rollback"

        return RemediationPlan(
            action=action,
            risk_level=risk_level,
            target_service=service_name,
            description=description,
            parameters=parameters,
            reasoning=diagnosis.get("reasoning", root_cause),
            fallback_action=fallback
        )

    def get_fallback_plan(
        self,
        current_plan: RemediationPlan,
        reason_rejected_or_failed: str = "Human rejected the proposal or fix failed to recover system."
    ) -> RemediationPlan:
        """
        If human operator rejects the proposal (e.g., rejects HIGH-risk rollback),
        or if the action failed to restore service health, propose the next-best option.
        """
        service = current_plan.target_service
        
        if current_plan.action == "rollback":
            # If rollback was rejected or failed, next best option is soft restart or DB remediation
            return RemediationPlan(
                action="restart_service",
                risk_level="LOW",
                target_service=service,
                description=f"Fallback Option: Perform safe restart of {service} pods.",
                parameters={"service_name": service},
                reasoning=f"Previous plan '{current_plan.action}' was rejected or ineffective ({reason_rejected_or_failed}). A restart is low risk and may release local hung sockets.",
                fallback_action="escalate_to_human_sre"
            )
        elif current_plan.action == "escalate_and_enable_fallback":
            return RemediationPlan(
                action="rollback",
                risk_level="HIGH",
                target_service=service,
                description=f"Fallback Option: Roll back {service} to v2.4.0 as secondary mitigation.",
                parameters={"service_name": service, "target_version": "v2.4.0"},
                reasoning=f"Vendor escalation / provider fallback rejected or ineffective ({reason_rejected_or_failed}). Rolling back to test application layer.",
                fallback_action="escalate_to_human_sre"
            )
        elif current_plan.action == "failover_replica":
            return RemediationPlan(
                action="rollback",
                risk_level="HIGH",
                target_service=service,
                description=f"Fallback Option: Roll back {service} to v2.4.1 to rule out client-side changes.",
                parameters={"service_name": service, "target_version": "v2.4.1"},
                reasoning=f"Replica failover rejected or ineffective ({reason_rejected_or_failed}). Initiating rollback to test client layer.",
                fallback_action="escalate_to_human_sre"
            )
        else:
            # If restart was tried and failed, next best option is rollback
            return RemediationPlan(
                action="rollback",
                risk_level="HIGH",
                target_service=service,
                description=f"Fallback Option: Roll back {service} to previous release v2.3.9.",
                parameters={"service_name": service, "target_version": "v2.3.9"},
                reasoning=f"Restarting did not restore health ({reason_rejected_or_failed}). Outage likely requires full version regression.",
                fallback_action="escalate_to_human_sre"
            )
