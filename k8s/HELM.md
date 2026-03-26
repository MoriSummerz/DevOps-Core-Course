# Helm Chart Documentation — devops-info-service

## Chart Overview

### Chart Structure

```
k8s/
├── devops-info-service/            # Primary application chart
│   ├── Chart.yaml                  # Chart metadata (name, version, appVersion)
│   ├── values.yaml                 # Default configuration values
│   ├── values-dev.yaml             # Development environment overrides
│   ├── values-prod.yaml            # Production environment overrides
│   └── templates/
│       ├── _helpers.tpl            # Reusable template helpers (names, labels)
│       ├── deployment.yaml         # Deployment manifest template
│       ├── service.yaml            # Service manifest template
│       ├── NOTES.txt               # Post-install usage instructions
│       └── hooks/
│           ├── pre-install-job.yaml    # Pre-install validation hook
│           └── post-install-job.yaml   # Post-install smoke test hook
│
├── devops-info-service-v2/         # Second app chart (uses library)
│   ├── Chart.yaml                  # Declares common-lib dependency
│   ├── values.yaml                 # Default values for v2
│   └── templates/
│       ├── deployment.yaml         # Uses common.* helpers from library
│       └── service.yaml            # Uses common.* helpers from library
│
└── common-lib/                     # Library chart (shared templates)
    ├── Chart.yaml                  # type: library
    └── templates/
        ├── _names.tpl              # Name generation helpers
        └── _labels.tpl             # Label generation helpers
```

### Key Template Files

| File | Purpose |
|------|---------|
| `_helpers.tpl` | Defines reusable named templates for name generation, labels, and selectors |
| `deployment.yaml` | Templatized Deployment with configurable replicas, resources, probes, strategy, and env vars |
| `service.yaml` | Templatized Service with configurable type, ports, and optional NodePort |
| `hooks/pre-install-job.yaml` | Validation job that runs before chart installation/upgrade |
| `hooks/post-install-job.yaml` | Smoke test job that verifies the service after installation/upgrade |
| `NOTES.txt` | Dynamic post-install instructions based on service type |

### Values Organization Strategy

Values are structured hierarchically by concern:
- **Top-level**: `replicaCount`, `containerPort` — simple scalars
- **image.\***: Container image configuration (repository, tag, pullPolicy)
- **service.\***: Service type, ports, and NodePort settings
- **strategy.\***: Rolling update configuration
- **resources.\***: CPU/memory requests and limits
- **livenessProbe/readinessProbe**: Health check configuration (never disabled)
- **env**: Environment variables passed to the container

## Configuration Guide

### Important Values

| Value | Default | Description |
|-------|---------|-------------|
| `replicaCount` | `3` | Number of pod replicas |
| `image.repository` | `morisummerz/devops-info-service` | Docker image repository |
| `image.tag` | `latest` | Image tag (defaults to `appVersion` if empty) |
| `image.pullPolicy` | `Never` | Image pull policy (`Never` for minikube local builds) |
| `containerPort` | `5000` | Port the application listens on |
| `service.type` | `NodePort` | Kubernetes service type |
| `service.port` | `80` | Service port exposed to cluster |
| `service.targetPort` | `5000` | Target port on the container |
| `service.nodePort` | `30080` | NodePort for external access (30000-32767) |
| `strategy.type` | `RollingUpdate` | Deployment update strategy |
| `strategy.rollingUpdate.maxSurge` | `1` | Max extra pods during rolling update |
| `strategy.rollingUpdate.maxUnavailable` | `0` | Max unavailable pods during update |
| `resources.requests.cpu` | `100m` | CPU request per pod |
| `resources.requests.memory` | `128Mi` | Memory request per pod |
| `resources.limits.cpu` | `200m` | CPU limit per pod |
| `resources.limits.memory` | `256Mi` | Memory limit per pod |
| `livenessProbe.httpGet.path` | `/health/` | Liveness check endpoint |
| `readinessProbe.httpGet.path` | `/health/` | Readiness check endpoint |

### Environment-Specific Customization

**Development** (`values-dev.yaml`):
- 1 replica (minimal resource usage)
- Relaxed resource limits (50m/64Mi → 100m/128Mi)
- DEBUG mode enabled
- Longer failure thresholds (5 attempts)
- NodePort service for direct access

**Production** (`values-prod.yaml`):
- 5 replicas (high availability)
- Higher resources (200m/256Mi → 500m/512Mi)
- DEBUG disabled
- Longer initial delays for probes (30s liveness, 10s readiness)
- LoadBalancer service type
- More aggressive rolling update (maxSurge: 2, maxUnavailable: 1)

### Example Installations

```bash
# Default configuration (3 replicas, NodePort)
helm install devops-app k8s/devops-info-service

# Development environment
helm install devops-dev k8s/devops-info-service -f k8s/devops-info-service/values-dev.yaml

# Production environment
helm install devops-prod k8s/devops-info-service -f k8s/devops-info-service/values-prod.yaml

# Override specific value at install time
helm install devops-custom k8s/devops-info-service --set replicaCount=10 --set service.type=ClusterIP
```

## Hook Implementation

### Hooks Overview

| Hook | Type | Weight | Purpose | Deletion Policy |
|------|------|--------|---------|----------------|
| `pre-install-job` | `pre-install, pre-upgrade` | `-5` | Validates environment before deployment | `hook-succeeded, before-hook-creation` |
| `post-install-job` | `post-install, post-upgrade` | `5` | Smoke tests service health after deployment | `hook-succeeded, before-hook-creation` |

### Execution Order

1. **Pre-install hook** (weight: -5) runs first — validates release metadata and environment
2. Kubernetes resources (Deployment, Service) are created
3. **Post-install hook** (weight: 5) runs after resources are ready — performs health check against the deployed service

### Hook Weights

- Negative weight (-5) ensures pre-install runs before any other hooks
- Positive weight (5) ensures post-install runs after any other hooks
- Lower weight = earlier execution

### Deletion Policies

- **`hook-succeeded`**: Automatically deletes the hook Job and its Pod after successful completion, keeping the cluster clean
- **`before-hook-creation`**: Deletes any previous instance of the hook before creating a new one (prevents name conflicts during upgrades)

### Hook Execution Evidence

```
$ kubectl get events --sort-by=.lastTimestamp | grep -E "pre-install|post-install"
Normal  SuccessfulCreate  job/devops-app-devops-info-service-pre-install   Created pod
Normal  Completed         job/devops-app-devops-info-service-pre-install   Job completed
Normal  SuccessfulCreate  job/devops-app-devops-info-service-post-install  Created pod
Normal  Completed         job/devops-app-devops-info-service-post-install  Job completed

$ kubectl get jobs
No resources found in default namespace.
# ↑ Jobs deleted per hook-succeeded policy
```

## Installation Evidence

### helm list

```
$ helm list
NAME         	NAMESPACE	REVISION	UPDATED                             	STATUS  	CHART                       	APP VERSION
devops-app   	default  	1       	2026-03-24 20:11:26.855236 +0300 MSK	deployed	devops-info-service-0.1.0   	1.0.0
devops-app-v2	default  	1       	2026-03-24 20:13:54.342729 +0300 MSK	deployed	devops-info-service-v2-0.1.0	1.0.0
```

### kubectl get all

```
$ kubectl get all
NAME                                                       READY   STATUS    RESTARTS   AGE
pod/devops-app-devops-info-service-779f7fd898-59sl9        1/1     Running   0          2m38s
pod/devops-app-v2-devops-info-service-v2-69df874b9-5g4gb   1/1     Running   0          19s
pod/devops-app-v2-devops-info-service-v2-69df874b9-tjs76   1/1     Running   0          19s

NAME                                           TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
service/devops-app-devops-info-service         NodePort    10.97.200.240    <none>        80:30080/TCP   2m38s
service/devops-app-v2-devops-info-service-v2   ClusterIP   10.102.247.188   <none>        80/TCP         19s

NAME                                                   READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-app-devops-info-service         1/1     1            1           2m38s
deployment.apps/devops-app-v2-devops-info-service-v2   2/2     2            2           19s
```

### Dev vs Prod Deployment Comparison

**Dev deployment (1 replica):**
```
$ helm install devops-dev k8s/devops-info-service -f k8s/devops-info-service/values-dev.yaml
$ kubectl get deployment devops-dev-devops-info-service
NAME                             READY   UP-TO-DATE   AVAILABLE
devops-dev-devops-info-service   1/1     1            1
```

**Upgraded to Prod values (5 replicas):**
```
$ helm upgrade devops-dev k8s/devops-info-service -f k8s/devops-info-service/values-prod.yaml
$ kubectl get deployment devops-dev-devops-info-service
NAME                             READY   UP-TO-DATE   AVAILABLE
devops-dev-devops-info-service   5/5     5            5
```

<!-- TODO: Add screenshots of Helm deployments in Kubernetes dashboard if needed -->

## Operations

### Installation

```bash
# Install with default values
helm install devops-app k8s/devops-info-service

# Install with environment-specific values
helm install devops-app k8s/devops-info-service -f k8s/devops-info-service/values-dev.yaml

# Install with --wait to block until ready
helm install devops-app k8s/devops-info-service --wait --timeout 120s
```

### Upgrade

```bash
# Upgrade to new values
helm upgrade devops-app k8s/devops-info-service -f k8s/devops-info-service/values-prod.yaml

# Upgrade with specific value override
helm upgrade devops-app k8s/devops-info-service --set replicaCount=5

# Upgrade with --wait to ensure zero-downtime
helm upgrade devops-app k8s/devops-info-service --wait --timeout 120s
```

### Rollback

```bash
# View release history
helm history devops-app

# Rollback to previous revision
helm rollback devops-app

# Rollback to specific revision
helm rollback devops-app 1
```

### Uninstall

```bash
# Remove release and all its resources
helm uninstall devops-app

# Dry-run to preview what would be deleted
helm uninstall devops-app --dry-run
```

## Testing & Validation

### helm lint

```
$ helm lint k8s/devops-info-service
==> Linting k8s/devops-info-service
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

### helm template

```
$ helm template test-release k8s/devops-info-service
---
# Source: devops-info-service/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: test-release-devops-info-service
  labels:
    helm.sh/chart: devops-info-service-0.1.0
    app.kubernetes.io/name: devops-info-service
    app.kubernetes.io/instance: test-release
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/managed-by: Helm
spec:
  type: NodePort
  ports:
    - port: 80
      targetPort: 5000
      protocol: TCP
      name: http
      nodePort: 30080
  selector:
    app.kubernetes.io/name: devops-info-service
    app.kubernetes.io/instance: test-release
---
# Source: devops-info-service/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-release-devops-info-service
  labels: ...
spec:
  replicas: 3
  strategy:
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
    type: RollingUpdate
  template:
    spec:
      containers:
        - name: devops-info-service
          image: "morisummerz/devops-info-service:latest"
          imagePullPolicy: Never
          ports:
            - name: http
              containerPort: 5000
          livenessProbe:
            httpGet:
              path: /health/
              port: 5000
          readinessProbe:
            httpGet:
              path: /health/
              port: 5000
          resources:
            limits:
              cpu: 200m
              memory: 256Mi
            requests:
              cpu: 100m
              memory: 128Mi
```

### Dry-Run

```bash
$ helm install --dry-run --debug test-release k8s/devops-info-service
# Renders all templates and shows the full output without applying to cluster
# Useful for catching template errors before deployment
```

### Application Verification

```
$ curl -s http://127.0.0.1:56902/health/
{
    "status": "healthy",
    "timestamp": "2026-03-24T17:11:40.123456Z",
    "uptime_seconds": 14
}

$ curl -s http://127.0.0.1:56902/ | jq .service
{
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "FastAPI"
}
```

---

## Bonus: Library Charts

### Library Chart Structure

The `common-lib` chart (`type: library`) provides shared template helpers used by both application charts, eliminating code duplication.

**Shared templates:**

| Template | Purpose |
|----------|---------|
| `common.name` | Generates chart name (truncated to 63 chars) |
| `common.fullname` | Generates release-qualified app name |
| `common.chart` | Generates chart name + version string |
| `common.labels` | Standard Kubernetes labels (chart, name, instance, version, managed-by) |
| `common.selectorLabels` | Minimal selector labels (name, instance) |

### How Both Apps Use the Library

**devops-info-service** (primary chart): Uses its own `_helpers.tpl` with `devops-info-service.*` template definitions (standalone chart).

**devops-info-service-v2** (second chart): Declares `common-lib` as a dependency and uses `common.*` template definitions from the library:

```yaml
# devops-info-service-v2/Chart.yaml
dependencies:
  - name: common-lib
    version: 0.1.0
    repository: "file://../common-lib"

# devops-info-service-v2/templates/deployment.yaml
metadata:
  name: {{ include "common.fullname" . }}
  labels:
    {{- include "common.labels" . | nindent 4 }}
```

### Benefits

| Benefit | Description |
|---------|-------------|
| **DRY** | Label and name logic defined once, used everywhere |
| **Consistency** | All charts produce the same label structure and naming convention |
| **Maintainability** | Fix a label bug once in the library, all charts get the fix |
| **Standardization** | Enforces Kubernetes recommended labels across all apps |

### Verification

```
$ helm dependency update k8s/devops-info-service-v2
Saving 1 charts
Deleting outdated charts

$ helm install devops-app-v2 k8s/devops-info-service-v2
NAME: devops-app-v2
STATUS: deployed
CHART: devops-info-service-v2-0.1.0
```

Both charts deploy successfully with consistent labels generated by the shared library.
