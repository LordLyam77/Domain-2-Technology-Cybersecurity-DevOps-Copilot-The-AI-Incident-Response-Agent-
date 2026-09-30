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

    print_section("ALL SIMULATION TESTS PASSED SUCCESSFULLY! (7/7)")


if __name__ == "__main__":
    test_simulation()
