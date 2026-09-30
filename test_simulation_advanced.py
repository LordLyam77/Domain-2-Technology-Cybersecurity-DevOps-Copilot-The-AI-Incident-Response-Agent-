"""
Advanced Unit & Lifecycle Tests for Simulation & Backend Layer.

Tests:
1. Scenario 1: Bad Deploy -> Rollback -> Verification Succeeded
2. Scenario 2: Fix Fails -> Rollback Fails -> Secondary Investigation & Remediation -> Verification Succeeded
3. Scenario 3: Memory Leak -> Pod Restart Flushes Heap -> Verification Succeeded
4. Scenario 4: Third-Party Outage -> Rollback Fails -> Fallback Enabled -> Verification Succeeded
5. Scenario 5: Conflicting Evidence -> Rollback Fails -> Replica Failover -> Verification Succeeded
6. Verification Engine: verify_remediation() before action, after failed action, after successful action
7. Defensive Edge Cases: Unknown scenario fallback, negative limits, repeated actions, idempotency
8. State Lifecycle & Reset Determinism: Repeatable resets restore clean state
"""

import json
import unittest
from simulation.environment import (
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


class TestSimulationBackend(unittest.TestCase):

    def setUp(self):
        # Reset to clean state before each test
        reset_environment("scenario_1")

    def test_scenario_1_lifecycle(self):
        """Scenario 1: Bad deploy rollback cures pool misconfiguration."""
        reset_res = reset_environment("scenario_1")
        self.assertEqual(reset_res["status"], "success")

        # Initial vital signs
        status_0 = get_status("payment-service")
        self.assertEqual(status_0["status"], "CRITICAL")
        self.assertEqual(status_0["current_version"], "v2.4.0")
        self.assertEqual(status_0["max_db_connections"], 10)

        # Inspect evidence
        logs = get_logs("payment-service", level="ERROR")
        self.assertTrue(len(logs) > 0)
        self.assertTrue(any("ConnectionPool" in l["message"] for l in logs))

        deploys = get_deploys("payment-service", limit=3)
        self.assertEqual(deploys[0]["version"], "v2.4.0")

        # Execute remediation: rollback to v2.3.9
        rb = rollback("payment-service", target_version="v2.3.9")
        self.assertTrue(rb["success"])
        self.assertEqual(rb["service_status"], "HEALTHY")

        # Verify remediation engine
        v = verify_remediation()
        self.assertEqual(v["verdict"], "SUCCESS")
        self.assertTrue(v["recovered"])
        self.assertEqual(v["service_status"], "HEALTHY")
        self.assertEqual(v["error_rate"], "0.2%")
        self.assertEqual(v["subsystem_checks"]["database"], "HEALTHY: Connections pool normal (8/50)")

    def test_scenario_2_two_phase_remediation(self):
        """Scenario 2: Rollback fails to clear DB exhaustion -> Secondary DB remediation succeeds."""
        reset_environment("scenario_2")

        status_0 = get_status("payment-service")
        self.assertEqual(status_0["status"], "CRITICAL")
        self.assertEqual(status_0["db_status"], "CONNECTIONS_EXHAUSTED")
        self.assertEqual(status_0["active_db_connections"], 500)

        # Phase 1: Rollback attempt
        rb = rollback("payment-service", target_version="v2.3.9")
        self.assertFalse(rb["success"])
        self.assertEqual(rb["service_status"], "CRITICAL")

        # Verification after Phase 1 MUST report FAILED
        v1 = verify_remediation()
        self.assertEqual(v1["verdict"], "FAILED")
        self.assertFalse(v1["recovered"])
        self.assertIn("CRITICAL", v1["subsystem_checks"]["database"])

        # Phase 2: Secondary remediation (pod restart drops hung client sockets & resets pool)
        sec_restart = restart_service("payment-service")
        self.assertTrue(sec_restart["success"])
        self.assertEqual(sec_restart["service_status"], "HEALTHY")

        # Verification after Phase 2 MUST report SUCCESS
        v2 = verify_remediation()
        self.assertEqual(v2["verdict"], "SUCCESS")
        self.assertTrue(v2["recovered"])
        self.assertEqual(v2["error_rate"], "0.2%")
        self.assertIn("HEALTHY", v2["subsystem_checks"]["database"])

    def test_scenario_3_memory_leak(self):
        """Scenario 3: Long uptime causes heap saturation -> Restart flushes memory."""
        reset_environment("scenario_3")

        status_0 = get_status("payment-service")
        self.assertEqual(status_0["status"], "CRITICAL")
        self.assertEqual(status_0["uptime_seconds"], 432000)
        self.assertEqual(status_0["memory_pct"], "96.1%")

        # Restart flushes heap
        rs = restart_service("payment-service")
        self.assertTrue(rs["success"])
        self.assertEqual(rs["service_status"], "HEALTHY")

        status_1 = get_status("payment-service")
        self.assertEqual(status_1["status"], "HEALTHY")
        self.assertEqual(status_1["memory_pct"], "11.7%")
        self.assertEqual(status_1["memory_usage_mb"], 240)

        v = verify_remediation()
        self.assertEqual(v["verdict"], "SUCCESS")
        self.assertTrue(v["recovered"])
        self.assertIn("HEALTHY", v["subsystem_checks"]["memory"])

    def test_scenario_4_third_party_vendor_outage(self):
        """Scenario 4: Upstream vendor 504 -> Rollback fails -> Fallback provider recovers."""
        reset_environment("scenario_4")

        status_0 = get_status("payment-service")
        self.assertEqual(status_0["status"], "CRITICAL")
        self.assertFalse(status_0["fallback_provider_enabled"])

        # Ineffective rollback
        rb = rollback("payment-service", target_version="v2.4.0")
        self.assertFalse(rb["success"])
        self.assertEqual(rb["service_status"], "CRITICAL")
        
        v_rb = verify_remediation()
        self.assertEqual(v_rb["verdict"], "FAILED")

        # Ineffective restart
        rs = restart_service("payment-service")
        self.assertFalse(rs["success"])

        # Effective remediation: enable standby fallback provider
        fb = escalate_and_enable_fallback("payment-service")
        self.assertTrue(fb["success"])
        self.assertEqual(fb["service_status"], "HEALTHY")

        status_1 = get_status("payment-service")
        self.assertTrue(status_1["fallback_provider_enabled"])
        self.assertEqual(status_1["error_rate"], "0.8%")

        v_fb = verify_remediation()
        self.assertEqual(v_fb["verdict"], "SUCCESS")
        self.assertTrue(v_fb["recovered"])
        self.assertIn("bypassed", v_fb["subsystem_checks"]["external_dependencies"].lower())

    def test_scenario_5_conflicting_evidence(self):
        """Scenario 5: Superficially implicates deploy -> True root cause is lagging replica."""
        reset_environment("scenario_5")

        status_0 = get_status("payment-service")
        self.assertEqual(status_0["status"], "CRITICAL")
        self.assertEqual(status_0["failing_node"], "db-replica-02")

        # Rollback fails to clear replica lag
        rb = rollback("payment-service", target_version="v2.4.1")
        self.assertFalse(rb["success"])
        self.assertEqual(rb["service_status"], "CRITICAL")

        # Failover replica resolves stale reads
        fo = failover_replica("payment-service", target_replica="db-replica-02")
        self.assertTrue(fo["success"])
        self.assertEqual(fo["service_status"], "HEALTHY")

        status_1 = get_status("payment-service")
        self.assertIn("DRAINED", status_1["failing_node"])
        self.assertEqual(status_1["error_rate"], "0.2%")

        v = verify_remediation()
        self.assertEqual(v["verdict"], "SUCCESS")
        self.assertTrue(v["recovered"])
        self.assertIn("HEALTHY", v["subsystem_checks"]["replica_health"])

    def test_defensive_edge_cases(self):
        """Test edge cases: unknown scenarios, negative limits, repeated actions."""
        # Unknown scenario gracefully falls back to scenario_1
        res = reset_environment("scenario_unknown_999")
        self.assertEqual(res["status"], "success")

        # Negative limit in get_logs
        logs = get_logs("payment-service", limit=-5)
        self.assertEqual(logs, [])

        # Unknown log level returns empty list
        logs_none = get_logs("payment-service", level="NONEXISTENT_LEVEL")
        self.assertEqual(logs_none, [])

        # Search past incidents with query
        hits = get_past_incidents(query="pg_terminate_backend")
        self.assertTrue(len(hits) >= 1)
        self.assertEqual(hits[0]["id"], "INC-650")

        # Repeated rollback calls do not crash
        rb1 = rollback("payment-service")
        rb2 = rollback("payment-service")
        self.assertIsNotNone(rb2)
        self.assertTrue(len(get_action_history()) >= 2)

    def test_clean_lifecycle_state_and_reset(self):
        """Test state transitions: RESET -> HEALTHY -> TRIGGER_ALERT -> INCIDENT -> VERIFY."""
        env = get_environment()
        
        # Reset with start_in_incident=False
        env.reset_environment("scenario_1", start_in_incident=False)
        self.assertEqual(env.lifecycle_state, "HEALTHY")
        st_healthy = env.get_status()
        self.assertEqual(st_healthy["status"], "HEALTHY")
        self.assertEqual(st_healthy["error_rate"], "0.1%")

        # Trigger incident
        env.trigger_incident()
        self.assertEqual(env.lifecycle_state, "INCIDENT")
        st_incident = env.get_status()
        self.assertEqual(st_incident["status"], "CRITICAL")
        self.assertEqual(st_incident["error_rate"], "43.5%")

        # Verification before any action
        v_pre = env.verify_remediation()
        self.assertEqual(v_pre["verdict"], "NO_ACTION_TAKEN")


if __name__ == "__main__":
    unittest.main()
