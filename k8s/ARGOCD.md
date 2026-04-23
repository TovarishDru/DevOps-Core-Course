# ArgoCD GitOps Deployment

## ArgoCD Setup

### Installation

ArgoCD was installed from the official GitHub release manifests (v3.3.8):

```bash
# Create a dedicated namespace
kubectl create namespace argocd

# Install ArgoCD from GitHub release manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.3.8/manifests/install.yaml \
  --server-side --force-conflicts

# Wait for all pods to become ready
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=argocd-server \
  -n argocd --timeout=120s
```

### Verification

```
$ kubectl get pods -n argocd
NAME                                                READY   STATUS    RESTARTS      AGE
argocd-application-controller-0                     1/1     Running   1 (28m ago)   59m
argocd-applicationset-controller-68fb4455bb-jbc6g   1/1     Running   1 (28m ago)   59m
argocd-dex-server-76dcbcbc86-8h744                  1/1     Running   1 (28m ago)   59m
argocd-notifications-controller-8495566bcf-d2r99    1/1     Running   2 (28m ago)   59m
argocd-redis-85cfb75bdd-lrrvj                       1/1     Running   1 (28m ago)   59m
argocd-repo-server-9fd46496f-lmk99                  1/1     Running   2 (30m ago)   59m
argocd-server-9c669c566-m99gw                       1/1     Running   2 (30m ago)   59m
```

All 7 ArgoCD components are running: application-controller, applicationset-controller, dex-server, notifications-controller, redis, repo-server, and server.

---

## Application Configuration

### Directory Structure

```
k8s/argocd/
├── application.yaml        # Base app — manual sync, default namespace
├── application-dev.yaml    # Dev environment — auto-sync with selfHeal + prune
└── application-prod.yaml   # Prod environment — manual sync only
```

### Base Application (`application.yaml`)

Deploys the Helm chart to the `default` namespace with **manual sync**:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: python-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/TovarishDru/DevOps-Core-Course.git
    targetRevision: master
    path: k8s/devops-app
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
```

**Key fields:**

| Field | Value | Purpose |
|-------|-------|---------|
| `source.repoURL` | GitHub repo URL | Git repository ArgoCD pulls from |
| `source.path` | `k8s/devops-app` | Path to the Helm chart in the repo |
| `source.targetRevision` | `master` | Git branch to track |
| `source.helm.valueFiles` | `values.yaml` | Which Helm values file to use |
| `destination.namespace` | `default` | Kubernetes namespace to deploy into |
| `syncPolicy` | No `automated` block | Manual sync — must trigger explicitly |

### Deployment Evidence

After applying all three Application manifests and syncing:

```
$ kubectl get applications -n argocd -o wide
NAME              CLUSTER                         NAMESPACE  PROJECT  STATUS  HEALTH       SYNCPOLICY  REPO                                                   PATH            TARGET
python-app        https://kubernetes.default.svc  default    default  Synced  Healthy      Manual      https://github.com/TovarishDru/DevOps-Core-Course.git  k8s/devops-app  master
python-app-dev    https://kubernetes.default.svc  dev        default  Synced  Healthy      Auto-Prune  https://github.com/TovarishDru/DevOps-Core-Course.git  k8s/devops-app  master
python-app-prod   https://kubernetes.default.svc  prod       default  Synced  Progressing  Manual      https://github.com/TovarishDru/DevOps-Core-Course.git  k8s/devops-app  master
```

---

## Multi-Environment Deployment

### Dev Environment (`application-dev.yaml`)

Uses `values-dev.yaml` with **automatic sync, self-healing, and pruning**:

```yaml
syncPolicy:
  automated:
    prune: true      # Delete resources removed from Git
    selfHeal: true   # Revert manual cluster changes
  syncOptions:
    - CreateNamespace=true
```

**Dev configuration highlights** (from `values-dev.yaml`):

- `replicaCount: 1` — minimal resources for development
- `image.tag: v1.0` — pinned stable version
- `DEBUG: "true"` — verbose logging enabled
- Lower resource limits (64Mi/50m requests)
- `nodePort: 30081` — avoids conflict with default namespace (30082)

### Prod Environment (`application-prod.yaml`)

Uses `values-prod.yaml` with **manual sync only**:

```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
  # No automated block = manual sync required
```

**Prod configuration highlights** (from `values-prod.yaml`):

- `replicaCount: 5` — high availability
- `image.tag: v1.0` — pinned version, no surprises
- `DEBUG: "false"` — production logging
- Higher resource limits (256Mi/200m requests)
- `service.type: LoadBalancer` — external access

### Why Manual Sync for Production?

| Reason | Explanation |
|--------|-------------|
| **Change review** | Changes should be reviewed before reaching production |
| **Controlled timing** | Deployments happen during maintenance windows |
| **Compliance** | Audit requirements demand explicit approval |
| **Rollback planning** | Team prepares rollback strategy before deploying |
| **Blast radius** | Mistakes in prod affect real users |

### Pod Status Evidence

```
$ kubectl get pods -n default -l app.kubernetes.io/name=devops-app
NAME                                     READY   STATUS    RESTARTS      AGE
python-app-devops-app-695c75d7df-h7mm7   1/1     Running   1 (28m ago)   44m
python-app-devops-app-695c75d7df-p68gx   1/1     Running   1 (28m ago)   44m
python-app-devops-app-695c75d7df-xm6p7   1/1     Running   1 (28m ago)   44m

$ kubectl get pods -n dev -l app.kubernetes.io/name=devops-app
NAME                                         READY   STATUS    RESTARTS   AGE
python-app-dev-devops-app-5f69d96b4b-pcnrk   1/1     Running   0          12m

$ kubectl get pods -n prod -l app.kubernetes.io/name=devops-app
NAME                                          READY   STATUS    RESTARTS   AGE
python-app-prod-devops-app-58c8b89777-6xtb8   1/1     Running   0          25m
python-app-prod-devops-app-58c8b89777-f7w5w   1/1     Running   0          25m
python-app-prod-devops-app-58c8b89777-nggtd   1/1     Running   0          25m
python-app-prod-devops-app-58c8b89777-spjhr   1/1     Running   0          25m
python-app-prod-devops-app-58c8b89777-wz4xz   1/1     Running   0          25m
```

### Configuration Comparison

| Aspect | Default | Dev | Prod |
|--------|---------|-----|------|
| Replicas | 3 | 1 | 5 |
| Image tag | `v1.0` | `v1.0` | `v1.0` |
| Debug mode | Disabled | Enabled | Disabled |
| CPU request | 100m | 50m | 200m |
| Memory request | 128Mi | 64Mi | 256Mi |
| Service type | NodePort (30082) | NodePort (30081) | LoadBalancer |
| Sync policy | Manual | Automated + selfHeal | Manual |
| Prune enabled | No (manual) | Yes | No (manual) |

---

## Self-Healing & Sync Behavior

### Test 1: Manual Scale (ArgoCD Self-Healing)

ArgoCD's `selfHeal` reverts any manual changes to match the Git-defined state.

**Before — 1 replica running in dev (as defined in Git):**

```
$ kubectl get deployment python-app-dev-devops-app -n dev
NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
python-app-dev-devops-app   1/1     1            1           46m
```

**Manually scaling to 5 replicas:**

```
$ kubectl scale deployment python-app-dev-devops-app -n dev --replicas=5
deployment.apps/python-app-dev-devops-app scaled

$ kubectl get pods -n dev -l app.kubernetes.io/name=devops-app
NAME                                         READY   STATUS              RESTARTS   AGE
python-app-dev-devops-app-5f69d96b4b-7zllx   0/1     ContainerCreating   0          0s
python-app-dev-devops-app-5f69d96b4b-lr8th   0/1     ContainerCreating   0          0s
python-app-dev-devops-app-5f69d96b4b-pcnrk   1/1     Running             0          13m
python-app-dev-devops-app-5f69d96b4b-r4gwt   0/1     ContainerCreating   0          0s
python-app-dev-devops-app-5f69d96b4b-rw4ph   0/1     ContainerCreating   0          0s
```

**After ~10 seconds — ArgoCD detected the drift and reverted to 1 replica:**

```
$ kubectl get pods -n dev -l app.kubernetes.io/name=devops-app
NAME                                         READY   STATUS        RESTARTS   AGE
python-app-dev-devops-app-5f69d96b4b-7zllx   1/1     Terminating   0          10s
python-app-dev-devops-app-5f69d96b4b-lr8th   1/1     Terminating   0          10s
python-app-dev-devops-app-5f69d96b4b-pcnrk   1/1     Running       0          13m
python-app-dev-devops-app-5f69d96b4b-r4gwt   1/1     Terminating   0          10s
python-app-dev-devops-app-5f69d96b4b-rw4ph   1/1     Terminating   0          10s

$ kubectl get deployment python-app-dev-devops-app -n dev -o jsonpath="{.spec.replicas}"
1
```

**Result:** ArgoCD detected the replica count drift (5 ≠ 1 in Git) and automatically scaled back to 1 replica within ~10 seconds. The 4 extra pods were terminated, and only the original pod remained running.

### Test 2: Pod Deletion (Kubernetes Self-Healing)

This tests **Kubernetes** self-healing (ReplicaSet controller), not ArgoCD.

**Before — 1 pod running:**

```
$ kubectl get pods -n dev -l app.kubernetes.io/name=devops-app
NAME                                         READY   STATUS    RESTARTS   AGE
python-app-dev-devops-app-5f69d96b4b-pcnrk   1/1     Running   0          14m
```

**Deleting the pod:**

```
$ kubectl delete pod python-app-dev-devops-app-5f69d96b4b-pcnrk -n dev
pod "python-app-dev-devops-app-5f69d96b4b-pcnrk" deleted
```

**After ~8 seconds — Kubernetes created a replacement pod:**

```
$ kubectl get pods -n dev -l app.kubernetes.io/name=devops-app
NAME                                         READY   STATUS    RESTARTS   AGE
python-app-dev-devops-app-5f69d96b4b-x2vgq   0/1     Running   0          8s
```

**Result:** The Deployment's ReplicaSet controller detected the pod count dropped below the desired count (1) and immediately created a replacement pod (`x2vgq`). ArgoCD was **not involved** — this is native Kubernetes behavior. The pod name changed (new pod), but the deployment spec remained unchanged.

### Test 3: Configuration Drift (ArgoCD Self-Healing)

This test demonstrates how ArgoCD handles metadata-level changes. We tested by adding a manual label to the deployment:

```
$ kubectl label deployment python-app-dev-devops-app -n dev manual-change=true
deployment.apps/python-app-dev-devops-app labeled
```

**Important finding:** ArgoCD uses a **3-way merge** strategy by default (comparing live state, last-applied state, and desired state). Metadata-only changes like labels are treated as non-conflicting additions and may not trigger an immediate self-heal revert. However, **spec-level changes** like replica count modifications (Test 1) are immediately detected and reverted because they directly conflict with the Git-defined desired state.

This behavior is by design — ArgoCD's default `Apply` strategy preserves non-conflicting additions to allow operators to add annotations/labels for monitoring or debugging without constant reverts. To enforce strict Git-only state, the `Replace` sync strategy or `ServerSideApply=true` sync option can be used.

### Key Differences: Kubernetes vs ArgoCD Self-Healing

| Aspect | Kubernetes Self-Healing | ArgoCD Self-Healing |
|--------|------------------------|---------------------|
| **What it heals** | Pod count (via ReplicaSet) | Full resource spec (replicas, images, env, etc.) |
| **Trigger** | Pod dies or is deleted | Any spec drift from Git state |
| **Speed** | Immediate (seconds) | Within seconds when drift detected |
| **Scope** | Only pod lifecycle | All managed resources |
| **Example** | Pod crash → new pod created | Manual scale → reverted to Git value |
| **Source of truth** | Deployment spec in cluster | Git repository |
| **Demonstrated in** | Test 2 (pod deletion) | Test 1 (replica scaling) |

### Sync Triggers

ArgoCD syncs when:

1. **Git polling** — ArgoCD checks the repo every **3 minutes** by default
2. **Webhook** — GitHub/GitLab webhook triggers immediate sync
3. **Manual** — User clicks Sync in UI or runs `argocd app sync`
4. **Self-heal** — Cluster drift detected (if `selfHeal: true`)
