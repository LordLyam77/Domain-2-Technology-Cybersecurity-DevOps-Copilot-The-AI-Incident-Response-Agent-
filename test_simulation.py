"""
Test script for Phase 1: Simulation Layer.

WHY THIS SCRIPT EXISTS:
This script allows you to verify that all simulation endpoints work as expected:
1. It reads the service status, logs, deploy history, and past incidents.
2. It tests state transitions (like rolling back) in both Scenario 1 and Scenario 2.
3. It prints clean, formatted output so you can visually verify the simulation.
"""

import json
from simulation.environment import (
    get_status,
    get_logs,
    get_deploys,
    get_past_incidents,
    get_metrics_timeline,
    rollback,
    restart_service,
    reset_environment
)


def print_section(title: str):
    print("\n" + "=" * 65)
    print(f" {title.upper()}")
    print("=" * 65)


def test_simulation():
    # -------------------------------------------------------------------------
    # TEST 1: Reset to Scenario 1 (Bad Deploy) & Check Initial Status
    # -------------------------------------------------------------------------
    print_section("1. Reset to Scenario 1 (Bad Deploy) & Check Status")
    reset_res = reset_environment("scenario_1")
    print("Reset Result:", json.dumps(reset_res, indent=2))

    status_before = get_status("payment-service")
    print("\nInitial Status of payment-service:")
    print(json.dumps(status_before, indent=2))
    assert status_before["status"] == "CRITICAL", "Initial status should be CRITICAL"
    assert status_before["current_version"] == "v2.4.0", "Current version should be v2.4.0"

    # -------------------------------------------------------------------------
    # TEST 2: Inspect Deploys (Find recent deployments)
    # -------------------------------------------------------------------------
    print_section("2. Inspect Deployments (get_deploys)")
    deploys = get_deploys("payment-service", limit=4)
    print(f"Found {len(deploys)} recent deployments:")
    for dep in deploys:
        print(f"  - [{dep['timestamp']}] {dep['version']} by {dep['author']}: '{dep['commit_msg']}'")
    assert len(deploys) >= 4, "Should have at least 4 deployments"

    # -------------------------------------------------------------------------
    # TEST 3: Inspect Logs (Check 500 errors and DB timeouts)
    # -------------------------------------------------------------------------
    print_section("3. Inspect Logs (get_logs - ERROR level)")
    error_logs = get_logs(service_name="payment-service", limit=6, level="ERROR")
    print(f"Fetched {len(error_logs)} recent ERROR logs:")
    for l in error_logs:
        print(f"  [{l['timestamp']}] [{l['level']}] {l['message']}")
    assert len(error_logs) > 0, "Should have error logs"

    # -------------------------------------------------------------------------
    # TEST 4: Query Past Incidents (Find similar postmortems)
    # -------------------------------------------------------------------------
    print_section("4. Query Past Incidents (get_past_incidents)")
    incidents = get_past_incidents(query="pool")
    print(f"Found {len(incidents)} past incidents mentioning 'pool':")
    for inc in incidents:
        print(f"  * Incident ID: {inc['id']}")
        print(f"    Title: {inc['title']}")
        print(f"    Root Cause: {inc['root_cause']}")
        print(f"    Resolution: {inc['resolution']}\n")
    assert len(incidents) >= 1, "Should find at least 1 incident matching 'pool'"

    # -------------------------------------------------------------------------
    # TEST 5: Action: Restart Service (Should not fix bad pool config)
    # -------------------------------------------------------------------------
    print_section("5. Action: Restart Service (restart_service)")
    restart_res = restart_service("payment-service")
    print("Restart Result:")
    print(json.dumps(restart_res, indent=2))
    assert restart_res["service_status"] == "CRITICAL", "Restart should not fix bad config"

    # -------------------------------------------------------------------------
    # TEST 6: Action: Rollback in Scenario 1 (Should fix and recover service)
    # -------------------------------------------------------------------------
    print_section("6. Action: Rollback in Scenario 1 (rollback)")
    rollback_res = rollback("payment-service", target_version="v2.3.9")
    print("Rollback Result:")
    print(json.dumps(rollback_res, indent=2))

    status_after = get_status("payment-service")
    print("\nStatus After Rollback:")
    print(json.dumps(status_after, indent=2))
    assert status_after["status"] == "HEALTHY", "Status should recover to HEALTHY"
    assert status_after["current_version"] == "v2.3.9", "Version should be v2.3.9"
    assert status_after["error_rate"] == "0.2%", "Error rate should drop to ~0.2%"

    # -------------------------------------------------------------------------
    # TEST 7: Scenario 2: Rollback Fails (Underlying Postgres connection exhaustion)
    # -------------------------------------------------------------------------
    print_section("7. Scenario 2: Fix Fails (Postgres Out of Connections)")
    reset_environment("scenario_2")
    status_s2 = get_status("payment-service")
    print("Scenario 2 Initial Status:")
    print(json.dumps(status_s2, indent=2))

    print("\nAttempting Rollback on Scenario 2...")
    rollback_s2 = rollback("payment-service", target_version="v2.3.9")
    print("Rollback Outcome on Scenario 2:")
    print(json.dumps(rollback_s2, indent=2))

    status_s2_after = get_status("payment-service")
    print("\nScenario 2 Status After Rollback:")
    print(json.dumps(status_s2_after, indent=2))
    assert status_s2_after["status"] == "CRITICAL", "In Scenario 2, rollback must NOT fix outage"
    assert "CONNECTIONS_EXHAUSTED" in status_s2_after["db_status"] or "CRITICAL" in status_s2_after["status"]

    # -------------------------------------------------------------------------
    # TEST 8: Timeline Metrics (Error-rate over time & event annotations)
    # -------------------------------------------------------------------------
    print_section("8. Error Rate Timeline Metrics (get_metrics_timeline)")
    reset_environment("scenario_1")
    timeline_before = get_metrics_timeline("payment-service")
    print(f"Pre-fix timeline points: {len(timeline_before)}")
    assert any("v2.4.0 deployed" in pt.get("event", "") for pt in timeline_before), "Timeline must annotate deploy event"

    rollback("payment-service", target_version="v2.3.9")
    timeline_after = get_metrics_timeline("payment-service")
    print(f"Post-fix timeline points: {len(timeline_after)}")
    assert len(timeline_after) > len(timeline_before), "Timeline must append post-fix recovery points"
    assert timeline_after[-1]["error_rate"] <= 0.2, "Final error rate must reflect recovery"

    # -------------------------------------------------------------------------
    # TEST 9: Scenario 3: Memory Leak (Restart clears leak & recovers)
    # -------------------------------------------------------------------------
    print_section("9. Scenario 3: Memory Leak (restart_service cures OOM)")
    reset_res_s3 = reset_environment("scenario_3")
    assert reset_res_s3["status"] == "success"
    
    status_s3 = get_status("payment-service")
    print("Scenario 3 Initial Status:")
    print(json.dumps(status_s3, indent=2))
    assert status_s3["status"] == "CRITICAL"
    assert "96" in status_s3.get("memory_pct", "")
    
    restart_s3 = restart_service("payment-service")
    print("\nScenario 3 Restart Outcome:")
    print(json.dumps(restart_s3, indent=2))
    assert restart_s3["success"] is True
    assert restart_s3["service_status"] == "HEALTHY"
    
    status_s3_after = get_status("payment-service")
    print("\nScenario 3 Status After Restart:")
    print(json.dumps(status_s3_after, indent=2))
    assert status_s3_after["status"] == "HEALTHY"
    assert status_s3_after["error_rate"] == "0.1%"
    assert status_s3_after["memory_usage_mb"] < 300

    # -------------------------------------------------------------------------
    # TEST 10: Scenario 4: Third-Party Outage (Do NOT roll back, escalate & fallback)
    # -------------------------------------------------------------------------
    print_section("10. Scenario 4: Third-Party Outage (escalate_and_enable_fallback)")
    from simulation.environment import escalate_and_enable_fallback
    reset_res_s4 = reset_environment("scenario_4")
    assert reset_res_s4["status"] == "success"

    status_s4 = get_status("payment-service")
    print("Scenario 4 Initial Status:")
    print(json.dumps(status_s4, indent=2))
    assert status_s4["status"] == "CRITICAL"
    assert status_s4["error_rate"] == "41.8%"
    assert status_s4["fallback_provider_enabled"] is False

    # Attempting rollback MUST fail because outage is third-party
    rb_fail = rollback("payment-service", target_version="v2.4.0")
    print("\nScenario 4 Ineffective Rollback Attempt:")
    print(json.dumps(rb_fail, indent=2))
    assert rb_fail["success"] is False
    assert rb_fail["service_status"] == "CRITICAL"

    # Attempting restart MUST fail as well
    rs_fail = restart_service("payment-service")
    assert rs_fail["success"] is False

    # escalate_and_enable_fallback cures the incident!
    fallback_res = escalate_and_enable_fallback("payment-service")
    print("\nScenario 4 Escalate & Enable Fallback Outcome:")
    print(json.dumps(fallback_res, indent=2))
    assert fallback_res["success"] is True
    assert fallback_res["service_status"] == "HEALTHY"

    status_s4_after = get_status("payment-service")
    assert status_s4_after["status"] == "HEALTHY"
    assert status_s4_after["error_rate"] == "0.8%"
    assert status_s4_after["fallback_provider_enabled"] is True

    # -------------------------------------------------------------------------
    # TEST 11: Scenario 5: Conflicting Evidence (failover_replica resolves)
    # -------------------------------------------------------------------------
    print_section("11. Scenario 5: Conflicting Evidence (failover_replica)")
    from simulation.environment import failover_replica
    reset_res_s5 = reset_environment("scenario_5")
    assert reset_res_s5["status"] == "success"

    status_s5 = get_status("payment-service")
    print("Scenario 5 Initial Status:")
    print(json.dumps(status_s5, indent=2))
    assert status_s5["status"] == "CRITICAL"
    assert status_s5["error_rate"] == "32.4%"
    assert status_s5["failing_node"] == "db-replica-02"
    assert status_s5["replica_nodes"]["db-replica-02"]["lag_seconds"] == 480.0

    # Ineffective Rollback attempt
    rb_fail_s5 = rollback("payment-service", target_version="v2.4.1")
    print("\nScenario 5 Ineffective Rollback Attempt:")
    print(json.dumps(rb_fail_s5, indent=2))
    assert rb_fail_s5["success"] is False
    assert rb_fail_s5["service_status"] == "CRITICAL"

    # Ineffective Restart attempt
    rs_fail_s5 = restart_service("payment-service")
    assert rs_fail_s5["success"] is False

    # Failover Replica cures the incident
    failover_res = failover_replica("payment-service", target_replica="db-replica-02")
    print("\nScenario 5 Failover Replica Outcome:")
    print(json.dumps(failover_res, indent=2))
    assert failover_res["success"] is True
    assert failover_res["service_status"] == "HEALTHY"

    status_s5_after = get_status("payment-service")
    print("\nScenario 5 Status After Failover:")
    print(json.dumps(status_s5_after, indent=2))
    assert status_s5_after["status"] == "HEALTHY"
    assert status_s5_after["error_rate"] == "0.2%"
    assert "DRAINED" in status_s5_after["failing_node"]

    print_section("ALL SIMULATION TESTS PASSED SUCCESSFULLY! (11/11)")


if __name__ == "__main__":
    test_simulation()


