# StatefulSets & Persistent Storage — Lab 15

This document covers the conversion of the `devops-info-service` Helm chart
from a Deployment/Rollout to a StatefulSet with per-pod persistent storage,
plus the verification evidence required by Lab 15.

The chart still supports the Deployment and Rollout paths from previous labs
— the StatefulSet path is opt-in via `statefulset.enabled=true` and the
`values-statefulset.yaml` overlay.

---

## 1. Concepts

### Why StatefulSet, not Deployment

Deployments are designed for stateless workloads: replicas are
interchangeable, share a Service, and (when persistence is involved) typically
share a single PVC. That model breaks for stateful systems where each
instance owns a piece of the data and needs to be addressable on its own.

StatefulSets give the workload three guarantees that Deployments do not:

1. **Stable, unique network identity.** Each pod gets a deterministic name
   (`<sts>-0`, `<sts>-1`, ...) and a per-pod DNS record under a headless
   Service. The DNS name follows the pod across rescheduling — pod-0 is
   always pod-0, regardless of which node it lands on.
2. **Stable, persistent per-pod storage.** A `volumeClaimTemplates` block
   tells the controller to mint one PVC per pod, named
   `<volumeName>-<sts>-<ordinal>`. The PVC is bound to that ordinal for the
   lifetime of the StatefulSet — deleting the pod does **not** delete the
   PVC, so when the pod is recreated it reattaches to the same volume and
   sees the same data.
3. **Ordered, predictable lifecycle.** Pods are created and terminated in
   ordinal order (0 → 1 → 2 on scale-up, 2 → 1 → 0 on scale-down) and
   updates roll from the highest ordinal down. This matters for clustered
   systems where peer-discovery requires a known leader.

### Deployment vs StatefulSet

| Feature      | Deployment                | StatefulSet                                |
|--------------|---------------------------|--------------------------------------------|
| Pod names    | random hash suffix        | ordered `<name>-0`, `<name>-1`, ...        |
| Storage      | shared PVC (or ephemeral) | per-pod PVC via `volumeClaimTemplates`     |
| Scaling      | parallel, any order       | ordered (`OrderedReady`) by default        |
| Network ID   | ephemeral pod IP          | stable DNS via headless Service            |
| Update order | unspecified               | highest-ordinal first, respects partition  |
| PVC lifetime | tied to PVC object        | survives pod deletion, scoped to ordinal   |

### When to reach for which

- **Deployment / Rollout** — stateless web apps, API servers, fungible
  workers. Use Argo Rollouts (Lab 14) when you want progressive delivery
  on top of that.
- **StatefulSet** — databases (PostgreSQL, MySQL, MongoDB), brokers
  (Kafka, RabbitMQ), distributed stores (Elasticsearch, Cassandra, etcd) —
  anything where instances are not interchangeable.

### Headless Service

A `ClusterIP: None` Service is "headless": kube-proxy does **not** create a
virtual IP for it. Instead, the kube-DNS records resolve directly to the
backing pod IPs. For a StatefulSet, this means each pod is addressable as:

```
<pod-name>.<headless-service>.<namespace>.svc.cluster.local
```

Resolving the headless Service by name returns the IPs of all ready pods —
useful for peer discovery. Each pod also gets its own A record so callers
can target a specific replica deterministically (e.g. always write to
`<sts>-0` as the leader).

The chart sets `publishNotReadyAddresses: true` on the headless Service
so peers can discover each other during startup, before readiness probes
pass — important for clustered systems that bootstrap via DNS.

---

## 2. Implementation

### Chart layout

The chart now renders one of three workload kinds, mutually exclusive:

| `statefulset.enabled` | `rollout.enabled` | Renders            |
|-----------------------|-------------------|--------------------|
| `false` (default)     | `false`           | `Deployment`       |
| `false`               | `true`            | `Rollout` (Argo)   |
| `true`                | (ignored)         | `StatefulSet`      |

The `pvc.yaml` template (a single shared PVC) is suppressed when the
StatefulSet path is active — `volumeClaimTemplates` provisions per-pod
PVCs instead.

### New / changed files

- `templates/statefulset.yaml` — StatefulSet manifest with
  `volumeClaimTemplates`, configurable `podManagementPolicy`, and
  `RollingUpdate` / `OnDelete` strategies.
- `templates/headless-service.yaml` — `ClusterIP: None` Service that
  backs the StatefulSet's stable DNS records.
- `templates/{deployment,rollout,pvc}.yaml` — gated behind
  `not .Values.statefulset.enabled` so the chart renders cleanly.
- `values.yaml` — new `statefulset:` block (disabled by default).
- `values-statefulset.yaml` — overlay that flips
  `statefulset.enabled=true`, sets `replicaCount: 3`, and disables the
  Rollout path.

### Key knobs

```yaml
statefulset:
  enabled: true
  podManagementPolicy: OrderedReady   # or Parallel
  updateStrategy:
    type: RollingUpdate               # or OnDelete
    partition: 0                      # only pods with ordinal >= partition update

persistence:
  enabled: true
  mountPath: /data
  size: 100Mi
  accessMode: ReadWriteOnce
```

### Deploy

```bash
helm install info k8s/devops-info-service \
  -f k8s/devops-info-service/values-statefulset.yaml
```

---

## 3. Resource verification

Output of `kubectl get po,sts,svc,pvc` after install:

```
NAME                             READY   STATUS    RESTARTS   AGE
pod/info-devops-info-service-0   1/1     Running   0          93s
pod/info-devops-info-service-1   1/1     Running   0          60s
pod/info-devops-info-service-2   1/1     Running   0          27s

NAME                                        READY   AGE
statefulset.apps/info-devops-info-service   3/3     93s

NAME                                        TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
service/info-devops-info-service            NodePort    10.102.34.253   <none>        80:30080/TCP   93s
service/info-devops-info-service-headless   ClusterIP   None            <none>        80/TCP         93s

NAME                                                    STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
persistentvolumeclaim/data-info-devops-info-service-0   Bound    pvc-aa8afb5d-c989-40e5-aa02-1a5530f03217   100Mi      RWO            standard
persistentvolumeclaim/data-info-devops-info-service-1   Bound    pvc-2b978d18-c6c3-4408-9c0a-989d205c71b5   100Mi      RWO            standard
persistentvolumeclaim/data-info-devops-info-service-2   Bound    pvc-9fd48e30-faed-4d83-ab0c-b21e1fbc3518   100Mi      RWO            standard
```

Notes:

- Pod names are ordered (`-0`, `-1`, `-2`) and were created sequentially
  (notice the 33s gap between AGE values — `OrderedReady` waits for each
  pod to become ready before starting the next).
- One PVC per pod, each named `data-<sts>-<ordinal>` from the
  `volumeClaimTemplates.metadata.name=data` plus the StatefulSet name.
- Two Services: the existing `NodePort` for external access, and the new
  `ClusterIP: None` headless Service for per-pod DNS.

---

## 4. Network identity (DNS)

The headless Service publishes one A record per pod under the form
`<pod>.<headless>.<namespace>.svc.cluster.local`.

### Per-pod DNS records (resolved from inside pod-0)

```
$ getent hosts info-devops-info-service-0.info-devops-info-service-headless.default.svc.cluster.local
10.244.0.5      info-devops-info-service-0.info-devops-info-service-headless.default.svc.cluster.local

$ getent hosts info-devops-info-service-1.info-devops-info-service-headless.default.svc.cluster.local
10.244.0.6      info-devops-info-service-1.info-devops-info-service-headless.default.svc.cluster.local

$ getent hosts info-devops-info-service-2.info-devops-info-service-headless.default.svc.cluster.local
10.244.0.7      info-devops-info-service-2.info-devops-info-service-headless.default.svc.cluster.local
```

These match the pod IPs from `kubectl get pods -o wide` (10.244.0.5,
10.244.0.6, 10.244.0.7) — each pod is individually addressable.

### Headless Service: returns all endpoints

```
$ getent ahostsv4 info-devops-info-service-headless.default.svc.cluster.local
10.244.0.5      STREAM info-devops-info-service-headless.default.svc.cluster.local
10.244.0.7      STREAM
10.244.0.6      STREAM
```

Resolving the headless Service name returns the IPs of *all* ready pods —
this is what peer-discovery code (Cassandra, Elasticsearch, etc.) uses
to find cluster members.

### Cross-pod resolution works in both directions

```
$ kubectl exec info-devops-info-service-2 -- getent hosts \
    info-devops-info-service-0.info-devops-info-service-headless.default.svc.cluster.local
10.244.0.5      info-devops-info-service-0.info-devops-info-service-headless.default.svc.cluster.local
```

### DNS naming pattern

```
<pod-name>.<service-name>.<namespace>.svc.cluster.local
```

where `<service-name>` is the `serviceName` field on the StatefulSet
(must match a real headless Service in the same namespace).

---

## 5. Per-pod storage isolation

Each pod owns its own PVC, mounted at `/data`, holding its own
`/data/visits` counter. Hitting different pods produces different
counts — proving that the storage is not shared.

```
$ kubectl exec info-devops-info-service-0 -- python3 -c \
    "import urllib.request; [urllib.request.urlopen('http://localhost:5000/').read() for _ in range(3)]"
$ kubectl exec info-devops-info-service-0 -- python3 -c \
    "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/visits/').read().decode())"
{"visits":3}

$ # 5 hits to pod-1
$ kubectl exec info-devops-info-service-1 -- python3 -c "..."
{"visits":5}

$ # 1 hit to pod-2
$ kubectl exec info-devops-info-service-2 -- python3 -c "..."
{"visits":1}
```

Reading `/data/visits` directly from each pod confirms the divergence:

```
$ for i in 0 1 2; do echo -n "pod-$i: "; \
    kubectl exec info-devops-info-service-$i -- cat /data/visits; echo; done
pod-0: 3
pod-1: 5
pod-2: 1
```

Three pods, three independent counters — none of the writes from one pod
are visible to the others. This is the property a Deployment with a
shared PVC could not give you (and a Deployment with a `ReadWriteOnce`
shared PVC would in fact break, because only one pod could mount it).

---

## 6. Persistence test

Deleting a pod does **not** delete its PVC. The StatefulSet controller
recreates the pod and rebinds it to the same PVC, so the data survives.

```
$ kubectl exec info-devops-info-service-0 -- cat /data/visits
3

$ kubectl delete pod info-devops-info-service-0
pod "info-devops-info-service-0" deleted

$ kubectl wait --for=condition=Ready pod/info-devops-info-service-0 --timeout=120s
pod/info-devops-info-service-0 condition met

$ kubectl exec info-devops-info-service-0 -- cat /data/visits
3

$ kubectl get pvc data-info-devops-info-service-0
NAME                              STATUS   VOLUME                                     CAPACITY   AGE
data-info-devops-info-service-0   Bound    pvc-aa8afb5d-c989-40e5-aa02-1a5530f03217   100Mi      4m45s
```

The PVC UID (`pvc-aa8afb5d-...`) is unchanged across the delete — the
underlying PV is the same disk, just remounted into the new pod. This is
the core durability guarantee that makes StatefulSets safe for stateful
workloads.

---

## 7. Update strategies (bonus)

The chart exposes both update strategies via
`statefulset.updateStrategy`.

### RollingUpdate with `partition`

Pods with ordinal `>= partition` are updated; the rest are frozen on the
current revision. This is the StatefulSet equivalent of a canary — you
can update the highest ordinals first, observe, then drop the partition
to roll the rest.

```
# Set partition=2 with 3 replicas: only pod-2 updates.
$ helm upgrade info k8s/devops-info-service \
    -f k8s/devops-info-service/values-statefulset.yaml \
    --set image.tag=v2 \
    --set statefulset.updateStrategy.partition=2

$ kubectl get pods -l app.kubernetes.io/instance=info \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'
info-devops-info-service-0      morisummerz/devops-info-service:latest
info-devops-info-service-1      morisummerz/devops-info-service:latest
info-devops-info-service-2      morisummerz/devops-info-service:v2
```

`kubectl rollout status` reports `partitioned roll out complete: 1 new
pods have been updated...` — the controller knows the partition has
held the other two back deliberately, not failed.

Dropping `partition` to `0` rolls the remaining pods (highest ordinal
first, so order is `pod-1` → `pod-0`, since `pod-2` is already on the
new revision):

```
$ helm upgrade info ... --set image.tag=v2 --set statefulset.updateStrategy.partition=0
$ kubectl rollout status sts/info-devops-info-service
partitioned roll out complete: 3 new pods have been updated...
```

**Use cases:** progressive delivery for clustered apps (test the new
version on the highest-ordinal replica first, since it tends to be the
"newest" follower in many leader-election schemes).

### OnDelete

The controller does **not** auto-recreate pods on spec changes — they
are only updated when the user manually deletes them.

```
$ helm upgrade info ... --set image.tag=latest --set statefulset.updateStrategy.type=OnDelete
$ kubectl get sts info-devops-info-service -o jsonpath='{.spec.updateStrategy}'
{"type":"OnDelete"}

$ # All pods still on the old image — spec change did not trigger a roll.
$ kubectl get pods -l app.kubernetes.io/instance=info \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'
info-devops-info-service-0      morisummerz/devops-info-service:v2
info-devops-info-service-1      morisummerz/devops-info-service:v2
info-devops-info-service-2      morisummerz/devops-info-service:v2

$ # Manually delete pod-2 to pick up the new image.
$ kubectl delete pod info-devops-info-service-2
$ kubectl wait --for=condition=Ready pod/info-devops-info-service-2

$ kubectl get pods -l app.kubernetes.io/instance=info \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'
info-devops-info-service-0      morisummerz/devops-info-service:v2
info-devops-info-service-1      morisummerz/devops-info-service:v2
info-devops-info-service-2      morisummerz/devops-info-service:latest
```

**Use cases:**

- Workloads where pod restarts have non-trivial coordination costs
  (e.g. Kafka brokers that need a controlled leader handoff, or
  PostgreSQL primaries where you want to choose the failover moment).
- Applications that need an external orchestrator (an Operator) to
  drive updates rather than the StatefulSet controller.
- Any case where "the operator clicks the button" semantics are
  desirable over "kubectl apply" semantics.

After all pods are recreated, the `/data/visits` counters are still 3,
5, and 1 — confirming once more that the PVCs survive both update
strategies, since they are scoped to the StatefulSet, not the pod.
