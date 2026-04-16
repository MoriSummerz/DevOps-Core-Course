# Lab 12 — ConfigMaps & Persistent Volumes

This document covers the visits-counter application upgrade, the ConfigMap-based
configuration, the PVC-backed `/data` volume, and the bonus work on ConfigMap
hot reload.

---

## 1. Application Changes

### Visits counter

`app_python/routes/visits/` adds a file-backed counter guarded by a
`threading.Lock`, with atomic writes via `tmp.replace(target)`:

- `service.py` — `VisitsCounter` reads `visits_file` (configurable via
  `VISITS_FILE`, default `/data/visits`). It returns `0` if the file is missing
  and writes to a sibling `.tmp` file before replacing, so partial writes are
  not visible.
- `router.py` — exposes `GET /visits/` returning `{ "visits": N }`.
- `routes/root/router.py` — the root handler now depends on the counter and
  calls `increment()` on every `GET /`.

Configuration entry point:

```python
# app_python/config.py
class Settings(BaseSettings):
    ...
    visits_file: str = "/data/visits"
```

### New endpoint

| Endpoint | Method | Behavior |
| --- | --- | --- |
| `/` | GET | Returns API info **and increments** the counter |
| `/visits/` | GET | Returns the current count without incrementing |

### Local Docker Compose test

`app_python/docker-compose.yml`:

```yaml
services:
  app:
    build: .
    image: morisummerz/devops-info-service:latest
    ports:
      - "8080:5000"       # port 5000 is taken by macOS AirPlay
    environment:
      VISITS_FILE: "/data/visits"
    volumes:
      - ./data:/data
```

Session output:

```
$ docker compose up -d --build
$ curl -s http://localhost:8080/visits/
{"visits":0}
$ for i in 1 2 3; do curl -s -o /dev/null http://localhost:8080/; done
$ curl -s http://localhost:8080/visits/
{"visits":3}
$ cat data/visits
3
$ docker compose restart
$ curl -s http://localhost:8080/visits/
{"visits":3}
$ curl -s -o /dev/null http://localhost:8080/ && curl -s http://localhost:8080/visits/
{"visits":4}
```

The counter survives `docker compose restart`, confirming the bind-mount
persists the file across container lifecycles.

---

## 2. ConfigMap Implementation

### `files/config.json`

Non-secret application configuration is kept in
`k8s/devops-info-service/files/config.json` so Helm can render it directly via
`.Files.Get`:

```json
{
  "application": {
    "name": "devops-info-service",
    "environment": "dev",
    "owner": "MoriSummerz"
  },
  "features": {
    "visits_counter": true,
    "metrics_endpoint": true,
    "debug_routes": false
  },
  "limits": {
    "max_request_body_bytes": 1048576,
    "request_timeout_seconds": 30
  }
}
```

### `templates/configmap.yaml`

Two ConfigMaps are generated — one holds the JSON file, the other holds env
key-value pairs:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "devops-info-service.fullname" . }}-config
data:
  config.json: |-
{{ .Files.Get "files/config.json" | indent 4 }}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "devops-info-service.fullname" . }}-env
data:
  {{- range $key, $value := .Values.configMapEnv }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
```

`values.yaml` exposes the env entries so they can be overridden per
environment:

```yaml
configMapEnv:
  APP_ENV: "dev"
  LOG_LEVEL: "INFO"
  CONFIG_FILE: "/config/config.json"
```

### Deployment wiring

The deployment mounts the file ConfigMap as a volume and consumes the env
ConfigMap via `envFrom` (see `templates/deployment.yaml`):

```yaml
envFrom:
  - configMapRef:
      name: {{ include "devops-info-service.fullname" . }}-env
  - secretRef:
      name: {{ include "devops-info-service.fullname" . }}-secret
volumeMounts:
  - name: config-volume
    mountPath: /config
    readOnly: true
volumes:
  - name: config-volume
    configMap:
      name: {{ include "devops-info-service.fullname" . }}-config
```

### Verification

```
$ kubectl get configmap
NAME                                  DATA   AGE
devops-devops-info-service-config     1      2m
devops-devops-info-service-env        3      2m
kube-root-ca.crt                      1      5m

$ kubectl exec <pod> -- cat /config/config.json
{
  "application": { "name": "devops-info-service", "environment": "dev", "owner": "MoriSummerz" },
  "features":    { "visits_counter": true, "metrics_endpoint": true, "debug_routes": false },
  "limits":      { "max_request_body_bytes": 1048576, "request_timeout_seconds": 30 }
}

$ kubectl exec <pod> -- sh -c 'printenv | sort' | grep -E "APP_|LOG_|CONFIG_"
APP_ENV=dev
APP_NAME=devops-devops-info-service
APP_VERSION=1.0.0
CONFIG_FILE=/config/config.json
LOG_LEVEL=INFO
```

Volumes section from `kubectl describe pod`:

```
Mounts:
  /config from config-volume (ro)
  /data   from data-volume (rw)
Volumes:
  config-volume:
    Type:      ConfigMap
    Name:      devops-devops-info-service-config
  data-volume:
    Type:      PersistentVolumeClaim
    ClaimName: devops-devops-info-service-data
```

---

## 3. Persistent Volume

### PVC template (`templates/pvc.yaml`)

```yaml
{{- if .Values.persistence.enabled }}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "devops-info-service.fullname" . }}-data
spec:
  accessModes:
    - {{ .Values.persistence.accessMode | default "ReadWriteOnce" }}
  resources:
    requests:
      storage: {{ .Values.persistence.size }}
  {{- if .Values.persistence.storageClass }}
  storageClassName: {{ .Values.persistence.storageClass | quote }}
  {{- end }}
{{- end }}
```

`values.yaml` defaults:

```yaml
persistence:
  enabled: true
  mountPath: /data
  size: 100Mi
  accessMode: ReadWriteOnce
  storageClass: ""   # empty = use default StorageClass
```

### Access mode & storage class

- **ReadWriteOnce (RWO)** — the node holding the pod gets read/write access.
  This is what Minikube's default `standard` storage class supports, and it is
  fine for a single-writer counter. `replicaCount` is therefore pinned to `1`
  in `values.yaml` (multiple pods cannot bind a RWO volume).
- Leaving `storageClass` empty delegates provisioning to the cluster default;
  on Minikube that's `standard` (hostPath via `k8s.io/minikube-hostpath`), on
  GKE it would be `standard-rwo`, etc.

### Mount in deployment

```yaml
volumeMounts:
  - name: data-volume
    mountPath: /data
volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: {{ include "devops-info-service.fullname" . }}-data
```

The container reads/writes `/data/visits`, which matches `VISITS_FILE` in
`values.yaml`.

### Persistence test

```
$ kubectl get pvc
NAME                                STATUS   VOLUME  CAPACITY  ACCESS MODES  STORAGECLASS
devops-devops-info-service-data     Bound    pvc-…   100Mi     RWO           standard

$ curl -s http://localhost:8081/visits/
{"visits":0}
$ for i in 1 2 3 4 5; do curl -s -o /dev/null http://localhost:8081/; done
$ curl -s http://localhost:8081/visits/
{"visits":5}
$ kubectl exec <pod> -- cat /data/visits
5

$ kubectl delete pod devops-devops-info-service-6979c68dc7-8pf8b
pod "devops-devops-info-service-6979c68dc7-8pf8b" deleted

$ kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=devops-info-service
pod/devops-devops-info-service-6979c68dc7-g8krh condition met

$ kubectl exec devops-devops-info-service-6979c68dc7-g8krh -- cat /data/visits
5
$ curl -s http://localhost:8082/visits/
{"visits":5}
```

The counter held at `5` across pod deletion, across two `helm upgrade`
operations, and across the checksum-triggered rolling restart (see bonus
section below) — the PVC is decoupled from pod lifecycle.

---

## 4. ConfigMap vs. Secret

| | ConfigMap | Secret |
| --- | --- | --- |
| **Purpose** | Non-sensitive app config | Credentials, tokens, certs |
| **Storage** | Plain text in etcd | Base64-encoded in etcd (optionally encrypted at rest) |
| **Access** | `get configmap <name>` shows content | `get secret <name>` hides `data` by default |
| **Mount** | As file(s) or env vars | Same (file/env) |
| **Audit** | Safe to commit rendered YAML | Never commit; use SealedSecrets / Vault / ExternalSecrets |
| **Size limit** | ~1 MiB per object | ~1 MiB per object |
| **Good for** | `config.json`, feature flags, log levels, endpoints | `DB_PASSWORD`, `API_KEY`, TLS keys |

Rule of thumb: if leaking the value would force a rotation, it belongs in a
Secret (Lab 11 — SealedSecrets, Vault injector). Everything else goes into a
ConfigMap so it can live alongside the code, be diffed in PRs, and be rendered
into Helm templates without extra tooling.

---

## Bonus — ConfigMap Hot Reload

### Default kubelet update delay

Kubelet periodically resyncs mounted ConfigMaps; the effective delay is
`syncFrequency (default 1m) + cache TTL`, so several tens of seconds is
expected.

Measured on this cluster:

```
$ kubectl patch configmap devops-devops-info-service-config --type merge \
    -p '{"data":{"config.json":"{\"application\":{\"environment\":\"dev-UPDATED\"}}"}}'
configmap/devops-devops-info-service-config patched

# Polling the file inside the pod until the new value appears:
=== propagated after 26s ===
{"application":{"name":"devops-info-service","environment":"dev-UPDATED",...}}
```

26 s in this run, and it varies with the kubelet sync window.

### `subPath` caveat

Using `subPath` in a `volumeMount` copies the file once at pod start and
**does not receive updates** — the mount is a bind of a single path from the
volume, not the symlinked directory kubelet maintains for live updates. So:

- **Full-directory mount** (what this chart uses, `mountPath: /config`) —
  auto-updates after the sync window.
- **`subPath: config.json`** — frozen at pod creation; the only way to refresh
  is to restart the pod.

Use `subPath` when you need to overlay a single file next to existing
container files (e.g. a sidecar's own configs) and explicitly *don't* want
auto-reload; otherwise avoid it.

### Chosen reload approach — checksum annotation

The deployment template includes:

```yaml
spec:
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

Any change to the rendered ConfigMap YAML changes the hash, which changes the
pod template, which triggers a rolling update on `helm upgrade`. That gives
deterministic "config change → pod restart" semantics without waiting for the
kubelet sync window, and without adding a sidecar.

Evidence:

```
$ POD_BEFORE=$(kubectl get pod -l app.kubernetes.io/name=devops-info-service -o jsonpath='{.items[0].metadata.name}')
devops-devops-info-service-6979c68dc7-g8krh

# flip debug_routes in files/config.json, then:
$ helm upgrade devops devops-info-service -f devops-info-service/values-dev.yaml

$ POD_AFTER=$(kubectl get pod -l app.kubernetes.io/name=devops-info-service -o jsonpath='{.items[0].metadata.name}')
devops-devops-info-service-5475d695bf-f75hd

✓ checksum annotation triggered rolling restart
```

Rendered annotation:

```
$ kubectl get deploy devops-devops-info-service -o jsonpath='{.spec.template.metadata.annotations}'
{ "checksum/config": "f1bcb91d98003b656e68f105d2b3fb876a5f1e8c934a138d844963208be0a6f1" }
```

**Alternatives considered**

- **Application file-watching** — viable, but it forces every service to own
  reload logic and handle half-written files. Overkill here.
- **Stakater Reloader sidecar/controller** — great for teams with many charts
  that don't want the checksum boilerplate; would require a cluster-wide
  install. Not needed for one chart.
- **Manual `kubectl rollout restart deployment/...`** — works but is imperative
  and out-of-band of Helm; easy to forget in CI.

---

## Reproduction

```bash
# 1. Minikube cluster for the lab
minikube start -p lab12 --driver=docker

# 2. Build the image inside the minikube Docker daemon
eval $(minikube -p lab12 docker-env)
docker build -t morisummerz/devops-info-service:latest app_python

# 3. Install the chart
cd k8s
helm install devops devops-info-service -f devops-info-service/values-dev.yaml

# 4. Verify
kubectl get all,configmap,pvc
POD=$(kubectl get pod -l app.kubernetes.io/name=devops-info-service -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD -- cat /config/config.json
kubectl exec $POD -- printenv | grep -E "APP_|LOG_|CONFIG_"
kubectl port-forward svc/devops-devops-info-service 8081:80 &
curl -s http://localhost:8081/visits/
```

## Teardown

```bash
helm uninstall devops
kubectl delete pvc --all           # PVC does not auto-delete with the release
minikube delete -p lab12
```
