# ArgoCD GitOps Deployment — Lab 13

Documentation for deploying the `devops-info-service` Helm chart via ArgoCD, including
multi-environment rollout, self-healing verification, and an ApplicationSet-based
template pattern.

Source of truth: this repository, branch `lab13`, path `k8s/devops-info-service`.

---

## 1. ArgoCD Setup

### Installation

Installed ArgoCD via the official Helm chart into a dedicated `argocd` namespace on a
Minikube cluster (`lab13` profile).

```bash
minikube start --profile=lab13 --driver=docker --memory=4096 --cpus=2

helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo

kubectl create namespace argocd
helm install argocd argo/argo-cd \
  --namespace argocd \
  --version 7.8.2 \
  --wait --timeout 5m
```

Chart version `7.8.2` → ArgoCD application version `v2.14.2`.

**Pod verification:**

```
$ kubectl get pods -n argocd
NAME                                                READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                     1/1     Running   0          19m
argocd-applicationset-controller-5d6449c58c-q7m5c   1/1     Running   0          19m
argocd-dex-server-5b86876f59-cv5l2                  1/1     Running   0          19m
argocd-notifications-controller-5c49fdc665-htjcs    1/1     Running   0          19m
argocd-redis-64f9c74654-jjv5m                       1/1     Running   0          19m
argocd-repo-server-b586f7fbd-hvbhz                  1/1     Running   0          19m
argocd-server-58d76b65fd-9vhgp                      1/1     Running   0          19m
```

### UI Access

ArgoCD was exposed via `kubectl port-forward`:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Initial admin password retrieved from the bootstrap secret:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

UI opened at `https://localhost:8080` (username `admin`, password from secret above).

### CLI

Installed via Homebrew and logged in through the port-forward:

```bash
brew install argocd
# argocd: v3.3.8

argocd login localhost:8080 --username admin --password <password> --insecure
# 'admin:login' logged in successfully
```

> **Screenshot placeholder:** `screenshots/argocd-login.png` — ArgoCD UI login page and
> the first view of the Applications grid immediately after install (empty state).

---

## 2. Application Configuration

All ArgoCD resources live in [`k8s/argocd/`](argocd/). Each Application points at this
same Git repository and sub-path; environment-specific behaviour is controlled entirely
through the Helm `values-*.yaml` files chosen in `spec.source.helm.valueFiles`.

### Single-environment Application (baseline)

`k8s/argocd/application.yaml` — deploys into `default`, manual sync. Used for the
initial Task 2 walkthrough before splitting into dev/prod.

Key fields:
- `spec.source.repoURL` → this repo.
- `spec.source.targetRevision` → `lab13` branch.
- `spec.source.path` → `k8s/devops-info-service`.
- `spec.source.helm.valueFiles` → `[values.yaml]`.
- `spec.destination.namespace` → `default`.
- `spec.syncPolicy` → manual (no `automated` block).

### Initial sync result

```
$ argocd app sync python-app
Sync Status:   Synced to lab13 (457974f)
Health Status: Healthy
Phase:         Succeeded
Duration:      31s

KIND                   STATUS  HEALTH
Deployment             Synced  Healthy
Service                Synced  Healthy
ConfigMap (env)        Synced
ConfigMap (config)     Synced
Secret                 Synced
PersistentVolumeClaim  Synced  Healthy
ServiceAccount         Synced
Job (pre-install)      Succeeded
Job (post-install)     Succeeded
```

### GitOps workflow test

Commit `c012926` bumped `replicaCount: 1 → 2` in `values-dev.yaml`.

```bash
# Edit values-dev.yaml
git commit -am "Lab 13: GitOps test — bump dev replicaCount to 2"
git push

# Force ArgoCD to re-check the repo (otherwise it polls every 3 minutes)
argocd app get python-app-dev --refresh
# Sync Status: OutOfSync from lab13 (c012926)
```

Because the dev app has `automated` sync, ArgoCD applied the change on its own within
seconds — no `argocd app sync` needed. Deployment scaled from 1 → 2 replicas:

```
autosync-applied replicas=2 at 16:06:36
```

---

## 3. Multi-Environment Deployment

Two Applications target the same Helm chart but different value files and
namespaces:

| Application        | Namespace | Values file       | Sync policy             | Replicas | Service type |
|--------------------|-----------|-------------------|-------------------------|----------|--------------|
| `python-app-dev`   | `dev`     | `values-dev.yaml` | Automated, prune, selfHeal | 1–2      | NodePort     |
| `python-app-prod`  | `prod`    | `values-prod.yaml`| Manual                  | 5        | LoadBalancer |

Both Application manifests are committed in [`k8s/argocd/`](argocd/):
`application-dev.yaml` and `application-prod.yaml`.

### Sync policy rationale

**Dev — automated:**
```yaml
syncPolicy:
  automated:
    prune: true      # delete resources removed from Git
    selfHeal: true   # revert manual cluster edits
  syncOptions:
    - CreateNamespace=true
```
Dev should always mirror `HEAD`. Drift is a bug, not a release event.

**Prod — manual:**
```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
  # no automated block → manual sync required
```
Production deploys need a human gate: a reviewer confirms the diff, picks a window that
avoids peak traffic, and is present for rollback. ArgoCD still surfaces drift and
out-of-sync status; it just won't auto-apply.

### Verification

```
$ argocd app list
NAME                    NAMESPACE  STATUS  HEALTH       SYNCPOLICY
argocd/python-app-dev   dev        Synced  Progressing  Auto-Prune
argocd/python-app-prod  prod       Synced  Healthy      Manual

$ kubectl get pods -n dev
python-app-dev-devops-info-service-... 1/1 Running

$ kubectl get pods -n prod
python-app-prod-devops-info-service-... 1/1 Running   (× 5)
```

> **Screenshot placeholder:** `screenshots/argocd-multi-env.png` — ArgoCD Applications
> tiles showing `python-app-dev` (Auto-Sync) and `python-app-prod` (Manual) side by
> side, both `Synced / Healthy`.

---

## 4. Self-Healing & Sync Policies

### Test 4.1 — Manual scale (ArgoCD self-heal)

```
=== BEFORE SCALE ===
python-app-dev-devops-info-service   1/1     1            1           85s

$ kubectl scale deploy python-app-dev-devops-info-service -n dev --replicas=5
deployment.apps/python-app-dev-devops-info-service scaled

=== Immediately after scale ===
NAME                                                  READY   STATUS    RESTARTS   AGE
python-app-dev-devops-info-service-...-57f92   0/1     Pending   0          0s
python-app-dev-devops-info-service-...-bg8n7   1/1     Running   0          85s
python-app-dev-devops-info-service-...-j4s65   0/1     Pending   0          0s
python-app-dev-devops-info-service-...-lxstj   0/1     Pending   0          0s
python-app-dev-devops-info-service-...-pr7n9   0/1     Pending   0          0s

selfheal-complete replicas=1 at 16:03:47

=== After ArgoCD self-heal ===
python-app-dev-devops-info-service   1/1     1            1           98s
```

ArgoCD reverted the scale within ~13 seconds. The 4 extra pods were first scheduled,
then immediately terminated when the controller reconciled the desired spec from Git.

### Test 4.2 — Pod deletion (Kubernetes self-heal, not ArgoCD)

```
$ kubectl delete pod -n dev python-app-dev-devops-info-service-...-57f92
pod "..." deleted

$ kubectl get pods -n dev
python-app-dev-devops-info-service-... 1/1 Terminating
python-app-dev-devops-info-service-... 1/1 Running       <-- recreated
```

Recreated almost instantly by the Deployment's ReplicaSet controller — this happens
even if ArgoCD is completely down. ArgoCD never sees the deletion because the desired
state (Deployment with N replicas) was never changed; only a pod owned by the
ReplicaSet was removed.

### Test 4.3 — Configuration drift (label / env var)

```
$ kubectl label deploy python-app-dev-devops-info-service -n dev manually-added=drift-test --overwrite
$ kubectl set env deploy/python-app-dev-devops-info-service -n dev MANUAL_DRIFT=yes
```

ArgoCD reports the state through `argocd app get --refresh` and re-reconciles on its
3-minute cycle (or immediately when the app is refreshed). For label-only drift, the
default diff tracker may treat added labels as additive and leave them alone; for spec
drift (env vars, replica counts, images), `selfHeal: true` will revert the change.

To clean up a stuck drift manually:
```bash
kubectl set env deploy/python-app-dev-devops-info-service -n dev MANUAL_DRIFT-
kubectl label deploy python-app-dev-devops-info-service -n dev manually-added-
```

### ArgoCD vs Kubernetes self-healing

| Mechanism       | Watches                            | Reverts                             |
|-----------------|------------------------------------|-------------------------------------|
| Kubernetes      | Pods vs ReplicaSet `replicas`      | Missing or crashed pods             |
| ArgoCD          | Live cluster state vs Git manifest | Any field drift in managed resources |

These stack: Kubernetes keeps pod count matching the Deployment; ArgoCD keeps the
Deployment matching Git.

### Sync triggers

- **Polling** — ArgoCD polls every 3 minutes by default
  (`timeout.reconciliation` in the `argocd-cm` ConfigMap).
- **Webhook** — configure the Git host to POST to ArgoCD for near-instant sync.
- **Manual** — `argocd app sync <name>` or the "Sync" button in the UI.
- **Refresh** — `argocd app get --refresh` forces a single comparison without waiting
  for the poll.

> **Screenshot placeholder:** `screenshots/argocd-selfheal-diff.png` — ArgoCD diff view
> immediately after `kubectl scale`, showing the OutOfSync banner and the live-vs-desired
> `spec.replicas` diff that triggers self-heal.

---

## 5. Bonus — ApplicationSet

`k8s/argocd/applicationset.yaml` uses the **list generator** to emit both the dev and
prod Applications from a single template. A `templatePatch` injects the `automated`
sync policy only when `autoSync == "true"`, so dev keeps auto-sync/selfHeal and prod
stays manual — expressed once, not duplicated across two Application manifests.

```yaml
generators:
  - list:
      elements:
        - { env: dev,  namespace: dev,  valuesFile: values-dev.yaml,  autoSync: "true"  }
        - { env: prod, namespace: prod, valuesFile: values-prod.yaml, autoSync: "false" }

template:
  metadata:
    name: 'python-app-set-{{ .env }}'
  spec:
    source:
      repoURL: https://github.com/MoriSummerz/.../DevOps-Core-Course.git
      targetRevision: lab13
      path: k8s/devops-info-service
      helm:
        valueFiles: ['{{ .valuesFile }}']
    destination:
      server: https://kubernetes.default.svc
      namespace: '{{ .namespace }}'

templatePatch: |
  spec:
    syncPolicy:
      syncOptions:
        - CreateNamespace=true
      {{- if eq .autoSync "true" }}
      automated:
        prune: true
        selfHeal: true
      {{- end }}
```

### Verified output

```
$ kubectl apply -f k8s/argocd/applicationset.yaml
applicationset.argoproj.io/python-app-set created

$ kubectl get appset,app -n argocd
NAME                                        AGE
applicationset.argoproj.io/python-app-set   5s

NAME                                          SYNC STATUS   HEALTH STATUS
application.argoproj.io/python-app-set-dev    Synced        Healthy   # auto-synced
application.argoproj.io/python-app-set-prod   OutOfSync     Missing   # manual, as intended

$ argocd app sync python-app-set-prod    # human gate
$ argocd app list
NAME                         NAMESPACE  STATUS  HEALTH   SYNCPOLICY
argocd/python-app-set-dev    dev        Synced  Healthy  Auto-Prune
argocd/python-app-set-prod   prod       Synced  Healthy  Manual
```

### Why ApplicationSet vs N separate Applications

- **One source of truth** — adding a third environment (`staging`) is a single list
  entry, not a new file and a new manual apply.
- **No copy-paste drift** — repoURL, path, targetRevision, finalizers, and common
  sync options are templated once.
- **Lifecycle automation** — removing an element from `generators` deletes its
  Application (and, with the finalizer, its cluster resources). No dangling apps.

**When to pick which generator:**
- `list` — small, fixed environment set (dev/staging/prod).
- `git` (directory) — one Application per chart discovered under a mono-repo path.
- `cluster` — same workload across many clusters in `argocd cluster list`.
- `matrix` — combine generators, e.g. `list × cluster` for per-env-per-cluster apps.
- `pullRequest` — ephemeral preview environments per open PR.

> **Screenshot placeholder:** `screenshots/argocd-applicationset.png` — ArgoCD UI
> showing the `python-app-set` ApplicationSet and both generated child Applications
> (`python-app-set-dev`, `python-app-set-prod`).

---

## 6. Reproducing from scratch

```bash
# 1. Cluster + ArgoCD
minikube start --profile=lab13 --driver=docker --memory=4096 --cpus=2
helm repo add argo https://argoproj.github.io/argo-helm && helm repo update argo
kubectl create namespace argocd
helm install argocd argo/argo-cd -n argocd --version 7.8.2 --wait

# 2. Load the app image (pullPolicy: Never / IfNotPresent + not pushed to a registry)
eval $(minikube -p lab13 docker-env)
docker build -t morisummerz/devops-info-service:latest app_python/
docker tag morisummerz/devops-info-service:latest morisummerz/devops-info-service:1.0.0

# 3. Deploy via ArgoCD — pick ONE of the two patterns:
# Individual Applications:
kubectl apply -f k8s/argocd/application-dev.yaml
kubectl apply -f k8s/argocd/application-prod.yaml

# OR ApplicationSet (bonus):
kubectl apply -f k8s/argocd/applicationset.yaml

# 4. Sync prod manually (dev auto-syncs)
argocd login localhost:8080 --username admin \
  --password "$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)" \
  --insecure
argocd app sync python-app-prod    # or python-app-set-prod with ApplicationSet
```

---

## Files

- [`k8s/argocd/application.yaml`](argocd/application.yaml) — single-env baseline
- [`k8s/argocd/application-dev.yaml`](argocd/application-dev.yaml) — dev with auto-sync
- [`k8s/argocd/application-prod.yaml`](argocd/application-prod.yaml) — prod with manual sync
- [`k8s/argocd/applicationset.yaml`](argocd/applicationset.yaml) — bonus list generator
- [`k8s/devops-info-service/`](devops-info-service/) — the Helm chart being deployed
