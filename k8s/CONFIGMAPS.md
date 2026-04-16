# ConfigMaps & Persistent Volumes — Lab Report

## Application Changes

### Visits Counter Implementation

The Flask application was extended with a file-based visits counter:

- **Counter logic**: Each `GET /` request increments a counter stored in a file at `$DATA_DIR/visits` (configurable via `DATA_DIR` env var, defaults to `/app/data`)
- **Thread safety**: A `threading.Lock` protects concurrent read/write operations
- **Atomic writes**: The counter file is written via a temp file + `os.replace()` to prevent corruption
- **Graceful startup**: If the visits file does not exist, the counter starts at 0

### New Endpoint

| Endpoint     | Method | Description                                    |
|-------------|--------|------------------------------------------------|
| `/visits`   | GET    | Returns the current visit count (without incrementing) |

**Response format:**
```json
{
  "visits": 42
}
```

The root endpoint (`/`) now also returns a `"visits"` field in its response and includes `/visits` in the endpoints list.

### Local Testing with Docker

A `docker-compose.yml` was added to `app_python/` with a volume mount for persistence:

```yaml
volumes:
  - ./data:/app/data
```

---

## ConfigMap Implementation

### File-Based ConfigMap (`configmap.yaml`)

A ConfigMap was created from a static `files/config.json` file using Helm's `.Files.Get` function:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "devops-app.fullname" . }}-config
data:
  config.json: |-
{{ .Files.Get "files/config.json" | indent 4 }}
```

**`config.json` content:**
```json
{
  "app_name": "devops-info-service",
  "environment": "production",
  "version": "1.0.0",
  "features": {
    "visits_counter": true,
    "debug_mode": false
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  }
}
```

### ConfigMap Mounted as a File

The ConfigMap is mounted as a volume in the deployment, making `config.json` available at `/config/config.json` inside the pod:

```yaml
volumes:
  - name: config-volume
    configMap:
      name: {{ include "devops-app.fullname" . }}-config

containers:
  - volumeMounts:
      - name: config-volume
        mountPath: /config
```

**Verification — file content inside pod:**
```
$ kubectl exec devops-app-57544fd5f9-v26hd -- cat /config/config.json
{
  "app_name": "devops-info-service",
  "environment": "production",
  "version": "1.0.0",
  "features": {
    "visits_counter": true,
    "debug_mode": false
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  }
}
```

### Environment Variable ConfigMap (`configmap-env.yaml`)

A second ConfigMap provides key-value pairs as environment variables:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "devops-app.fullname" . }}-env
data:
  APP_ENV: {{ .Values.config.environment | quote }}
  LOG_LEVEL: {{ .Values.config.logLevel | quote }}
  APP_NAME: {{ .Values.config.appName | quote }}
```

The deployment injects these via `envFrom` with `configMapRef`:

```yaml
envFrom:
  - secretRef:
      name: {{ include "devops-app.fullname" . }}-secret
  - configMapRef:
      name: {{ include "devops-app.fullname" . }}-env
```

**Verification — environment variables in pod:**
```
$ kubectl exec devops-app-57544fd5f9-v26hd -- printenv | grep -E "APP_ENV|LOG_LEVEL|APP_NAME"
APP_ENV=production
APP_NAME=devops-info-service
LOG_LEVEL=INFO
```

### `kubectl get configmap,pvc` Output

```
$ kubectl get configmap,pvc
NAME                          DATA   AGE
configmap/devops-app-config   1      38s
configmap/devops-app-env      3      38s
configmap/kube-root-ca.crt    1      2m52s

NAME                                    STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/devops-app-data   Bound    pvc-a25c1488-5b62-44cc-8ed1-a8bd59652214   100Mi      RWO            standard       <unset>                 38s
```

### Environment-Specific Values

| Value              | Default (values.yaml) | Dev (values-dev.yaml) | Prod (values-prod.yaml) |
|--------------------|-----------------------|-----------------------|-------------------------|
| `config.environment` | production          | development           | production              |
| `config.logLevel`    | INFO                | DEBUG                 | WARNING                 |
| `config.appName`     | devops-info-service | devops-info-service   | devops-info-service     |

---

## Persistent Volume

### PVC Configuration

A PersistentVolumeClaim was created via `templates/pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "devops-app.fullname" . }}-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: {{ .Values.persistence.size }}
```

**Values:**
```yaml
persistence:
  enabled: true
  size: 100Mi
  storageClass: ""  # Uses default storage class
```

### Access Modes and Storage Class

- **ReadWriteOnce (RWO)**: The volume can be mounted as read-write by a single node. This is sufficient for Minikube (single-node cluster).
- **Storage Class**: Left empty to use the cluster's default. Minikube provides a `standard` storage class that provisions hostPath volumes automatically.

### Volume Mount Configuration

The PVC is mounted at `/data` in the deployment, and the `DATA_DIR=/data` environment variable directs the application to write the visits file there. The `fsGroup: 999` in the pod security context ensures the mounted volume is writable by the application user.

```yaml
volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: {{ include "devops-app.fullname" . }}-data

containers:
  - env:
      - name: DATA_DIR
        value: "/data"
    volumeMounts:
      - name: data-volume
        mountPath: /data
```

### Persistence Test Evidence

**Before pod deletion** — visits count is 3:
```
$ POD=devops-app-57544fd5f9-v26hd

$ kubectl exec $POD -- python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/visits').read().decode())"
{"visits":3}
```

**Pod deletion:**
```
$ kubectl delete pod devops-app-57544fd5f9-v26hd
pod "devops-app-57544fd5f9-v26hd" deleted
```

**After new pod starts** — visits count is still 3:
```
$ NEW_POD=devops-app-57544fd5f9-qvtrv

$ kubectl exec $NEW_POD -- python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/visits').read().decode())"
{"visits":3}

$ kubectl exec $NEW_POD -- cat /data/visits
3
```

Data survived pod restart. The visits count of 3 was preserved across pod deletion and recreation thanks to the PersistentVolumeClaim.

---

## ConfigMap vs Secret

| Aspect              | ConfigMap                              | Secret                                  |
|---------------------|----------------------------------------|-----------------------------------------|
| **Purpose**         | Non-sensitive configuration data       | Sensitive data (passwords, tokens, keys)|
| **Encoding**        | Plain text                             | Base64-encoded (not encrypted by default)|
| **Size limit**      | 1 MiB                                 | 1 MiB                                   |
| **Use cases**       | App settings, feature flags, config files | DB passwords, API keys, TLS certs     |
| **Access control**  | Standard RBAC                          | Can have stricter RBAC policies         |
| **Encryption**      | Not encrypted                          | Can be encrypted at rest (EncryptionConfiguration) |
| **Mounting**        | Volume or env vars                     | Volume or env vars                      |
| **Best practice**   | Use for all non-sensitive config       | Use for anything sensitive; enable encryption at rest |

**Rule of thumb:** If the data would be a problem if exposed in a Git repo or logs, use a Secret. Otherwise, use a ConfigMap.
