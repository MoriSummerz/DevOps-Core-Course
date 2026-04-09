# Lab 11 — Kubernetes Secrets & HashiCorp Vault

## Table of Contents

- [Kubernetes Secrets](#kubernetes-secrets)
- [Helm Secret Integration](#helm-secret-integration)
- [Resource Management](#resource-management)
- [Vault Integration](#vault-integration)
- [Security Analysis](#security-analysis)
- [Bonus: Vault Agent Templates](#bonus-vault-agent-templates)

---

## Kubernetes Secrets

### Creating a Secret

```bash
$ kubectl create secret generic app-credentials \
    --from-literal=username=admin \
    --from-literal=password=S3cur3P@ssw0rd
secret/app-credentials created
```

### Viewing the Secret (YAML)

```bash
$ kubectl get secret app-credentials -o yaml
apiVersion: v1
data:
  password: UzNjdXIzUEBzc3cwcmQ=
  username: YWRtaW4=
kind: Secret
metadata:
  creationTimestamp: "2026-04-09T18:43:16Z"
  name: app-credentials
  namespace: default
type: Opaque
```

### Decoding Base64 Values

```bash
$ echo 'YWRtaW4=' | base64 -d
admin

$ echo 'UzNjdXIzUEBzc3cwcmQ=' | base64 -d
S3cur3P@ssw0rd
```

### Base64 Encoding vs Encryption

| Aspect | Base64 Encoding | Encryption |
|--------|----------------|------------|
| **Purpose** | Binary-to-text representation | Confidentiality protection |
| **Security** | None — trivially reversible | Strong — requires a key to decrypt |
| **K8s Default** | Secrets are base64-encoded | Not enabled by default |
| **Reversibility** | Anyone can decode | Only key holders can decrypt |

**Key Insight:** Kubernetes Secrets are **not encrypted** at rest by default — they are merely base64-encoded in etcd. This means anyone with etcd access or API access to read secrets can trivially decode them.

**etcd Encryption:** Should be enabled in production via `EncryptionConfiguration` with a provider like `aescbc`, `aesgcm`, or a KMS plugin. This encrypts secret data before it is written to etcd.

---

## Helm Secret Integration

### Chart Structure

```
k8s/devops-info-service/
├── Chart.yaml
├── values.yaml                    # Default values with placeholder secrets
├── values-vault.yaml              # Vault-enabled values
├── templates/
│   ├── _helpers.tpl               # Named templates (incl. envVars)
│   ├── deployment.yaml            # Consumes secrets via envFrom
│   ├── secrets.yaml               # Secret resource template
│   ├── service.yaml
│   ├── serviceaccount.yaml
│   └── hooks/
│       ├── pre-install-job.yaml
│       └── post-install-job.yaml
```

### Secret Template (`templates/secrets.yaml`)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "devops-info-service.fullname" . }}-secret
  labels:
    {{- include "devops-info-service.labels" . | nindent 4 }}
type: Opaque
stringData:
  {{- range $key, $value := .Values.secrets }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
```

### Secret Values in `values.yaml`

```yaml
secrets:
  DB_USERNAME: "changeme"
  DB_PASSWORD: "changeme"
  API_KEY: "changeme"
```

Real values are injected at deploy time via `--set` or values files — never committed to Git.

### Consuming Secrets in Deployment

The deployment uses `envFrom` with `secretRef` to inject all secret keys as environment variables:

```yaml
envFrom:
  - secretRef:
      name: {{ include "devops-info-service.fullname" . }}-secret
```

### Verification

```bash
# Environment variables inside the pod:
$ kubectl exec <pod> -- env | grep -E "DB_USERNAME|DB_PASSWORD|API_KEY"
DB_USERNAME=admin
API_KEY=my-secret-api-key-123
DB_PASSWORD=S3cur3P@ssw0rd

# Secrets are NOT visible in kubectl describe (only the reference):
$ kubectl describe pod <pod> | grep -A3 "Environment"
    Environment Variables from:
      devops-app-devops-info-service-secret  Secret  Optional: false
    Environment:
      HOST:   0.0.0.0
```

---

## Resource Management

### Configuration

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 200m
    memory: 256Mi
```

### Requests vs Limits

| Aspect | Requests | Limits |
|--------|----------|--------|
| **Purpose** | Guaranteed minimum resources | Maximum allowed resources |
| **Scheduling** | Used by scheduler for pod placement | Not used for scheduling |
| **Enforcement** | Soft — pod can use more if available | Hard — pod is killed (OOM) or throttled (CPU) |
| **Best Practice** | Set based on average usage | Set based on peak usage + headroom |

### Choosing Appropriate Values

1. **Start with observation:** Monitor actual resource usage via `kubectl top pods` or Prometheus metrics
2. **Requests:** Set to p50 (median) usage — ensures reliable scheduling
3. **Limits:** Set to 1.5-2x requests — prevents runaway processes without over-constraining
4. **Memory:** Be conservative with limits (OOM kills are disruptive)
5. **CPU:** Can be more generous (throttling is less disruptive than killing)

---

## Vault Integration

### Installation

Vault was installed via Helm in dev mode:

```bash
$ helm install vault hashicorp/vault \
    --set "server.dev.enabled=true" \
    --set "injector.enabled=true"
```

### Running Pods

```
$ kubectl get pods
NAME                                             READY   STATUS    RESTARTS   AGE
devops-app-devops-info-service-9d9f68d4c-dfgqj   2/2     Running   0          70s
vault-0                                          1/1     Running   0          16m
vault-agent-injector-848dd747d7-9dqz4            1/1     Running   0          16m
```

Note: The application pod shows **2/2** containers — the app container plus the Vault Agent sidecar.

### Vault Configuration

**Secrets stored:**

```bash
$ vault kv put secret/devops/config \
    db_username="admin" \
    db_password="VaultS3cur3P@ss" \
    api_key="vault-api-key-abc123"
```

**Policy (`devops-app`):**

```hcl
path "secret/data/devops/config" {
  capabilities = ["read"]
}
```

**Kubernetes Auth Role:**

```bash
$ vault write auth/kubernetes/role/devops-app \
    bound_service_account_names=devops-app-devops-info-service \
    bound_service_account_namespaces=default \
    policies=devops-app \
    ttl=24h
```

### Secret Injection Proof

```bash
$ kubectl exec <pod> -c devops-info-service -- cat /vault/secrets/config
DB_USERNAME=admin
DB_PASSWORD=VaultS3cur3P@ss
API_KEY=vault-api-key-abc123
```

### Sidecar Injection Pattern

The Vault Agent Injector uses a **mutating admission webhook** to automatically inject a Vault Agent sidecar into pods with the appropriate annotations:

1. **Init Container (`vault-agent-init`):** Runs before the app container, authenticates with Vault, retrieves secrets, and writes them to a shared volume at `/vault/secrets/`
2. **Sidecar Container (`vault-agent`):** Runs alongside the app container, continuously watches for secret changes and refreshes the files
3. **Shared Volume:** An `emptyDir` volume is mounted into both the sidecar and the app container

```
┌─────────────────────────────────────────┐
│ Pod                                      │
│  ┌────────────────┐ ┌────────────────┐  │
│  │  vault-agent   │ │  app container │  │
│  │  (sidecar)     │ │                │  │
│  └───────┬────────┘ └───────┬────────┘  │
│          │    /vault/secrets/│           │
│          └──────┬───────────┘           │
│           emptyDir volume               │
└─────────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │  Vault Server │
    │  (vault-0)    │
    └──────────────┘
```

---

## Security Analysis

### Kubernetes Secrets vs HashiCorp Vault

| Feature | K8s Secrets | HashiCorp Vault |
|---------|-------------|-----------------|
| **Encryption at rest** | Optional (etcd encryption) | Always encrypted |
| **Access control** | RBAC (namespace-level) | Fine-grained policies (path-level) |
| **Audit logging** | K8s audit logs | Built-in detailed audit logs |
| **Secret rotation** | Manual | Automatic with dynamic secrets |
| **Dynamic secrets** | No | Yes (database creds, cloud IAM, etc.) |
| **Lease/TTL** | No | Yes — secrets expire automatically |
| **Multi-cluster** | No (namespace-scoped) | Yes — centralized secret management |
| **Complexity** | Low | Higher (requires Vault infrastructure) |
| **Setup effort** | Minimal | Significant (HA, unsealing, backup) |

### When to Use Each

**Kubernetes Secrets** — suitable for:
- Development and staging environments
- Non-critical configuration that needs basic protection
- Small teams with simple RBAC requirements
- Quick prototyping and testing

**HashiCorp Vault** — recommended for:
- Production environments with compliance requirements
- Dynamic secrets (database credentials, cloud tokens)
- Multi-cluster or multi-cloud secret management
- Audit trail requirements
- Secret rotation and lease management

### Production Recommendations

1. **Always enable etcd encryption at rest** — even when using Vault, K8s secrets may still exist
2. **Use RBAC** to restrict who can read secrets — principle of least privilege
3. **Never commit secrets to Git** — use placeholder values in `values.yaml`
4. **Implement secret rotation** — Vault's dynamic secrets or external-secrets-operator
5. **Enable audit logging** — both Kubernetes and Vault audit logs
6. **Use namespaces** to isolate secrets between teams/environments
7. **Consider External Secrets Operator** as a bridge between cloud secret managers and K8s

---

## Bonus: Vault Agent Templates

### Template Annotation

Instead of the default raw Vault output, we use a template annotation to render secrets in `.env` format:

```yaml
vault.hashicorp.com/agent-inject-template-config: |
  {{- with secret "secret/data/devops/config" -}}
  DB_USERNAME={{ .Data.data.db_username }}
  DB_PASSWORD={{ .Data.data.db_password }}
  API_KEY={{ .Data.data.api_key }}
  {{- end -}}
```

**Rendered output** (`/vault/secrets/config`):

```
DB_USERNAME=admin
DB_PASSWORD=VaultS3cur3P@ss
API_KEY=vault-api-key-abc123
```

This format is directly consumable by applications that read `.env` files or can be sourced in shell scripts.

### Dynamic Secret Rotation

Vault Agent automatically refreshes secrets based on their TTL:

- The sidecar continuously watches Vault for secret changes
- When a secret is updated in Vault, the agent re-renders the template file
- The **`vault.hashicorp.com/agent-inject-command-*`** annotation specifies a command to run after secrets are updated (e.g., send SIGHUP to reload the app):

```yaml
vault.hashicorp.com/agent-inject-command-config: "/bin/sh -c 'kill -HUP $(pidof python) 2>/dev/null || true'"
```

This enables zero-downtime secret rotation — the app gets notified to reload its configuration when secrets change.

### Named Templates (`_helpers.tpl`)

A named template consolidates common environment variables to follow the DRY principle:

```yaml
{{- define "devops-info-service.envVars" -}}
- name: APP_NAME
  value: {{ include "devops-info-service.fullname" . }}
- name: APP_VERSION
  value: {{ .Chart.AppVersion | quote }}
- name: RELEASE_NAME
  value: {{ .Release.Name }}
{{- range .Values.env }}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end }}
{{- end }}
```

**Usage in deployment:**

```yaml
env:
  {{- include "devops-info-service.envVars" . | nindent 12 }}
```

**Benefits:**
- **DRY:** Common env vars defined once, reusable across multiple templates
- **Consistency:** All deployments get the same base environment variables
- **Maintainability:** Changes to common env vars only need to happen in one place
- **Extensibility:** Easy to add new common variables without modifying every deployment
