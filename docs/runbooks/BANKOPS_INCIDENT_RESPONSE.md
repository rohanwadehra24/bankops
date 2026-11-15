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
