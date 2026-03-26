# Kubernetes Deployment — devops-info-service

## Architecture Overview

```
                          ┌──────────────────────────────────────────┐
                          │            Minikube Cluster               │
                          │                                          │
                          │  ┌─────────────────────────────────┐     │
   HTTPS (/app1, /app2)   │  │   NGINX Ingress Controller      │     │
  ───────────────────────▶│  │   (TLS termination + routing)   │     │
                          │  └───────────┬────────────┬────────┘     │
                          │              │            │               │
                          │         /app1│       /app2│               │
                          │              ▼            ▼               │
                          │  ┌────────────────┐ ┌────────────────┐   │
                          │  │ Service        │ │ Service        │   │
                          │  │ devops-info-   │ │ devops-info-   │   │
                          │  │ service        │ │ service-v2     │   │
                          │  │ (NodePort)     │ │ (ClusterIP)    │   │
                          │  └───┬───┬───┬───┘ └───┬───┬────────┘   │
                          │      │   │   │         │   │             │
                          │      ▼   ▼   ▼         ▼   ▼             │
                          │  ┌───┐ ┌───┐ ┌───┐  ┌───┐ ┌───┐         │
                          │  │Pod│ │Pod│ │Pod│  │Pod│ │Pod│         │
                          │  │ 1 │ │ 2 │ │ 3 │  │ 1 │ │ 2 │         │
                          │  └───┘ └───┘ └───┘  └───┘ └───┘         │
                          │  ◀─── App v1 ────▶  ◀── App v2 ──▶      │
                          │  (3 replicas)       (2 replicas)         │
                          │  CPU: 100-200m ea   CPU: 100-200m ea     │
                          │  Mem: 128-256Mi ea  Mem: 128-256Mi ea    │
                          └──────────────────────────────────────────┘
```

**Networking flow:**
1. External traffic reaches the NGINX Ingress Controller via minikube tunnel
2. Ingress routes `/app1` → `devops-info-service` Service (3 Pods)
3. Ingress routes `/app2` → `devops-info-service-v2` Service (2 Pods)
4. TLS termination happens at the Ingress layer using a self-signed certificate
5. Direct NodePort access is also available on port 30080 for the primary app

**Resource allocation:** Each pod requests 100m CPU / 128Mi memory with limits of 200m CPU / 256Mi memory, balancing responsiveness with cluster efficiency on a local development setup.

## Manifest Files

| File | Description |
|------|-------------|
| `deployment.yml` | Primary app Deployment — 3 replicas, rolling update, health probes, resource limits |
| `service.yml` | NodePort Service for direct access on port 30080 |
| `deployment-app2.yml` | Second app Deployment (v2) — 2 replicas with DEBUG mode enabled |
| `service-app2.yml` | ClusterIP Service for app2 (ingress-only access) |
| `ingress.yml` | NGINX Ingress with TLS and path-based routing (/app1, /app2) |

### Key Configuration Choices

- **3 replicas** for the primary app: provides high availability while staying reasonable for a local cluster
- **Rolling update strategy** with `maxSurge: 1, maxUnavailable: 0`: ensures zero downtime during deployments by always keeping all replicas available
- **`imagePullPolicy: Never`**: since we build directly into minikube's Docker daemon, avoids unnecessary registry pulls
- **Separate liveness and readiness probes**: liveness restarts unhealthy containers, readiness gates traffic only to ready pods
- **Resource requests/limits**: prevents resource starvation and enables proper Kubernetes scheduling

## Deployment Evidence

### Cluster Setup

```
$ kubectl cluster-info
Kubernetes control plane is running at https://127.0.0.1:32771
CoreDNS is running at https://127.0.0.1:32771/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

$ kubectl get nodes
NAME       STATUS   ROLES           AGE     VERSION
minikube   Ready    control-plane   9m17s   v1.35.1
```

**Tool choice: minikube** — selected for its full-featured local Kubernetes environment with built-in addons (ingress, dashboard), easy Docker driver integration on macOS, and widely available documentation.

### kubectl get all

```
$ kubectl get all
NAME                                          READY   STATUS    RESTARTS   AGE
pod/devops-info-service-589c64455f-562ht      1/1     Running   0          7m44s
pod/devops-info-service-589c64455f-fhqwx      1/1     Running   0          7m56s
pod/devops-info-service-589c64455f-vwfnz      1/1     Running   0          7m30s
pod/devops-info-service-v2-6f4cd49d9c-7glmm   1/1     Running   0          110s
pod/devops-info-service-v2-6f4cd49d9c-rzn5p   1/1     Running   0          110s

NAME                             TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
service/devops-info-service      NodePort    10.105.152.201   <none>        80:30080/TCP   10m
service/devops-info-service-v2   ClusterIP   10.106.157.215   <none>        80/TCP         110s
service/kubernetes               ClusterIP   10.96.0.1        <none>        443/TCP        21m

NAME                                     READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-info-service      3/3     3            3           10m
deployment.apps/devops-info-service-v2   2/2     2            2           110s
```

### kubectl get pods,svc -o wide

```
NAME                                          READY   STATUS    RESTARTS   AGE     IP            NODE       NOMINATED NODE   READINESS GATES
pod/devops-info-service-589c64455f-562ht      1/1     Running   0          7m44s   10.244.0.14   minikube   <none>           <none>
pod/devops-info-service-589c64455f-fhqwx      1/1     Running   0          7m56s   10.244.0.13   minikube   <none>           <none>
pod/devops-info-service-589c64455f-vwfnz      1/1     Running   0          7m30s   10.244.0.16   minikube   <none>           <none>
pod/devops-info-service-v2-6f4cd49d9c-7glmm   1/1     Running   0          110s    10.244.0.22   minikube   <none>           <none>
pod/devops-info-service-v2-6f4cd49d9c-rzn5p   1/1     Running   0          110s    10.244.0.21   minikube   <none>           <none>

NAME                             TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE    SELECTOR
service/devops-info-service      NodePort    10.105.152.201   <none>        80:30080/TCP   10m    app=devops-info-service
service/devops-info-service-v2   ClusterIP   10.106.157.215   <none>        80/TCP         110s   app=devops-info-service-v2
```

### kubectl describe deployment

```
Name:                   devops-info-service
Replicas:               3 desired | 3 updated | 3 total | 3 available | 0 unavailable
StrategyType:           RollingUpdate
RollingUpdateStrategy:  0 max unavailable, 1 max surge
Pod Template:
  Containers:
   devops-info-service:
    Image:      morisummerz/devops-info-service:latest
    Port:       5000/TCP
    Limits:     cpu: 200m, memory: 256Mi
    Requests:   cpu: 100m, memory: 128Mi
    Liveness:   http-get http://:5000/health/ delay=10s timeout=3s period=10s #success=1 #failure=3
    Readiness:  http-get http://:5000/health/ delay=5s timeout=3s period=5s #success=1 #failure=3
```

### Application Response

```json
$ curl -s http://127.0.0.1:56902/
{
    "service": {
        "name": "devops-info-service",
        "version": "1.0.0",
        "description": "DevOps course info service",
        "framework": "FastAPI"
    },
    "system": {
        "hostname": "devops-info-service-589c64455f-4zq7m",
        "platform": "Linux",
        "architecture": "aarch64",
        "cpu_count": 12,
        "python_version": "3.12.13"
    }
}

$ curl -s http://127.0.0.1:56902/health/
{
    "status": "healthy",
    "timestamp": "2026-03-24T16:53:29.566403Z",
    "uptime_seconds": 39
}
```

<!-- TODO: Add screenshots of application running in browser if needed -->

## Operations Performed

### Deployment Commands

```bash
# Build image inside minikube's Docker daemon
eval $(minikube docker-env)
docker build -t morisummerz/devops-info-service:latest app_python/

# Apply manifests
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/service.yml

# Verify
kubectl rollout status deployment/devops-info-service
kubectl get pods -l app=devops-info-service
```

### Scaling Demonstration

```
$ kubectl scale deployment/devops-info-service --replicas=5
deployment.apps/devops-info-service scaled

$ kubectl get pods -l app=devops-info-service
NAME                                   READY   STATUS    RESTARTS   AGE
devops-info-service-589c64455f-4zq7m   1/1     Running   0          66s
devops-info-service-589c64455f-9nm66   1/1     Running   0          12s
devops-info-service-589c64455f-dqj9n   1/1     Running   0          66s
devops-info-service-589c64455f-kvfq7   1/1     Running   0          12s
devops-info-service-589c64455f-xwh8r   1/1     Running   0          66s
```

All 5 replicas reached Running/Ready status within 12 seconds.

### Rolling Update Demonstration

```
# Tag a new image version
docker tag morisummerz/devops-info-service:latest morisummerz/devops-info-service:v1.1.0

# Perform rolling update
$ kubectl set image deployment/devops-info-service \
    devops-info-service=morisummerz/devops-info-service:v1.1.0 --record
deployment.apps/devops-info-service image updated

$ kubectl rollout status deployment/devops-info-service
Waiting for deployment "devops-info-service" rollout to finish: 1 out of 5 new replicas have been updated...
...
deployment "devops-info-service" successfully rolled out
```

Zero-downtime update verified: the rolling update strategy (`maxSurge: 1, maxUnavailable: 0`) ensured all existing pods remained available while new pods were gradually created.

### Rollback Demonstration

```
$ kubectl rollout history deployment/devops-info-service
REVISION  CHANGE-CAUSE
1         <none>
2         kubectl set image ... morisummerz/devops-info-service:v1.1.0 --record=true

$ kubectl rollout undo deployment/devops-info-service
deployment.apps/devops-info-service rolled back

$ kubectl rollout history deployment/devops-info-service
REVISION  CHANGE-CAUSE
2         kubectl set image ... morisummerz/devops-info-service:v1.1.0 --record=true
3         <none>
```

Rollback completed successfully, reverting to the original `latest` image tag.

### Service Access

```bash
# Via NodePort (direct)
minikube service devops-info-service --url
# → http://127.0.0.1:56902

# Via Ingress (HTTPS)
curl -sk -H "Host: local.example.com" https://127.0.0.1:62975/app1
curl -sk -H "Host: local.example.com" https://127.0.0.1:62975/app2
```

## Production Considerations

### Health Checks

| Probe | Path | Purpose | Config |
|-------|------|---------|--------|
| **Liveness** | `/health/` | Restarts container if app becomes unresponsive | delay=10s, period=10s, failure=3 |
| **Readiness** | `/health/` | Removes pod from service if not ready to handle traffic | delay=5s, period=5s, failure=3 |

- **Liveness probe** has a longer initial delay (10s) to allow the application to fully start before checking health
- **Readiness probe** starts earlier (5s) and checks more frequently to quickly detect pods that can accept traffic
- Both use the app's dedicated `/health/` endpoint which returns uptime and status information

### Resource Limits Rationale

| Resource | Request | Limit | Reasoning |
|----------|---------|-------|-----------|
| CPU | 100m | 200m | FastAPI with Uvicorn is lightweight; 100m is sufficient for normal operation with 200m headroom for request spikes |
| Memory | 128Mi | 256Mi | Python baseline ~80Mi; 128Mi request covers steady state, 256Mi limit accommodates temporary memory allocation during request processing |

### Production Improvements

1. **Horizontal Pod Autoscaler (HPA)**: automatically scale replicas based on CPU/memory utilization or custom metrics
2. **Pod Disruption Budgets (PDB)**: guarantee minimum availability during voluntary disruptions (node upgrades, cluster maintenance)
3. **Network Policies**: restrict inter-pod communication to only required paths
4. **Secrets management**: use Kubernetes Secrets or external secret stores (Vault) instead of environment variables for sensitive config
5. **Image versioning**: use specific image tags (not `latest`) with image digest pinning for reproducibility
6. **Namespace isolation**: deploy to a dedicated namespace instead of `default`
7. **Persistent logging**: integrate with centralized logging (EFK/Loki stack from Lab 7)

### Monitoring and Observability

- The application exposes Prometheus metrics at `/metrics` endpoint
- Kubernetes native monitoring via `kubectl top pods` (requires metrics-server)
- Integration with the Prometheus + Grafana stack from Lab 8 via ServiceMonitor CRDs
- Health probe failures are captured as Kubernetes events, visible with `kubectl describe pod`

## Challenges & Solutions

### Challenge 1: Image Pull in Minikube

**Issue:** Default `imagePullPolicy` attempts to pull from a remote registry, failing with `ErrImagePull` for locally-built images.

**Solution:** Set `imagePullPolicy: Never` in the deployment manifest and build images directly inside minikube's Docker daemon using `eval $(minikube docker-env)`.

**Debugging:** Used `kubectl describe pod <name>` to identify the image pull error in the Events section.

### Challenge 2: Ingress Access on macOS with Docker Driver

**Issue:** Minikube with the Docker driver on macOS doesn't expose NodePort services at `localhost` directly, and the Ingress controller isn't directly accessible.

**Solution:** Used `minikube service <name> --url` for NodePort access and `minikube tunnel` for Ingress. For HTTPS testing, used `curl` with `--resolve` or `-H "Host:"` to route to the correct virtual host.

### Challenge 3: Rolling Update Zero-Downtime Verification

**Issue:** Needed to confirm that the rolling update strategy actually maintained availability during image updates.

**Solution:** Configured `maxSurge: 1` and `maxUnavailable: 0` to ensure at least the full replica count is always available. Monitored with `kubectl rollout status` which showed gradual pod replacement without service interruption.

### Key Learnings

- Kubernetes declarative approach makes desired state management intuitive — define what you want, let controllers handle the reconciliation
- Health probes are essential for production readiness — they enable self-healing and traffic management
- Rolling updates with proper strategy settings provide zero-downtime deployments out of the box
- Ingress provides a cleaner HTTP routing layer compared to exposing multiple NodePort services
- Resource requests/limits are crucial for cluster stability and proper scheduling decisions

---

## Bonus: Ingress with TLS

### Second Application Deployment

Deployed `devops-info-service-v2` with 2 replicas running in DEBUG mode as a differentiated second application instance.

### Ingress Controller

```bash
$ minikube addons enable ingress
# Verified NGINX Ingress Controller running:
$ kubectl get pods -n ingress-nginx
NAME                                        READY   STATUS      RESTARTS   AGE
ingress-nginx-controller-596f8778bc-xpt9g   1/1     Running     0          5m
```

### TLS Certificate

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=local.example.com/O=local.example.com"

# Create Kubernetes TLS secret
kubectl create secret tls tls-secret --key tls.key --cert tls.crt
```

### Path-Based Routing Verification

```
$ curl -sk -H "Host: local.example.com" https://127.0.0.1:62975/app1 | jq .system.hostname
"devops-info-service-589c64455f-vwfnz"

$ curl -sk -H "Host: local.example.com" https://127.0.0.1:62975/app2 | jq .system.hostname
"devops-info-service-v2-6f4cd49d9c-7glmm"
```

Different hostnames confirm routing to separate deployments.

### Ingress Benefits over NodePort

| Feature | NodePort | Ingress |
|---------|----------|---------|
| TLS termination | Must handle in app | Handled at ingress layer |
| Path-based routing | Not supported | Native support |
| Port management | Random 30000-32767 range | Standard 80/443 |
| Multiple apps | One NodePort per service | Single entry point |
| Host-based routing | Not supported | Native support |
| Load balancing | Basic round-robin | Configurable algorithms |

<!-- TODO: Add screenshots of ingress routing working in browser if needed -->
