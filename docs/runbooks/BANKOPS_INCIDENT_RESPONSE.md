# BankOps SRE Incident Response Runbook

## Environment
- Kubernetes context: kind-bankops
- Application namespace: bankops-gitops
- Application deployment: bankops-gitops-bankops-chart
- Database deployment: bankops-db
- Monitoring: Prometheus and Grafana

## 1. Alert Triage

### BankOpsSLOFastBurn (Critical)
- Acknowledge immediately.
- Check application error rate and latency.
- Check pod readiness, restarts and recent deployments.
- Escalate promptly if customer transactions are affected.

### BankOpsSLOSlowBurn (Warning)
- Investigate sustained error-budget consumption.
- Compare current and historical metrics.
- Identify recurring errors and plan corrective action.

### BankOpsServerErrors (Warning)
- Check HTTP 5xx metrics and application logs.
- Identify affected endpoints and error patterns.

## 2. Initial Diagnostics

Check application and database:

    kubectl -n bankops-gitops get deployments,pods,services

Check recent application logs:

    kubectl -n bankops-gitops logs deployment/bankops-gitops-bankops-chart --tail=100 --timestamps

Check previous container logs, when available:

    kubectl -n bankops-gitops logs deployment/bankops-gitops-bankops-chart --previous --tail=100 --timestamps

Check pod events and termination details:

    kubectl -n bankops-gitops describe pod <pod-name>

Check deployment history:

    kubectl -n bankops-gitops rollout history deployment/bankops-gitops-bankops-chart

## 3. Mitigation

- Identify whether the issue affects the application, database or infrastructure.
- Review recent code, image and configuration changes.
- If a deployment caused the incident, prepare a rollback to a known-good version.
- For this ArgoCD-managed application, prefer reverting the relevant Git change and synchronizing the application.
- Do not restart or delete pods without understanding the impact.
- Escalate database and infrastructure failures to the appropriate owner.

## 4. Recovery Verification

- Confirm deployments and pods are ready.
- Verify the /health endpoint.
- Check transaction-processing functionality.
- Confirm Prometheus target availability (up == 1).
- Verify HTTP 5xx error rate has returned to an acceptable level.
- Confirm FastBurn and SlowBurn alerts have resolved.
- Continue monitoring for recurrence.

## 5. Incident Closure and RCA

Record:
- Incident start and recovery times
- Severity and customer impact
- Alert and affected components
- Timeline and investigation evidence
- Confirmed root cause or explicitly unknown cause
- Mitigation and recovery actions
- Corrective and preventive actions
- Follow-up owner and due date

## 6. Investigation Example — 12 November 2026

Observed:
- BankOps application and PostgreSQL both terminated at 05:43:40 UTC.
- Both reported termination reason Unknown and exit code 255.
- Application and database subsequently recovered.
- Both deployments were healthy during investigation.

Assessment:
- Simultaneous termination suggests a shared infrastructure interruption.
- Exact root cause remains unconfirmed.
- No further disruptive action was required.

## 7. Correlate metrics, logs and traces

- In Prometheus, check `up{job="bankops"}`, request rate, 5xx ratio, latency and burn-rate alerts.
- In Grafana Explore, query Loki with `{namespace="bankops-gitops"}`; narrow time range and filter relevant errors.
- In Tempo, search for service bankops and open relevant Trace IDs to inspect span duration and attributes. Correlate using time, endpoint and trace ID where available; do not assume every log contains a trace ID.
- Compare telemetry with deployment history and Kubernetes events. Missing telemetry is not proof of no incident.

## 8. Argo CD comparison error / internal DNS timeout

Start with read-only checks:

```bash
kubectl get applications -n argocd
kubectl get application bankops-gitops -n argocd -o jsonpath='{.status.conditions}'
kubectl get pods -n argocd -o wide
kubectl get svc argocd-repo-server -n argocd
kubectl get endpointslices -n argocd -l kubernetes.io/service-name=argocd-repo-server
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide
kubectl logs -n kube-system deployment/coredns --tail=100
```

Unknown sync and Healthy health can coexist: inability to generate target manifests does not establish an application outage. Check internal DNS and TCP connectivity from the affected workload, service endpoints, node networking and kube-proxy before escalating. Capture evidence before restarting.

If justified, roll out a targeted restart of the affected Argo CD component; CoreDNS restart can temporarily affect cluster-wide resolution. In this local Kind lab, Docker Desktop restart is a last-resort recovery action with possible downtime for all workloads. Never factory-reset or delete the cluster as a routine recovery step. Verify nodes, workloads, application sync, transaction retrieval and telemetry afterward.

On 25 November 2026, reconciliation recovered to Synced/Healthy after Docker Desktop recovery; the exact underlying cause was not confirmed. See [validation evidence](../FINAL_VALIDATION.md).

## 9. Database backup and recovery

Before any destructive database recovery, preserve the current state and obtain approval. In the lab, a logical backup can be created outside the repository:

```bash
mkdir -p ~/bankops-backups
(umask 077; kubectl exec -n bankops-gitops deploy/bankops-db -- pg_dump -U bankops_app -d bankops -Fc > ~/bankops-backups/bankops-$(date +%F).dump)
```

Use a unique filename if running more than once per day; check command exit status and file size. Inspect the archive catalog with pg_restore --list. Do not expose passwords or commit dump files. A logical backup does not include all cluster-wide roles or configuration.

Restore testing should target a separate disposable PostgreSQL instance, not the live database. Verify schema, row counts and known synthetic transaction records; measure restoration time. Define RPO/RTO and offsite retention before production use. Actual restore is outstanding.

## 10. Communication and escalation

Record impact, severity, incident owner, latest verified state, next action and update cadence. Escalate infrastructure, application or database faults to the corresponding owner. Preserve evidence and document unknowns. Close only after recovery checks and monitoring; assign corrective action owners and dates. This local lab has no formal on-call organization or customer SLA.
