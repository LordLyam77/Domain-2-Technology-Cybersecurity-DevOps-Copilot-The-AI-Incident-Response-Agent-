"""
Helper script to generate scenario_1_bad_deploy.json and scenario_2_fix_fails.json
with 70-80 realistic log lines, deploy history, and environment states.
"""
import json
import os

data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)

# -------------------------------------------------------------
# Scenario 1: Bad Deploy
# -------------------------------------------------------------
# Healthy logs from 13:48 to 14:01
# Deploy at 14:02:00 (v2.4.0)
# Errors from 14:03:00 to 14:15:00
scenario_1_logs = []

# Normal logs before 14:02
healthy_endpoints = [
    ("13:48:12", "INFO", "payment-service", "GET /health 200 OK - latency: 12ms"),
    ("13:48:45", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_9912 amount=45.00 USD status=200 OK"),
    ("13:49:10", "INFO", "payment-service", "GET /metrics 200 OK - pool_active=4 pool_idle=46"),
    ("13:50:02", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_8831 amount=120.50 USD status=200 OK"),
    ("13:51:22", "INFO", "payment-service", "POST /api/v1/refund - refund_id=ref_1012 status=200 OK"),
    ("13:52:05", "INFO", "payment-service", "GET /health 200 OK - latency: 14ms"),
    ("13:53:18", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_4411 amount=19.99 USD status=200 OK"),
    ("13:54:33", "INFO", "payment-service", "GET /metrics 200 OK - pool_active=6 pool_idle=44"),
    ("13:55:01", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_7721 amount=89.00 USD status=200 OK"),
    ("13:56:40", "INFO", "payment-service", "GET /health 200 OK - latency: 11ms"),
    ("13:57:15", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_3342 amount=250.00 USD status=200 OK"),
    ("13:58:20", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_6619 amount=15.00 USD status=200 OK"),
    ("13:59:05", "INFO", "payment-service", "GET /metrics 200 OK - pool_active=5 pool_idle=45"),
    ("14:00:12", "INFO", "payment-service", "GET /health 200 OK - latency: 13ms"),
    ("14:01:05", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_1120 amount=65.20 USD status=200 OK"),
    ("14:01:45", "INFO", "payment-service", "Incoming SIGTERM for rolling upgrade to v2.4.0"),
]

for t, lvl, svc, msg in healthy_endpoints:
    scenario_1_logs.append({
        "timestamp": f"2026-09-30T{t}Z",
        "level": lvl,
        "service": svc,
        "message": msg
    })

# Deploy event logs
deploy_logs = [
    ("14:02:00", "INFO", "deployer", "Starting rolling deployment of payment-service:v2.4.0"),
    ("14:02:15", "INFO", "payment-service", "Applying configuration: max_connection_pool=10, connection_timeout_ms=1000"),
    ("14:02:22", "INFO", "payment-service", "Container started. Listening on :8080. Version v2.4.0"),
    ("14:02:30", "INFO", "deployer", "Deployment completed for payment-service:v2.4.0. Traffic cutover 100%."),
]
for t, lvl, svc, msg in deploy_logs:
    scenario_1_logs.append({
        "timestamp": f"2026-09-30T{t}Z",
        "level": lvl,
        "service": svc,
        "message": msg
    })

# Error spike logs (14:03 to 14:15)
error_patterns = [
    ("14:03:02", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_9011 amount=34.00 USD status=200 OK"),
    ("14:03:15", "WARN", "payment-service", "Connection pool capacity reaching threshold (9/10 allocated)"),
    ("14:03:28", "WARN", "payment-service", "Connection acquisition took 850ms (threshold: 500ms)"),
    ("14:03:45", "ERROR", "payment-service", "ConnectionPoolExhaustedException: Timeout waiting for idle connection in pool (max=10, active=10, waiters=4)"),
    ("14:03:46", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:04:02", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:04:10", "WARN", "payment-service", "GET /health 500 Internal Server Error - db ping failed: connection timeout"),
    ("14:04:18", "ERROR", "payment-service", "ConnectionPoolExhaustedException: pool size 10 exceeded, request queued > 1000ms"),
    ("14:04:30", "ERROR", "payment-service", "POST /api/v1/refund 500 Internal Server Error - database connection timeout"),
    ("14:05:01", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:05:15", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_5512 amount=10.00 USD status=200 OK"),
    ("14:05:22", "ERROR", "payment-service", "ConnectionPoolExhaustedException: Timeout waiting for idle connection in pool (active=10/10)"),
    ("14:05:35", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:06:00", "WARN", "payment-service", "GET /metrics 200 OK - pool_active=10 pool_idle=0 pool_waiters=12"),
    ("14:06:12", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:06:33", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:07:05", "ERROR", "payment-service", "POST /api/v1/refund 500 Internal Server Error - database connection timeout"),
    ("14:07:22", "ERROR", "payment-service", "ConnectionPoolExhaustedException: pool size 10 exceeded"),
    ("14:07:44", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:08:10", "ERROR", "payment-service", "GET /health 500 Internal Server Error - db ping failed: connection timeout"),
    ("14:08:35", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:09:02", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_2234 amount=5.00 USD status=200 OK"),
    ("14:09:20", "ERROR", "payment-service", "ConnectionPoolExhaustedException: pool size 10 exceeded"),
    ("14:09:48", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:10:15", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:10:40", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:11:05", "WARN", "payment-service", "GET /metrics 200 OK - pool_active=10 pool_idle=0 pool_waiters=18"),
    ("14:11:32", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:12:01", "ERROR", "payment-service", "POST /api/v1/refund 500 Internal Server Error - database connection timeout"),
    ("14:12:28", "ERROR", "payment-service", "ConnectionPoolExhaustedException: pool size 10 exceeded"),
    ("14:12:55", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:13:19", "ERROR", "payment-service", "GET /health 500 Internal Server Error - db ping failed: connection timeout"),
    ("14:13:42", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:14:05", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:14:30", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:14:55", "ERROR", "payment-service", "ConnectionPoolExhaustedException: pool size 10 exceeded"),
    ("14:15:10", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:15:18", "ERROR", "payment-service", "Connection acquisition attempt timed out after 1000ms"),
    ("14:15:25", "ERROR", "payment-service", "POST /api/v1/refund 500 Internal Server Error - database connection timeout"),
    ("14:15:30", "WARN", "alertmanager", "ALERT firing: PaymentServiceHigh5xxErrorRate (rate > 40%)"),
    ("14:15:45", "WARN", "alertmanager", "ALERT firing: PaymentServiceDatabaseConnectionTimeouts (count > 50 in 10m)"),
    ("14:15:50", "ERROR", "payment-service", "GET /health 500 Internal Server Error - db ping failed: connection timeout"),
    ("14:16:02", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:16:15", "ERROR", "payment-service", "ConnectionPoolExhaustedException: pool size 10 exceeded"),
    ("14:16:30", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:16:45", "WARN", "ingress-controller", "Upstream server returned 500 for host payment.internal"),
    ("14:17:00", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout")
]

for t, lvl, svc, msg in error_patterns:
    scenario_1_logs.append({
        "timestamp": f"2026-09-30T{t}Z",
        "level": lvl,
        "service": svc,
        "message": msg
    })

scenario_1_deploys = [
    {
        "deploy_id": "dep-491",
        "version": "v2.3.7",
        "service": "payment-service",
        "timestamp": "2026-09-28T09:15:00Z",
        "author": "alice@company.com",
        "commit_hash": "a7e10c2",
        "commit_msg": "Fix currency rounding issue in checkout calculation",
        "status": "SUCCESS"
    },
    {
        "deploy_id": "dep-492",
        "version": "v2.3.8",
        "service": "payment-service",
        "timestamp": "2026-09-29T11:30:00Z",
        "author": "bob@company.com",
        "commit_hash": "f4c99b1",
        "commit_msg": "Add metric logging for checkout conversion funnel",
        "status": "SUCCESS"
    },
    {
        "deploy_id": "dep-493",
        "version": "v2.3.9",
        "service": "payment-service",
        "timestamp": "2026-09-30T10:00:00Z",
        "author": "carol@company.com",
        "commit_hash": "3d9a184",
        "commit_msg": "Bump dependencies and update stripe-sdk version",
        "status": "SUCCESS"
    },
    {
        "deploy_id": "dep-494",
        "version": "v2.4.0",
        "service": "payment-service",
        "timestamp": "2026-09-30T14:02:00Z",
        "author": "dave@company.com",
        "commit_hash": "9b8e21a",
        "commit_msg": "Updated DB connection pool config to tune memory usage (reduced pool size to 10)",
        "status": "DEPLOYED"
    }
]

scenario_1_data = {
    "scenario_id": "scenario_1_bad_deploy",
    "title": "Scenario 1: Bad Deploy (Configuration Regression)",
    "description": "Payment service degraded after v2.4.0 deploy due to DB connection pool misconfiguration. Rollback fixes it.",
    "service_name": "payment-service",
    "initial_state": {
        "status": "CRITICAL",
        "current_version": "v2.4.0",
        "previous_version": "v2.3.9",
        "healthy_version": "v2.3.9",
        "error_rate": "43.5%",
        "avg_latency_ms": 1150,
        "active_db_connections": 10,
        "max_db_connections": 10,
        "db_status": "ONLINE",
        "uptime_seconds": 840,
        "last_updated": "2026-09-30T14:16:00Z"
    },
    "deploys": scenario_1_deploys,
    "logs": scenario_1_logs
}

with open(os.path.join(data_dir, "scenario_1_bad_deploy.json"), "w") as f:
    json.dump(scenario_1_data, f, indent=2)

# -------------------------------------------------------------
# Scenario 2: Fix Fails (Underlying DB issue, rollback won't fix)
# -------------------------------------------------------------
scenario_2_logs = []

# Normal logs before 14:00
scenario_2_pre = [
    ("13:48:00", "INFO", "payment-service", "GET /health 200 OK - latency: 15ms"),
    ("13:49:12", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_1001 amount=22.00 USD status=200 OK"),
    ("13:50:30", "INFO", "postgres-primary", "PostgreSQL database autovacuum finished on table payments"),
    ("13:51:15", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_1002 amount=85.00 USD status=200 OK"),
    ("13:52:40", "INFO", "payment-service", "GET /metrics 200 OK - active_pool=12 idle_pool=38"),
    ("13:53:20", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_1003 amount=110.00 USD status=200 OK"),
    ("13:54:10", "INFO", "payment-service", "GET /health 200 OK - latency: 14ms"),
    ("13:55:00", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_1004 amount=45.00 USD status=200 OK"),
    ("13:56:15", "WARN", "postgres-primary", "Postgres active connection count reached 420/500"),
    ("13:57:30", "WARN", "postgres-primary", "Unterminated client connections detected from analytics-batch-job"),
    ("13:58:10", "WARN", "postgres-primary", "Postgres active connection count reached 480/500"),
    ("13:59:00", "INFO", "payment-service", "POST /api/v1/charge - customer_id=cus_1005 amount=18.50 USD status=200 OK"),
    ("14:00:20", "WARN", "postgres-primary", "Connection count reached 498/500. Remaining 2 slots reserved for superuser."),
    ("14:01:05", "INFO", "payment-service", "Incoming SIGTERM for routine maintenance deploy v2.4.0"),
    ("14:02:00", "INFO", "deployer", "Starting rolling deployment of payment-service:v2.4.0"),
    ("14:02:18", "INFO", "payment-service", "Container started. Listening on :8080. Version v2.4.0"),
    ("14:02:30", "INFO", "deployer", "Deployment completed for payment-service:v2.4.0"),
]
for t, lvl, svc, msg in scenario_2_pre:
    scenario_2_logs.append({
        "timestamp": f"2026-09-30T{t}Z",
        "level": lvl,
        "service": svc,
        "message": msg
    })

# Scenario 2 errors - DB max connections exhausted!
scenario_2_errs = [
    ("14:03:00", "FATAL", "postgres-primary", "FATAL: remaining connection slots are reserved for non-replication superuser connections"),
    ("14:03:02", "ERROR", "payment-service", "psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections"),
    ("14:03:03", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:03:15", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:03:25", "ERROR", "payment-service", "GET /health 500 Internal Server Error - database connection timeout"),
    ("14:03:40", "FATAL", "postgres-primary", "FATAL: too many connections for role 'payment_app' (current: 500, max: 500)"),
    ("14:03:55", "ERROR", "payment-service", "POST /api/v1/refund 500 Internal Server Error - database connection timeout"),
    ("14:04:10", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:04:22", "FATAL", "postgres-primary", "FATAL: remaining connection slots are reserved for non-replication superuser connections"),
    ("14:04:35", "ERROR", "payment-service", "Connection acquisition timed out after 5000ms. Database server rejected connection request."),
    ("14:04:50", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:05:05", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:05:20", "ERROR", "payment-service", "GET /health 500 Internal Server Error - database connection timeout"),
    ("14:05:40", "FATAL", "postgres-primary", "FATAL: too many connections for role 'payment_app' (current: 500, max: 500)"),
    ("14:06:00", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:06:15", "ERROR", "payment-service", "POST /api/v1/refund 500 Internal Server Error - database connection timeout"),
    ("14:06:30", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:06:50", "FATAL", "postgres-primary", "FATAL: remaining connection slots are reserved for non-replication superuser connections"),
    ("14:07:10", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:07:30", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:07:55", "ERROR", "payment-service", "GET /health 500 Internal Server Error - database connection timeout"),
    ("14:08:15", "FATAL", "postgres-primary", "FATAL: too many connections for role 'payment_app' (current: 500, max: 500)"),
    ("14:08:35", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:08:50", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:09:10", "FATAL", "postgres-primary", "FATAL: remaining connection slots are reserved for non-replication superuser connections"),
    ("14:09:30", "ERROR", "payment-service", "POST /api/v1/refund 500 Internal Server Error - database connection timeout"),
    ("14:09:55", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:10:15", "ERROR", "payment-service", "GET /health 500 Internal Server Error - database connection timeout"),
    ("14:10:40", "FATAL", "postgres-primary", "FATAL: too many connections for role 'payment_app' (current: 500, max: 500)"),
    ("14:11:00", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:11:25", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:11:50", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:12:15", "FATAL", "postgres-primary", "FATAL: remaining connection slots are reserved for non-replication superuser connections"),
    ("14:12:40", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:13:00", "ERROR", "payment-service", "GET /health 500 Internal Server Error - database connection timeout"),
    ("14:13:25", "ERROR", "payment-service", "POST /api/v1/refund 500 Internal Server Error - database connection timeout"),
    ("14:13:50", "FATAL", "postgres-primary", "FATAL: too many connections for role 'payment_app' (current: 500, max: 500)"),
    ("14:14:10", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:14:35", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:14:45", "FATAL", "postgres-primary", "FATAL: remaining connection slots are reserved for non-replication superuser connections"),
    ("14:14:50", "ERROR", "payment-service", "POST /api/v1/refund 500 Internal Server Error - database connection timeout"),
    ("14:15:00", "WARN", "alertmanager", "ALERT firing: PaymentServiceHigh5xxErrorRate (rate > 50%)"),
    ("14:15:15", "WARN", "alertmanager", "ALERT firing: PostgresDatabaseConnectionsExhausted (active: 500/500)"),
    ("14:15:30", "ERROR", "payment-service", "GET /health 500 Internal Server Error - database connection timeout"),
    ("14:15:45", "FATAL", "postgres-primary", "FATAL: too many connections for role 'payment_app' (current: 500, max: 500)"),
    ("14:16:00", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:16:15", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout"),
    ("14:16:30", "ERROR", "payment-service", "psycopg2.OperationalError: server closed the connection unexpectedly"),
    ("14:16:45", "ERROR", "payment-service", "POST /api/v1/charge 500 Internal Server Error - database connection timeout")
]
for t, lvl, svc, msg in scenario_2_errs:
    scenario_2_logs.append({
        "timestamp": f"2026-09-30T{t}Z",
        "level": lvl,
        "service": svc,
        "message": msg
    })

scenario_2_deploys = [
    {
        "deploy_id": "dep-491",
        "version": "v2.3.7",
        "service": "payment-service",
        "timestamp": "2026-09-28T09:15:00Z",
        "author": "alice@company.com",
        "commit_hash": "a7e10c2",
        "commit_msg": "Fix currency rounding issue in checkout calculation",
        "status": "SUCCESS"
    },
    {
        "deploy_id": "dep-492",
        "version": "v2.3.8",
        "service": "payment-service",
        "timestamp": "2026-09-29T11:30:00Z",
        "author": "bob@company.com",
        "commit_hash": "f4c99b1",
        "commit_msg": "Add metric logging for checkout conversion funnel",
        "status": "SUCCESS"
    },
    {
        "deploy_id": "dep-493",
        "version": "v2.3.9",
        "service": "payment-service",
        "timestamp": "2026-09-30T10:00:00Z",
        "author": "carol@company.com",
        "commit_hash": "3d9a184",
        "commit_msg": "Bump dependencies and update stripe-sdk version",
        "status": "SUCCESS"
    },
    {
        "deploy_id": "dep-494",
        "version": "v2.4.0",
        "service": "payment-service",
        "timestamp": "2026-09-30T14:02:00Z",
        "author": "emma@company.com",
        "commit_hash": "11fa23e",
        "commit_msg": "Refactor async payment receipt email dispatcher",
        "status": "DEPLOYED"
    }
]

scenario_2_data = {
    "scenario_id": "scenario_2_fix_fails",
    "title": "Scenario 2: Fix Fails (Underlying DB Exhaustion)",
    "description": "Payment service degraded, coincides with deploy v2.4.0, but root cause is PostgreSQL running out of connection slots. Rollback will NOT recover service.",
    "service_name": "payment-service",
    "initial_state": {
        "status": "CRITICAL",
        "current_version": "v2.4.0",
        "previous_version": "v2.3.9",
        "healthy_version": "NONE",
        "error_rate": "54.8%",
        "avg_latency_ms": 2800,
        "active_db_connections": 500,
        "max_db_connections": 500,
        "db_status": "CONNECTIONS_EXHAUSTED",
        "uptime_seconds": 840,
        "last_updated": "2026-09-30T14:16:00Z"
    },
    "deploys": scenario_2_deploys,
    "logs": scenario_2_logs
}

with open(os.path.join(data_dir, "scenario_2_fix_fails.json"), "w") as f:
    json.dump(scenario_2_data, f, indent=2)

print("Generated scenario_1_bad_deploy.json and scenario_2_fix_fails.json successfully!")
print(f"Scenario 1 log count: {len(scenario_1_logs)}")
print(f"Scenario 2 log count: {len(scenario_2_logs)}")
