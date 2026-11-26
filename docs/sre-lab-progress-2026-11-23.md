# BankOps SRE Lab Progress — 18–23 November 2026

> **Scope:** Training and validation performed after the latest application/configuration commit on `main` as inspected on 23 November 2026.
>
> **Baseline commit:** [`e54b478` — Enable CPU-based HPA for BankOps](https://github.com/rohanwadehra24/bankops/commit/e54b478470cc10a05a81dd3821e17bea80b13699), committed 18 November 2026.
>
> **Environment:** Local Kind cluster (`kind-bankops`), Kubernetes v1.34.0, nodes `bankops-control-plane`, `bankops-worker`, `bankops-worker2`. Main GitOps application namespace: `bankops-gitops`.
>
> **Evidence classification:** The tests below were executed interactively in the local cluster. They are **not** presented as GitHub code changes. Unless otherwise noted, temporary demonstration workloads were deleted. Commands are included as reproducible training examples, not production change instructions.

## Executive summary

Since the HPA configuration commit, the BankOps SRE training expanded beyond autoscaling to cover application recovery, Kubernetes probes, rolling deployments, disruption budgets, CPU and memory resource behavior, scheduling controls, safe node-maintenance preparation, and node-level incident diagnosis.

The exercises were designed to avoid changing the GitOps-managed BankOps application wherever possible. Standalone demonstration Pods/Deployments were used for failure scenarios. **No actual worker-node drain was performed.**

## Phase 33 — Self-healing, probes and rolling updates

### Container restart versus Pod replacement

- Deleting a BankOps Pod demonstrated that its ReplicaSet creates a replacement to maintain desired replicas.
- Sending `SIGTERM` to PID 1 inside a BankOps container demonstrated a container restart within the Pod under the Deployment restart policy.
- Key distinction: **kubelet restarts failed containers; a Deployment/ReplicaSet replaces deleted Pods**.

### Readiness probe demonstration

A temporary BusyBox Pod used an exec readiness check based on the presence of `/tmp/ready`.

- With the file present: `1/1 Running`.
- After removing the file: `0/1 Running` without a container restart.
- After restoring the file: readiness recovered.

**Lesson:** Readiness controls whether a Pod is eligible to receive Service traffic; a failed readiness probe alone does not restart the container.

### Liveness probe demonstration

A separate BusyBox Pod used `/tmp/alive` for its liveness check.

- Removing the file caused the kubelet to restart the container.
- Restart count increased from 0 to 1; the container subsequently recovered.

**Lesson:** Liveness failures can trigger container restarts.

### Rolling update and rollback

A standalone two-replica Nginx Deployment (`rollout-demo`) was updated from `nginx:1.27-alpine` to `nginx:1.28-alpine`.

- Kubernetes progressively replaced old ReplicaSet Pods with new ones.
- `kubectl rollout status` confirmed successful rollout.
- `kubectl rollout undo` restored the earlier image.
- The demo Deployment was deleted afterward.

The GitOps-managed BankOps Deployment was not used for this standalone Nginx rollout exercise.

## Phase 34 — Availability and PodDisruptionBudget (PDB)

A temporary three-replica Nginx Deployment (`pdb-demo`) was paired with a PDB using `minAvailable: 2`.

1. With three available replicas, `disruptionsAllowed: 1`; an eviction through the Eviction API succeeded and a replacement Pod appeared.
2. After scaling the Deployment to two replicas, `disruptionsAllowed: 0`.
3. Another eviction request was rejected with `TooManyRequests` because it would violate the PDB.

**Lesson:** A PDB limits *voluntary* disruptions; it does not guarantee availability during node failures or provide application replicas automatically.

Both the demonstration Deployment and PDB were removed.

## Phase 35 — Resource management, OOM and CPU throttling

### Baseline observations

Observed resource configuration in `bankops-gitops`:

| Workload | CPU request | CPU limit | Memory request | Memory limit |
|---|---:|---:|---:|---:|
| BankOps API | 100m | 500m | 128Mi | 256Mi |
| PostgreSQL | 100m | 1000m | 256Mi | 512Mi |

At one measurement, BankOps used approximately `3m` CPU and `72Mi` memory; PostgreSQL used `1m` CPU and `23Mi` memory. These are **point-in-time readings**, not capacity guarantees.

### Memory-limit / OOMKilled experiment

A standalone Python Pod (`oom-demo`) was given a `32Mi` memory limit and attempted an allocation around `100Mi`.

- Pod showed `OOMKilled`.
- Termination exit code was `137`.
- The Pod used `restartPolicy: Never`, so it did not repeatedly restart.

**Lesson:** Exceeding the container memory limit can cause an OOM kill. Behavior after termination depends on the Pod's restart policy and its controller.

### CPU throttling experiment

A BusyBox Pod (`cpu-demo`) ran a CPU-intensive loop with a `50m` CPU request and `100m` limit.

- `kubectl top pod cpu-demo` showed approximately `101m` CPU usage.
- Cgroup `cpu.stat` reported `nr_periods=1093` and `nr_throttled=1078` (throttling in about 98.6% of periods).

**Lesson:** CPU limits generally throttle CPU execution rather than killing the container. CPU requests primarily influence scheduling and CPU allocation guarantees.

Both temporary Pods were deleted.

## Phase 36 — Node troubleshooting and maintenance

### 36.1–36.4 Node health and allocation

`kubectl get nodes -o wide` showed all three nodes `Ready` on Kubernetes v1.34.0.

The inspected worker node reported:

- `MemoryPressure=False`
- `DiskPressure=False`
- `PIDPressure=False`
- `Ready=True`

`kubectl top nodes` showed low observed CPU and memory usage during the inspection. The exercise also compared **actual usage**, **resource requests**, and **resource limits**, noting that scheduling is based primarily on requests rather than current usage.

### Scheduling failure: 100 cores versus 100 millicores

A standalone `pending-demo` Pod initially requested:

```yaml
resources:
  requests:
    cpu: "100"
```

The Pod stayed `Pending` with scheduling events reporting insufficient CPU on worker nodes and an untolerated control-plane taint. The request meant **100 CPU cores**, not `100m`.

After recreating the Pod with `cpu: "100m"` and `memory: "128Mi"`, it became `1/1 Running`. The demo was deleted.

### Taints, tolerations and node selection

The control-plane node carried:

```text
node-role.kubernetes.io/control-plane:NoSchedule
```

A temporary BusyBox Pod (`toleration-demo`) used:

```yaml
nodeSelector:
  kubernetes.io/hostname: bankops-control-plane
tolerations:
  - key: node-role.kubernetes.io/control-plane
    operator: Exists
    effect: NoSchedule
```

It successfully ran on `bankops-control-plane`, then was deleted.

**Lesson:** A toleration permits scheduling despite a matching taint; a `nodeSelector` restricts which nodes are eligible.

### Cordon and uncordon

The following were executed on `bankops-worker`:

```bash
kubectl cordon bankops-worker
kubectl get nodes
kubectl uncordon bankops-worker
```

The node temporarily showed `Ready,SchedulingDisabled` and returned to `Ready` after uncordon.

**Lesson:** Cordon blocks normal scheduling of new Pods but does not evict existing running Pods.

### Node-drain safety assessment

Inspection of `bankops-worker` showed 15 Pods, including PostgreSQL, Argo CD components, Grafana, Loki, Prometheus and Kubernetes DaemonSets. A **real drain was intentionally avoided** to prevent service interruption and possible local-data loss.

The first dry run:

```bash
kubectl drain bankops-worker --ignore-daemonsets --dry-run=client
```

reported blockers for Pods using local `emptyDir` storage, including Grafana, Loki and Prometheus Server.

The second dry run:

```bash
kubectl drain bankops-worker \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --dry-run=client
```

returned:

```text
node/bankops-worker drained (dry run)
```

A subsequent `kubectl get nodes` confirmed all three nodes remained `Ready`. **No actual Pods were evicted by these dry runs, and no actual node drain occurred.**

**Safety note:** `--delete-emptydir-data` would permit loss of local `emptyDir` data during a *real* drain. A successful dry run does not establish that live eviction, storage reattachment, PDB checks or rescheduling would succeed.

### Unhealthy-node diagnosis: read-only checks

`bankops-worker2` was inspected as a healthy baseline:

- `MemoryPressure=False`, `DiskPressure=False`, `PIDPressure=False`, `Ready=True`.
- A node-event query returned `No resources found`, meaning no matching events were retained.
- All 16 Pods listed on the node were `Running` and fully ready.
- Historical container restart counts were observed; these were not established as a current node incident.

A cluster-wide warning-event query also found an HPA `FailedGetScale: Unauthorized` warning for `bankops-gitops-bankops-chart`, recurring nine times over about three days. A subsequent `kubectl get hpa -n bankops-gitops` showed `cpu: 3%/60%`, `MINPODS=1`, `MAXPODS=3`, `REPLICAS=1`. The HPA warning's root cause **was not resolved** during this node-focused exercise; valid displayed CPU metrics alone do not prove the warning is permanently fixed.

The team chose not to create a disruptive `NotReady` incident in the shared local cluster. The conceptual troubleshooting approach was reviewed: inspect node readiness/conditions, kubelet and runtime, networking, disk/memory, affected Pods, and recovery verification.

## Practical SRE lessons

1. **Separate failure domains:** A healthy node can host an unhealthy Pod, and an HPA warning does not automatically imply a node failure.
2. **Check the evidence:** Use `kubectl describe`, Events, `kubectl top`, Pod status, logs and cgroup metrics before changing workloads.
3. **Protect service continuity:** Prefer isolated demonstration workloads and dry runs when the cluster also hosts a database and monitoring stack.
4. **Know Kubernetes ownership:** Kubelet, ReplicaSet/Deployment, HPA, scheduler and PDB each solve different problems.
5. **Document uncertainty:** Do not label intermittent warnings or historical restarts as resolved without direct evidence.

## Verification status at the end of the session

| Item | Observed result |
|---|---|
| Three Kind nodes | All `Ready` |
| `bankops-worker2` node conditions | Healthy baseline |
| Pods on `bankops-worker2` | 16 listed, all Running/Ready |
| Cordon/uncordon | Verified |
| Drain dry run | Completed after acknowledging `emptyDir` restriction |
| Real worker drain | **Not performed** |
| HPA | CPU metric and one replica visible; historical authorization warning still requires separate follow-up |
| Temporary demo resources | Removed following exercises |

## Remaining capstone work (planned, not yet verified)

- Final production-style incident scenario, RCA and runbook refinement.
- Confirm reliability indicators, SLOs, alerts and alert routing.
- Review RBAC/secrets and perform safe PostgreSQL backup validation.
- End-to-end verification of CI/CD, Argo CD, Kubernetes and observability.
- Final architecture/README documentation and interview walkthrough.
- Optional future extension: read-only AIOps/agentic incident assistant integrating metrics and logs.

---

**Repository note:** This document records interactive local-lab progress after commit `e54b478`. It does not claim that the lab-only Kubernetes objects were committed to Git or that the production-readiness checks above have already been completed.
