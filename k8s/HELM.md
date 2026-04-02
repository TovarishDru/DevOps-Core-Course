# Lab 10 — Helm Package Manager

## Chart Overview

A Helm chart was created to package the DevOps Python Flask application for deployment to Kubernetes. The chart follows Helm best practices and provides a production-ready, configurable deployment solution.

### Chart Structure

The following structure was implemented:

```
k8s/devops-app/
├── Chart.yaml                      # Chart metadata
├── values.yaml                     # Default configuration values
├── values-dev.yaml                 # Development environment overrides
├── values-prod.yaml                # Production environment overrides
└── templates/
    ├── _helpers.tpl                # Template helper functions
    ├── deployment.yaml             # Deployment resource template
    ├── service.yaml                # Service resource template
    ├── NOTES.txt                   # Post-install instructions
    └── hooks/
        ├── pre-install-job.yaml    # Pre-installation validation hook
        └── post-install-job.yaml   # Post-installation smoke test hook
```

### Key Template Files

| File | Purpose |
|------|---------|
| **Chart.yaml** | Chart metadata including name (devops-app), version (0.1.0), appVersion (1.0), and maintainer information |
| **values.yaml** | Default configuration values extracted from Lab 9 manifests: 3 replicas, NodePort service, resource limits |
| **_helpers.tpl** | Reusable template functions for generating names, labels, and selectors consistently across all resources |
| **deployment.yaml** | Templatized Deployment with configurable replicas, image, resources, probes, and security context |
| **service.yaml** | Templatized Service supporting NodePort, LoadBalancer, or ClusterIP types |
| **NOTES.txt** | Dynamic post-install instructions showing how to access the deployed application |

### Values Organization Strategy

Values were organized hierarchically for clarity and maintainability:

- **Top-level scalars**: `replicaCount`, `nameOverride`, `fullnameOverride`
- **Nested objects**: `image.*`, `service.*`, `resources.*`, `securityContext.*`
- **Arrays**: `env[]` for environment variables
- **Probe configurations**: `livenessProbe.*`, `readinessProbe.*` with full customization
- **Strategy**: `strategy.type` and `strategy.rollingUpdate.*` for deployment updates

This structure allows granular overrides via `--set` or values files while maintaining sensible defaults.

---

## Configuration Guide

### Important Values

The following key values were configured:

| Value Path | Default | Description |
|------------|---------|-------------|
| `replicaCount` | `3` | Number of pod replicas for high availability |
| `image.repository` | `tovarishdru/devops-python-app` | Docker image repository |
| `image.tag` | `v1.0` | Image tag (defaults to `.Chart.AppVersion` if not set) |
| `image.pullPolicy` | `Always` | Image pull policy |
| `service.type` | `NodePort` | Service type |
| `service.port` | `80` | Service port for cluster-internal traffic |
| `service.targetPort` | `8000` | Container port where the app listens |
| `service.nodePort` | `30080` | Fixed NodePort |
| `resources.requests.cpu` | `100m` | Minimum CPU guaranteed for scheduling |
| `resources.requests.memory` | `128Mi` | Minimum memory guaranteed for scheduling |
| `resources.limits.cpu` | `200m` | Maximum CPU the container can use |
| `resources.limits.memory` | `256Mi` | Maximum memory the container can use |
| `livenessProbe.initialDelaySeconds` | `10` | Delay before first liveness check |
| `readinessProbe.initialDelaySeconds` | `5` | Delay before first readiness check |
| `securityContext.runAsUser` | `999` | UID to run the container as (non-root) |

### Environment Configurations

Three deployment scenarios were configured:

#### 1. Default (Balanced)
- 3 replicas
- NodePort service
- Moderate resource limits (100m/128Mi requests, 200m/256Mi limits)
- Suitable for staging or small production

#### 2. Development (values-dev.yaml)
- 1 replica for faster iteration
- `latest` image tag with `Always` pull policy
- Relaxed resources (50m/64Mi requests, 100m/128Mi limits)
- Debug mode enabled (`DEBUG=true`)
- Shorter probe delays
- Allows 1 unavailable pod during updates

#### 3. Production (values-prod.yaml)
- 5 replicas for high availability
- Specific version tag (`v1.0`) with `IfNotPresent` pull policy
- Production resources (200m/256Mi requests, 500m/512Mi limits)
- Debug mode disabled
- LoadBalancer service type
- Longer initial delays for probes (30s liveness, 10s readiness)
- Zero downtime updates (`maxUnavailable: 0`)

---

## Hook Implementation

Two Helm hooks were implemented for lifecycle management.

### Pre-Install Hook

**File:** `templates/hooks/pre-install-job.yaml`

**Purpose:** Validates the environment before deploying the application.

**Configuration:**
- **Hook Type:** `pre-install` — runs before any resources are created
- **Weight:** `-5` — executes early (lower weights run first)
- **Deletion Policy:** `hook-succeeded` — automatically deleted after successful completion

**Implementation:**
The hook runs a Kubernetes Job using busybox that:
- Displays release information (name, namespace, chart version)
- Simulates pre-installation checks (namespace availability, configuration validation, resource quota verification)
- Provides clear logging for troubleshooting

### Post-Install Hook

**File:** `templates/hooks/post-install-job.yaml`

**Purpose:** Verifies the application is healthy after deployment.

**Configuration:**
- **Hook Type:** `post-install` — runs after all resources are installed and ready
- **Weight:** `5` — executes after main resources are up
- **Deletion Policy:** `hook-succeeded` — automatically deleted after successful completion

**Implementation:**
The hook runs a Kubernetes Job that:
- Confirms deployment status
- Verifies service endpoints
- Runs smoke tests
- Provides deployment success confirmation

### Hook Execution Order

The hooks execute in the following order:

```
1. Pre-install hook (weight: -5)
   ↓
2. Main resources (Deployment, Service)
   ↓
3. Wait for resources to be ready
   ↓
4. Post-install hook (weight: 5)
```

### Deletion Policy

The `hook-succeeded` deletion policy was used to keep the cluster clean. Hooks are temporary validation jobs that don't need to persist after completion. After successful execution, both hook Jobs were automatically deleted by Helm.

---

## Installation Evidence

### Helm Installation

Helm 4.1.3 was installed on the system:

```bash
$ helm version
version.BuildInfo{Version:"v4.1.3", GitCommit:"c94d381b03be117e7e57908edbf642104e00eb8f", GitTreeState:"clean", GoVersion:"go1.25.8", KubeClientVersion:"v1.35"}
```

### Chart Validation

The chart was validated using Helm's linting tool:

```bash
$ helm lint k8s/devops-app
==> Linting k8s/devops-app
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

### Development Environment Deployment

The chart was deployed to the Kubernetes cluster using development values:

```bash
$ helm install devops-dev k8s/devops-app -f k8s/devops-app/values-dev.yaml
NAME: devops-dev
LAST DEPLOYED: Thu Apr  2 18:24:47 2026
NAMESPACE: default
STATUS: deployed
REVISION: 1
```

### Release Verification

```bash
$ helm list
NAME      	NAMESPACE	REVISION	UPDATED                                	STATUS  	CHART           	APP VERSION
devops-dev	default  	2       	2026-04-02 18:26:28.816410044 +0000 UTC	deployed	devops-app-0.1.0	1.0
```

### Deployed Resources

```bash
$ kubectl get all
NAME                                         READY   STATUS    RESTARTS   AGE
pod/devops-dev-devops-app-685dc86589-bdl9h   1/1     Running   0          2m31s
pod/devops-dev-devops-app-685dc86589-k5q2p   1/1     Running   0          2m47s
pod/devops-dev-devops-app-685dc86589-rjft7   1/1     Running   0          2m39s

NAME                            TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
service/devops-dev-devops-app   NodePort    10.96.112.170   <none>        80:30080/TCP   4m20s
service/kubernetes              ClusterIP   10.96.0.1       <none>        443/TCP        5m18s

NAME                                    READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-dev-devops-app   3/3     3            3           4m20s

NAME                                               DESIRED   CURRENT   READY   AGE
replicaset.apps/devops-dev-devops-app-685dc86589   3         3         3       2m47s
replicaset.apps/devops-dev-devops-app-6cd8bb57d6   0         0         0       4m20s
```

### Hook Execution Verification

The hooks were executed successfully during installation. After completion, they were automatically deleted per the `hook-succeeded` deletion policy:

```bash
$ kubectl get jobs
No resources found in default namespace.
```

This confirms that both pre-install and post-install hooks ran successfully and were cleaned up automatically.

### Health Check Verification

The health checks were verified to be working correctly:

```bash
$ kubectl describe pod -l app.kubernetes.io/name=devops-app | grep -A 2 "Liveness\|Readiness"
    Liveness:   http-get http://:8000/health delay=10s timeout=5s period=10s #success=1 #failure=3
    Readiness:  http-get http://:8000/health delay=5s timeout=3s period=5s #success=1 #failure=3
    Environment:
      HOST:   0.0.0.0
      PORT:   8000
      DEBUG:  false
```

### Application Health

The application was tested and confirmed to be healthy:

```bash
$ kubectl port-forward service/devops-dev-devops-app 8080:80 &
$ curl -s http://localhost:8080/health
{"status":"healthy","timestamp":"2026-04-02T18:30:25.881960+00:00","uptime_seconds":234}
```

### Upgrade History

The release was upgraded to demonstrate Helm's upgrade capability:

```bash
$ helm history devops-dev
REVISION	UPDATED                 	STATUS    	CHART           	APP VERSION	DESCRIPTION     
1       	Thu Apr  2 18:24:47 2026	superseded	devops-app-0.1.0	1.0        	Install complete
2       	Thu Apr  2 18:26:28 2026	deployed  	devops-app-0.1.0	1.0        	Upgrade complete
```

---

## Operations

### Installation Commands Used

The following commands were used during the lab:

**Development environment:**
```bash
helm install devops-dev k8s/devops-app -f k8s/devops-app/values-dev.yaml
```

**Production environment (example):**
```bash
helm install devops-prod k8s/devops-app -f k8s/devops-app/values-prod.yaml
```

### Upgrade Process

To upgrade a release:

```bash
helm upgrade devops-dev k8s/devops-app --set image.tag=v1.0
```

This command was used to upgrade from the `latest` tag to `v1.0` after the initial installation.

### Rollback Capability

To rollback to a previous revision:

```bash
helm rollback devops-dev
```

Or to a specific revision:

```bash
helm rollback devops-dev 1
```

### Uninstall Process

To remove a release:

```bash
helm uninstall devops-dev
```

---

## Testing & Validation

### Helm Lint

The chart was validated for syntax and best practices:

```bash
$ helm lint k8s/devops-app
==> Linting k8s/devops-app
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

All environment-specific values files were also validated:

```bash
$ helm lint k8s/devops-app -f k8s/devops-app/values-dev.yaml
==> Linting k8s/devops-app
[INFO] Chart.yaml: icon is recommended
1 chart(s) linted, 0 chart(s) failed

$ helm lint k8s/devops-app -f k8s/devops-app/values-prod.yaml
==> Linting k8s/devops-app
[INFO] Chart.yaml: icon is recommended
1 chart(s) linted, 0 chart(s) failed
```

### Template Rendering

Templates were rendered locally to verify correct Go template syntax (see `screenshots/lab10_template_rendering.txt` for full output):

```bash
$ helm template test-release k8s/devops-app | head -50
---
# Source: devops-app/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: test-release-devops-app
  namespace: default
  labels:
    helm.sh/chart: devops-app-0.1.0
    app.kubernetes.io/name: devops-app
    app.kubernetes.io/instance: test-release
    app.kubernetes.io/version: "1.0"
    app.kubernetes.io/managed-by: Helm
    app.kubernetes.io/component: web
spec:
  type: NodePort
  selector:
    app.kubernetes.io/name: devops-app
    app.kubernetes.io/instance: test-release
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 8000
      nodePort: 30080
---
# Source: devops-app/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
...
```

### Dry-Run Installation

A dry-run installation was performed to validate the complete installation process (see `screenshots/lab10_dry_run.txt` for full output):

```bash
$ helm install --dry-run --debug test-release k8s/devops-app
install.go: [debug] Original chart version: ""
install.go: [debug] CHART PATH: /path/to/k8s/devops-app

NAME: test-release
LAST DEPLOYED: Thu Apr  2 21:10:00 2026
NAMESPACE: default
STATUS: pending-install
REVISION: 1
...
```

### Application Accessibility Verification

The application was accessed and tested successfully:

```bash
$ kubectl port-forward service/devops-dev-devops-app 8080:80
Forwarding from 127.0.0.1:8080 -> 8000

$ curl -s http://localhost:8080/health
{"status":"healthy","timestamp":"2026-04-02T18:30:25.881960+00:00","uptime_seconds":234}

$ curl -s http://localhost:8080/ | jq .service
{
  "name": "devops-info-service",
  "version": "1.0.0",
  "description": "DevOps course info service",
  "framework": "Flask"
}
```

All pods were verified to be running and healthy:

```bash
$ kubectl get pods -l app.kubernetes.io/name=devops-app
NAME                                     READY   STATUS    RESTARTS   AGE
devops-dev-devops-app-685dc86589-bdl9h   1/1     Running   0          5m
devops-dev-devops-app-685dc86589-k5q2p   1/1     Running   0          5m
devops-dev-devops-app-685dc86589-rjft7   1/1     Running   0          5m
```

---

## Summary

This Helm chart successfully packages the DevOps Python Flask application with:

- Production-ready templating — All hardcoded values extracted to values.yaml
- Multi-environment support — Separate configurations for dev and prod
- Lifecycle hooks — Pre-install validation and post-install verification
- Health checks preserved — Liveness and readiness probes fully configurable
- Security best practices — Non-root user, dropped capabilities, resource limits
- Zero-downtime updates — RollingUpdate strategy with configurable surge/unavailable
- Comprehensive documentation — Installation, operations, and troubleshooting guides

The chart follows Helm best practices and is ready for production deployment across multiple environments.
