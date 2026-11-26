# BankOps capstone validation — 24–26 November 2026

Scope: observed local-lab results and historical exercise evidence, not a production certification. Architecture presentation and interview assessment are deferred to live mock interviews. No new application or deployment configuration changes are included in this documentation update.

## 24 November — operational readiness review

| Check | Observed result |
|---|---|
| Application and database | Both deployments ready; services and backend endpoints present |
| Functional request | Internal GET /health returned ok; GITOPS-TXN-001 retrieved with PROCESSED and REVIEW |
| Request SLI | 100% non-5xx requests in observed 24-hour Prometheus window |
| Error budget | 0% consumed relative to 99.9% target in that measured window |
| Alerts | BankOpsServerErrors, BankOpsSLOFastBurn, BankOpsSLOSlowBurn inactive at inspection |
| RBAC | Default service account reviewed; no workload/Secret permissions observed in namespace review |
| Secrets | Database password referenced via Kubernetes Secret; no secret values included here |
| Backup | PostgreSQL custom-format pg_dump created outside repository; 2.2 KiB, mode 600; archive catalog inspected |

The SLI is request-based, includes observed handlers and does not measure downtime when no requests reach the application. A single 24-hour measurement is not proof of a longer-window SLO or continuous uptime.

## 25 November — CI/CD, GitOps and Kubernetes

- Reviewed CI and manual Helm CD workflow definitions. Historical GitHub Actions runs showed successful CI and local Helm deployment; no new workflow was triggered for validation.
- Argo CD initially reported Unknown/Healthy with a ComparisonError: DNS lookup of argocd-repo-server via 10.96.0.10:53 timed out. A separate TCP connection error to the repository service was also reported.
- Restarting Argo CD deployments and application controller did not immediately recover reconciliation. Synced/Healthy was observed after the Docker Desktop recovery step. Local networking is a suspected failure domain, not a confirmed root cause. CoreDNS restart execution was not independently established.
- BankOps and PostgreSQL deployments each 1/1 available; Pods Running/Ready; services on ports 8000 and 5432; GitOps PVC Bound (1 Gi, RWO); HPA 3% CPU utilization against 60% target, 1 replica, range 1–3.
- Helm test release bankops-test in bankops-helm-test: deployed revision 10. This is release metadata, not a fresh endpoint test.

## 26 November — observability and recovery

| Check | Observed result |
|---|---|
| Monitoring Pods | All 14 listed Pods Running and fully ready |
| Prometheus | up{job="bankops"} returned 1 |
| Grafana | User confirmed request rate, error, P95/P99 latency and availability/SLO panels visible and displaying data |
| Loki | Namespace query returned 150 INFO log entries in last 15 min; visible /health and /metrics requests HTTP 200 |
| Tempo | Recent bankops GET /health and GET /metrics traces visible; sampled durations 1–2 ms |
| Helm history | 10 revisions: 1 install, 4 upgrades, 5 rollbacks; revision 10 deployed from revision 6 |
| Backup | 24 November dump still present, mode 600 |

No additional deployment, load generation, rollback or restore was performed during these final checks. The log and trace samples are not a full transaction-level correlation test.

## Reproducible read-only checks

```bash
kubectl config current-context
kubectl get applications -n argocd
kubectl get deployment,pods,svc,hpa,pvc -n bankops-gitops
helm list -n bankops-helm-test
helm history bankops-test -n bankops-helm-test
kubectl get pods -n monitoring
ls -lh ~/bankops-backups/
```

Prometheus: `up{job="bankops"}`. Loki: `{namespace="bankops-gitops"}`. Tempo: search recent traces for service bankops in Grafana Explore. See the [incident runbook](runbooks/BANKOPS_INCIDENT_RESPONSE.md) for diagnostic and recovery procedures.

## Outstanding items and honest boundaries

- Full database restore to an isolated instance and recovery-time measurement not performed; backup exists on same host, not offsite. Catalog inspection is not a restore test.
- End-to-end Alertmanager notification delivery not retested; database-level trace correlation not confirmed.
- Historical HPA FailedGetScale Unauthorized warning and intermittent DNS issue require root-cause follow-up.
- CI/CD image promotion is manual/pinned. No recent CI rerun was part of the local validation.
- Single-host Kind, one PostgreSQL replica, API min one replica: no production HA/DR or security certification. Dedicated workload identity, secret management, image scanning and cloud infrastructure remain future work.
- Architecture walkthrough and technical knowledge assessment move to live mock interview sessions; optional AIOps extension remains planned.

See [earlier hands-on exercises](sre-lab-progress-2026-11-23.md) for probe, PDB, resource, scheduling and node-maintenance demonstrations.
