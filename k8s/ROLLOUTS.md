# Lab 14 — Progressive Delivery with Argo Rollouts

This document covers the progressive-delivery setup for the `devops-info-service`
Helm chart. The chart's `Deployment` was converted to an Argo Rollouts `Rollout`
that supports both **canary** and **blue-green** strategies, plus an optional
metrics-based `AnalysisTemplate` for automated rollback.

---

## 1. Argo Rollouts Setup

### 1.1 Install the controller

```bash
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts \
  -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

kubectl get pods -n argo-rollouts
# expected: argo-rollouts-<hash>   1/1   Running
```

### 1.2 Install the kubectl plugin

```bash
# macOS (Apple Silicon)
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-darwin-arm64
chmod +x kubectl-argo-rollouts-darwin-arm64
sudo mv kubectl-argo-rollouts-darwin-arm64 /usr/local/bin/kubectl-argo-rollouts

# macOS (Intel) — replace arm64 with amd64 in the URL above.
# Linux — replace darwin with linux.
# brew alternative: `brew install argoproj/tap/kubectl-argo-rollouts` (builds from
# source — needs an up-to-date Xcode on macOS).

kubectl argo rollouts version
```

### 1.3 Install the dashboard

```bash
kubectl apply -n argo-rollouts \
  -f https://github.com/argoproj/argo-rollouts/releases/latest/download/dashboard-install.yaml

kubectl port-forward svc/argo-rollouts-dashboard -n argo-rollouts 3100:3100
# open http://localhost:3100
```

![](k8s/screenshots/dashboard.png)

### 1.4 Rollout vs Deployment — what changes

Both objects share the same pod spec, replica count and label selector. The
differences are isolated to `spec.strategy`:

| Field | `Deployment` | `Rollout` |
|---|---|---|
| `apiVersion` | `apps/v1` | `argoproj.io/v1alpha1` |
| `kind` | `Deployment` | `Rollout` |
| `spec.strategy` | `RollingUpdate` / `Recreate` | `canary` or `blueGreen` |
| Traffic shifting | implicit, replica-driven | explicit, percentage steps |
| Manual gates | none | `pause: {}` step |
| Metric-based gates | none | `analysis:` step + `AnalysisTemplate` |
| Preview environment | none | `previewService` (blueGreen) |
| Abort / promote | `kubectl rollout undo` only | `kubectl argo rollouts abort/promote` |

The pod template, services, ConfigMaps and PVCs are unchanged — the existing
`Service` keeps routing traffic; Argo Rollouts mutates its selector and the
underlying ReplicaSets to control the split.

---

## 2. Chart layout

```
k8s/devops-info-service/
├── templates/
│   ├── deployment.yaml         # rendered only when rollout.enabled=false
│   ├── rollout.yaml            # rendered when rollout.enabled=true (default)
│   ├── preview-service.yaml    # rendered when strategy=blueGreen
│   ├── analysistemplate.yaml   # rendered when analysis.enabled=true
│   └── service.yaml            # active Service (unchanged)
├── values.yaml                 # default → canary
├── values-bluegreen.yaml       # override → blueGreen
└── values-canary-analysis.yaml # override → canary + AnalysisTemplate (bonus)
```

Toggle in `values.yaml`:

```yaml
rollout:
  enabled: true            # false → render plain Deployment
  strategy: canary         # canary | blueGreen
```

---

## 3. Canary Deployment

### 3.1 Strategy configuration

`values.yaml` ships with the canary steps required by the lab:

```yaml
rollout:
  enabled: true
  strategy: canary
  canary:
    steps:
      - setWeight: 20
      - pause: {}                 # manual promotion
      - setWeight: 40
      - pause: { duration: 30s }
      - setWeight: 60
      - pause: { duration: 30s }
      - setWeight: 80
      - pause: { duration: 30s }
      - setWeight: 100
```

`setWeight: N` shifts `N%` of replicas to the canary ReplicaSet. `pause: {}`
blocks the rollout until `kubectl argo rollouts promote` is run; `pause: {duration: 30s}`
auto-resumes after the timer.

### 3.2 First install

```bash
helm upgrade --install python-app k8s/devops-info-service \
    -f k8s/devops-info-service/values.yaml

kubectl get rollout
kubectl argo rollouts get rollout python-app-devops-info-service
```

The first install creates the stable ReplicaSet at 100% traffic — no canary
steps run because there is no previous version to compare against.

![](/k8s/screenshots/canary-initial.png)

### 3.3 Trigger a canary rollout

Bump the image tag (or any pod-spec field) and upgrade:

```bash
helm upgrade python-app k8s/devops-info-service \
    -f k8s/devops-info-service/values.yaml \
    --set image.tag=v2

# watch the rollout in a separate terminal
kubectl argo rollouts get rollout python-app-devops-info-service -w
```

Expected progression:

| Step | Action | What you see |
|---|---|---|
| 1 | `setWeight: 20` | 20% of pods on `:v2`, status = `Paused — CanaryPauseStep` |
| 2 | `pause: {}` | Rollout halts, dashboard shows a "Promote" button |
| — | `kubectl argo rollouts promote python-app-devops-info-service` | Step advances |
| 3 | `setWeight: 40` → `pause 30s` | auto-progresses after timer |
| 4 | `setWeight: 60` → `pause 30s` | auto-progresses |
| 5 | `setWeight: 80` → `pause 30s` | auto-progresses |
| 6 | `setWeight: 100` | canary becomes the new stable, old RS scales down |

![](/k8s/screenshots/canary-paused.png)

![](/k8s/screenshots/canary-promoting.png)

### 3.4 Test rollback (abort)

While a rollout is in progress (e.g. paused at 20%):

```bash
kubectl argo rollouts abort python-app-devops-info-service
```

The canary ReplicaSet scales to 0 immediately and 100% traffic returns to the
stable version. No pods on the new image remain. To resume the same rollout
later use `kubectl argo rollouts retry rollout <name>`.

![](/k8s/screenshots/canary-aborted.png)

---

## 4. Blue-Green Deployment

### 4.1 Strategy configuration

`values-bluegreen.yaml` flips the strategy:

```yaml
rollout:
  enabled: true
  strategy: blueGreen
  blueGreen:
    autoPromotionEnabled: false   # require manual promote
    scaleDownDelaySeconds: 30     # keep blue alive 30s for instant rollback
    previewService:
      type: NodePort
      nodePort: 30081
```

The chart renders two services:

* **`python-app-devops-info-service`** — active service, points at the live (blue) ReplicaSet.
* **`python-app-devops-info-service-preview`** — preview service, points at the new (green) ReplicaSet.

`autoPromotionEnabled: false` means the green stack is created and exposed via
the preview service, but the active Service does NOT switch until you promote
manually. With `autoPromotionEnabled: true` (or `autoPromotionSeconds: N`) the
switch happens automatically.

### 4.2 Install (initial blue)

```bash
helm upgrade --install python-app k8s/devops-info-service \
    -f k8s/devops-info-service/values.yaml \
    -f k8s/devops-info-service/values-bluegreen.yaml

kubectl get svc | grep python-app
# python-app-devops-info-service           NodePort   ...   30080
# python-app-devops-info-service-preview   NodePort   ...   30081
```

![](/k8s/screenshots/bluegreen-initial.png)

### 4.3 Trigger a green deployment

```bash
helm upgrade python-app k8s/devops-info-service \
    -f k8s/devops-info-service/values.yaml \
    -f k8s/devops-info-service/values-bluegreen.yaml \
    --set image.tag=v2

kubectl argo rollouts get rollout python-app-devops-info-service -w
```

A green ReplicaSet is created at full replica count. The preview Service now
selects green; active Service still selects blue.

```bash
# active = blue (current production)
minikube service python-app-devops-info-service --url

# preview = green (new version, for QA)
minikube service python-app-devops-info-service-preview --url
```

Compare both URLs — confirm production is unchanged and preview shows the new
build.

![](/k8s/screenshots/bluegreen-paused.png)

### 4.4 Promote

```bash
kubectl argo rollouts promote python-app-devops-info-service
```

The active Service selector flips to green in a single API call — the switch
is **instantaneous** for new connections. The blue ReplicaSet is kept alive
for `scaleDownDelaySeconds` (30s) before being scaled down.

![](/k8s/screenshots/bluegreen-promoted.png)

### 4.5 Instant rollback

If the new version misbehaves immediately after promotion (within
`scaleDownDelaySeconds`), abort:

```bash
kubectl argo rollouts undo python-app-devops-info-service
```

Argo Rollouts re-points the active Service back at the still-running blue
ReplicaSet — no pods need to be re-created, so rollback is effectively free.
After the scale-down delay the blue ReplicaSet is gone, and `undo` would have
to re-create it (slower, but still functional).

---

## 5. Strategy Comparison

| Aspect | Canary | Blue-Green |
|---|---|---|
| **Traffic shift** | Gradual (20% → 40% → ... → 100%) | Instant flip |
| **User impact during release** | Mixed: some users hit v2, most still on v1 | Zero until promote, then 100% on v2 |
| **Resource overhead** | Small (1 extra canary pod typically) | 2× replicas during the green phase |
| **Rollback latency** | Seconds — abort scales canary to 0 | Sub-second — selector flip |
| **Best for** | Backend APIs, gradual exposure, A/B-like checks | Stateless web apps, big UI changes, blast-radius isolation |
| **Bad for** | Stateful workloads (mixed versions on shared DB schema) | Cost-sensitive setups, DB migrations needing intermediate states |
| **Pairs naturally with** | Metric analysis (gate per-step) | Smoke tests against the preview Service |

**Recommendation for this project:** stick with **canary** by default. The app
is stateless behind a single Service, the `/health/` endpoint is cheap, and
gradual rollout pairs well with the bonus AnalysisTemplate. Switch to
**blue-green** for releases that change request/response shape or migrate
config — the all-or-nothing cutover prevents mixed-version traffic.

---

## 6. Bonus — Automated Analysis

The `AnalysisTemplate` runs an HTTP probe against the active Service's
`/health/` endpoint and decides per-metric whether the rollout should
continue. If `failureLimit` is exceeded the canary aborts automatically.

### 6.1 Template definition

`templates/analysistemplate.yaml` (rendered when `rollout.analysis.enabled=true`):

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: python-app-success-rate
spec:
  metrics:
    - name: webcheck
      provider:
        web:
          url: http://python-app-devops-info-service.<ns>.svc:80/health/
          jsonPath: "{$.status}"
      successCondition: 'result == "ok"'
      interval: 10s
      count: 3
      failureLimit: 1
```

* `interval` — how often to probe.
* `count` — how many probes constitute one analysis run.
* `failureLimit` — number of failures within `count` that triggers a failure
  verdict and aborts the rollout.

### 6.2 Wiring it into the canary

`values-canary-analysis.yaml` overrides the canary steps to inject an
`analysis` step right after the first 20% shift:

```yaml
rollout:
  enabled: true
  strategy: canary
  canary:
    steps:
      - setWeight: 20
      - analysis:
          templates:
            - templateName: python-app-success-rate
      - setWeight: 50
      - pause: { duration: 30s }
      - setWeight: 100
  analysis:
    enabled: true
```

Install with:

```bash
helm upgrade --install python-app k8s/devops-info-service \
    -f k8s/devops-info-service/values.yaml \
    -f k8s/devops-info-service/values-canary-analysis.yaml
```

### 6.3 Demonstrating auto-rollback

Force a failure by pointing the analysis at a path that returns a non-`ok`
status (or by deploying a build with a broken `/health/`):

```bash
helm upgrade python-app k8s/devops-info-service \
    -f k8s/devops-info-service/values.yaml \
    -f k8s/devops-info-service/values-canary-analysis.yaml \
    --set image.tag=broken \
    --set rollout.analysis.successCondition='result == "never-matches"'

kubectl argo rollouts get rollout python-app-devops-info-service -w
```

Expected sequence:

1. `setWeight: 20` → canary ReplicaSet at 20%.
2. `analysis` step starts; probes run every 10s.
3. After the first failure the analysis run goes `Failed`.
4. The Rollout enters `Degraded`, the canary is scaled to 0, traffic returns
   100% to stable. No human action required.

![](/k8s/screenshots/anaysis-aborted.png)

---

## 7. CLI Reference

```bash
# inspect
kubectl argo rollouts list rollouts
kubectl argo rollouts get rollout python-app-devops-info-service
kubectl argo rollouts get rollout python-app-devops-info-service -w   # watch

# control
kubectl argo rollouts promote python-app-devops-info-service          # advance one paused step
kubectl argo rollouts promote python-app-devops-info-service --full   # skip all remaining steps
kubectl argo rollouts abort python-app-devops-info-service            # roll back current rollout
kubectl argo rollouts retry rollout python-app-devops-info-service    # resume an aborted rollout
kubectl argo rollouts undo python-app-devops-info-service             # blueGreen → re-flip back

# analysis
kubectl get analysistemplate
kubectl get analysisrun
kubectl describe analysisrun <name>

# images & history
kubectl argo rollouts set image python-app-devops-info-service \
    devops-info-service=morisummerz/devops-info-service:v2
kubectl argo rollouts history rollout python-app-devops-info-service

# dashboard
kubectl port-forward svc/argo-rollouts-dashboard -n argo-rollouts 3100:3100
```

Common troubleshooting:

| Symptom | Likely cause | Fix |
|---|---|---|
| Rollout stuck at `Progressing` forever | `pause: {}` step waiting on manual promote | `kubectl argo rollouts promote …` |
| `AnalysisRun` keeps failing | wrong `url` / namespace / `jsonPath` | `kubectl describe analysisrun <name>` and check `Message` |
| Two ReplicaSets won't scale down (blueGreen) | `scaleDownDelaySeconds` not yet elapsed | wait, or set it lower |
| `Service` selects no pods after install | leftover Deployment from before the conversion | `kubectl delete deploy python-app-devops-info-service`, re-install |
