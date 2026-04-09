# Kubernetes Secrets & HashiCorp Vault

## 1. Kubernetes Secrets

### Creating and Viewing the Secret

```bash
$ kubectl create secret generic app-credentials \
    --from-literal=username=admin \
    --from-literal=password=secret123
secret/app-credentials created
```

```bash
$ kubectl get secret app-credentials -o yaml
apiVersion: v1
data:
  password: c2VjcmV0MTIz
  username: YWRtaW4=
kind: Secret
metadata:
  creationTimestamp: "2026-04-09T18:11:47Z"
  name: app-credentials
  namespace: default
  resourceVersion: "1681987"
  uid: bb7f0f71-462d-450c-beaf-9e4cd2a047ef
type: Opaque
```

### Decoded Secret Values

```bash
$ kubectl get secret app-credentials -o jsonpath='{.data.username}' | base64 -d
admin

$ kubectl get secret app-credentials -o jsonpath='{.data.password}' | base64 -d
secret123
```

### Base64 Encoding vs Encryption

Base64 is a reversible encoding — anyone can decode it. It is not a security mechanism. Kubernetes Secrets are base64-encoded by default, **not encrypted**. Without enabling etcd encryption at rest, secrets are stored in plaintext in etcd. Production clusters should enable `EncryptionConfiguration` and use RBAC to restrict access to Secret resources.

---

## 2. Helm Secret Integration

### Chart Structure

```
k8s/devops-app/templates/
├── secrets.yaml          # Secret resource template
├── serviceaccount.yaml   # ServiceAccount for Vault
├── deployment.yaml       # Consumes secrets via envFrom
├── service.yaml
└── _helpers.tpl
```

### How Secrets Are Consumed

The `templates/secrets.yaml` template creates a Secret from `values.yaml` using `stringData` (auto-encoded):

```yaml
stringData:
  {{- range $key, $value := .Values.secrets }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
```

The deployment injects all keys as environment variables via `envFrom`:

```yaml
envFrom:
  - secretRef:
      name: {{ include "devops-app.fullname" . }}-secret
```

### Verification

```bash
$ kubectl exec $POD -- env | grep -E 'DB_|API_KEY'
API_KEY=<REDACTED>
DB_PASSWORD=<REDACTED>
DB_USERNAME=<REDACTED>
```

All three secret keys are present as environment variables inside the pod.

---

## 3. Resource Management

### Resource Limits Configuration

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

### Requests vs Limits

- **Requests** — minimum guaranteed resources. The scheduler uses these to place pods on nodes. CPU is reserved; memory is guaranteed.
- **Limits** — maximum allowed resources. CPU is throttled when exceeded; memory triggers OOMKill when exceeded.

### Choosing Appropriate Values

- Set **requests** based on observed steady-state usage (`kubectl top pods`).
- Set **limits** at 1.5–2× the request to allow for traffic spikes.
- For a lightweight Flask app: 100m CPU / 128Mi memory requests are sufficient; 200m / 256Mi limits provide headroom.
- Always set both to enable Guaranteed or Burstable QoS class.

---

## 4. Vault Integration

### Vault Installation Verification

```bash
$ kubectl get pods -n vault
NAME                                   READY   STATUS    RESTARTS   AGE
vault-0                                1/1     Running   0          44s
vault-agent-injector-6b4f84b6c-twl58   1/1     Running   0          44s
```

### Policy and Role Configuration

**Policy** (`devops-app-policy`):

```hcl
path "secret/data/devops-app/*" {
  capabilities = ["read"]
}
```

**Role** (`devops-app-role`):

```
bound_service_account_names=devops-app
bound_service_account_namespaces=default
policies=devops-app-policy
ttl=24h
```

### Proof of Secret Injection

Pods run with 2/2 containers (app + vault-agent sidecar):

```bash
$ kubectl get pods -l app.kubernetes.io/name=devops-app
NAME                                     READY   STATUS
devops-dev-devops-app-7db5c69754-5rpjn   2/2     Running
devops-dev-devops-app-7db5c69754-gqtkj   2/2     Running
devops-dev-devops-app-7db5c69754-w5slv   2/2     Running
```

Secret file exists at the expected path:

```bash
$ kubectl exec $POD -c devops-app -- ls -la /vault/secrets/
drwxrwsrwt 2 root appuser   60 Apr  9 19:04 .
-rw-r--r-- 1  100 appuser  213 Apr  9 19:04 config

$ kubectl exec $POD -c devops-app -- cat /vault/secrets/config
data: map[api_key:vault-api-key-xyz789 db_password:vault-secure-pass-456 db_username:admin]
```

### Sidecar Injection Pattern

The Vault Agent Injector uses a Kubernetes mutating admission webhook. When a pod has `vault.hashicorp.com/agent-inject: "true"`, the webhook adds:

1. **Init container** — authenticates with Vault and fetches initial secrets before the app starts.
2. **Sidecar container** — runs alongside the app, refreshing secrets based on TTL.
3. **Shared tmpfs volume** — mounted at `/vault/secrets/`, ensuring secrets are never written to disk.

No application code changes are required — the app reads secrets from files.

---

## 5. Security Analysis

### K8s Secrets vs Vault

| Criteria | K8s Secrets | Vault |
|---|---|---|
| Encryption at rest | Base64 only (etcd encryption optional) | AES-256 encrypted |
| Access control | Kubernetes RBAC | Path-based policies |
| Audit logging | K8s API audit logs only | Built-in audit backend |
| Dynamic secrets | Not supported | Supported (DB creds, cloud IAM) |
| Secret rotation | Manual | Automatic via TTL/leases |
| Versioning | Not supported | KV v2 version history |

### When to Use Each

- **K8s Secrets**: development/testing, simple apps with few static secrets, when etcd encryption is enabled.
- **Vault**: production environments, compliance requirements, dynamic secrets, multi-cluster setups, when audit logging is needed.

### Production Recommendations

1. Enable etcd encryption at rest for K8s Secrets.
2. Use Vault for sensitive credentials (database passwords, API keys).
3. Never commit real secrets to version control — use `--set` flags or external secret operators.
4. Restrict Secret access with RBAC policies.
5. Rotate secrets regularly using Vault's lease/TTL system.
