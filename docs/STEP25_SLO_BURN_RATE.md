# BankOps — SLO Burn-Rate Alerting

## Objective
Implement and validate Prometheus multi-window burn-rate alerts
for a 99.9% availability SLO.

## Monitoring Configuration
- Application: BankOps FastAPI
- Metrics endpoint: /metrics
- Monitoring: Prometheus
- Visualization: Grafana
- Configuration: prometheus-values.yaml

## Permanent Alert Rules

| Alert | Threshold | Windows | Pending | Severity |
|---|---|---|---|---|
| BankOpsServerErrors | HTTP 5xx detected | 5m | 2m | Warning |
| BankOpsSLOFastBurn | 14.4x | 1h and 5m | 2m | Critical |
| BankOpsSLOSlowBurn | 6x | 6h and 30m | 5m | Warning |

Burn-rate calculations exclude /health and /metrics traffic.

## Testing Method
1. Deployed a temporary SRE testing image in bankops-helm-test.
2. Configured an isolated Prometheus scrape job.
3. Generated controlled HTTP 500 errors using /test-500.
4. Verified HTTP 5xx counters in Prometheus.
5. Observed alert state transitions in Prometheus.
6. Restored the original application image and monitoring configuration.

## Verified Results
- FastBurn alert reached FIRING.
- SlowBurn alert reached FIRING.
- FastBurn subsequently returned to INACTIVE.
- All three permanent alert rules passed promtool validation.
- Helm template validation passed.
- Main BankOps Prometheus scrape returned UP.

## Operational Notes
- Testing was isolated from the main BankOps application.
- Alertmanager notifications were disabled.
- Test alerts and temporary scrape configuration were removed.
- Evidence screenshots are retained in the project documentation.

## Outcome
Successfully implemented and tested SLO-based error-budget
monitoring using Prometheus and Kubernetes.
