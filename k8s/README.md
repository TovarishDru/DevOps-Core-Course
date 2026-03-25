# Lab 9 — Kubernetes Fundamentals

## Task 1 — Local Kubernetes Setup

### Tools Used

- **kubectl** v1.33.0 — Kubernetes CLI
- **kind** v0.27.0 — Kubernetes in Docker (local cluster)

**Why kind?**  
kind (Kubernetes IN Docker) was chosen because it runs entirely inside Docker containers with no VM overhead. It's lightweight, fast to start, and works perfectly on any Linux server with Docker installed. It's also the recommended tool for CI/CD environments and local development without a hypervisor

### Installation

```bash
# Install kubectl
curl -LO https://dl.k8s.io/release/v1.33.0/bin/linux/amd64/kubectl
chmod +x kubectl && sudo mv kubectl /usr/local/bin/kubectl

# Install kind
curl -Lo kind https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-amd64
chmod +x kind && sudo mv kind /usr/local/bin/kind

# Create cluster
kind create cluster --name devops-lab9

# Verify
kubectl cluster-info --context kind-devops-lab9
kubectl get nodes
```

### Cluster Setup Output

```
$ kind create cluster --name devops-lab9
Creating cluster "devops-lab9" ...
 ✓ Ensuring node image (kindest/node:v1.32.2) 🖼
 ✓ Preparing nodes 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
Set kubectl context to "kind-devops-lab9"

$ kubectl cluster-info --context kind-devops-lab9
Kubernetes control plane is running at https://127.0.0.1:45077
CoreDNS is running at https://127.0.0.1:45077/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

$ kubectl get nodes -o wide
NAME                        STATUS   ROLES           AGE    VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE                         KERNEL-VERSION      CONTAINER-RUNTIME
devops-lab9-control-plane   Ready    control-plane   4m4s   v1.32.2   172.21.0.2    <none>        Debian GNU/Linux 12 (bookworm)   6.8.0-100-generic   containerd://2.0.2
```

---

## Architecture Overview

```
                        ┌─────────────────────────────────────┐
                        │         Kubernetes Cluster           │
                        │         (kind-devops-lab9)           │
                        │                                      │
  kubectl port-forward  │  ┌──────────────────────────────┐   │
  localhost:8080 ──────►│  │   NodePort Service :30080    │   │
                        │  └──────────┬───────────────────┘   │
                        │             │ selector: app=devops-app│
                        │  ┌──────────▼───────────────────┐   │
                        │  │        Deployment             │   │
                        │  │  ┌────────┐ ┌────────┐       │   │
                        │  │  │ Pod 1  │ │ Pod 2  │ ...   │   │
                        │  │  │ :8000  │ │ :8000  │       │   │
                        │  │  └────────┘ └────────┘       │   │
                        │  │  replicas: 3 (→ 5 for scale) │   │
                        │  └──────────────────────────────┘   │
                        └─────────────────────────────────────┘
```

**Resource Allocation:**
- Each Pod: 100m CPU request / 200m CPU limit, 128Mi memory request / 256Mi memory limit
- 3 replicas × 100m = 300m CPU total requests
- 3 replicas × 128Mi = 384Mi memory total requests

---

## Manifest Files

### `deployment.yml`

Deploys the Python Flask application with production-grade configuration:

| Field | Value | Rationale |
|-------|-------|-----------|
| `replicas` | 3 | High availability — survives single pod failure |
| `strategy` | RollingUpdate | Zero-downtime deployments |
| `maxSurge` | 1 | One extra pod during update to maintain capacity |
| `maxUnavailable` | 0 | Never reduce below desired replica count |
| CPU request | 100m | Minimum guaranteed CPU for scheduling |
| CPU limit | 200m | Prevents one pod from starving others |
| Memory request | 128Mi | Baseline for Flask app |
| Memory limit | 256Mi | 2× request — headroom for traffic spikes |
| `livenessProbe` | `/health` HTTP GET | Restarts unhealthy containers automatically |
| `readinessProbe` | `/health` HTTP GET | Removes pod from load balancer if not ready |

### `service.yml`

Exposes the Deployment as a `NodePort` service:

| Field | Value | Rationale |
|-------|-------|-----------|
| `type` | NodePort | Allows external access without cloud provider |
| `port` | 80 | Standard HTTP port for cluster-internal traffic |
| `targetPort` | 8000 | Matches container's `PORT` env var |
| `nodePort` | 30080 | Fixed external port for predictable access |

---

## Deployment Evidence

### Deploy All Resources

```bash
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/service.yml
kubectl rollout status deployment/devops-app
```

### `kubectl get all` Output

```
$ kubectl get all
NAME                              READY   STATUS    RESTARTS   AGE
pod/devops-app-84ccfb98cc-nzz86   1/1     Running   0          24s
pod/devops-app-84ccfb98cc-q5qf4   1/1     Running   0          16s
pod/devops-app-84ccfb98cc-t8qmt   1/1     Running   0          37s

NAME                         TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
service/devops-app-service   NodePort    10.96.94.169   <none>        80:30080/TCP   3m23s
service/kubernetes           ClusterIP   10.96.0.1      <none>        443/TCP        4m2s

NAME                         READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-app   3/3     3            3           3m23s

NAME                                    DESIRED   CURRENT   READY   AGE
replicaset.apps/devops-app-558746d98    0         0         0       3m23s
replicaset.apps/devops-app-84ccfb98cc   3         3         3       37s
```

### `kubectl get pods,svc -o wide`

```
$ kubectl get pods,svc -o wide
NAME                              READY   STATUS    RESTARTS   AGE   IP            NODE                        NOMINATED NODE   READINESS GATES
pod/devops-app-84ccfb98cc-nzz86   1/1     Running   0          24s   10.244.0.9    devops-lab9-control-plane   <none>           <none>
pod/devops-app-84ccfb98cc-q5qf4   1/1     Running   0          16s   10.244.0.10   devops-lab9-control-plane   <none>           <none>
pod/devops-app-84ccfb98cc-t8qmt   1/1     Running   0          37s   10.244.0.8    devops-lab9-control-plane   <none>           <none>

NAME                         TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE     SELECTOR
service/devops-app-service   NodePort    10.96.94.169   <none>        80:30080/TCP   3m23s   app=devops-app
service/kubernetes           ClusterIP   10.96.0.1      <none>        443/TCP        4m2s    <none>
```

### `kubectl describe deployment devops-app`

```
$ kubectl describe deployment devops-app
Name:                   devops-app
Namespace:              default
Labels:                 app=devops-app
                        component=web
                        version=1.0.0
Annotations:            deployment.kubernetes.io/revision: 2
Selector:               app=devops-app
Replicas:               3 desired | 3 updated | 3 total | 3 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  0 max unavailable, 1 max surge
Pod Template:
  Labels:  app=devops-app
           component=web
           version=1.0.0
  Containers:
   devops-app:
    Image:      tovarishdru/devops-python-app:v1.0
    Port:       8000/TCP
    Limits:     cpu: 200m, memory: 256Mi
    Requests:   cpu: 100m, memory: 128Mi
    Liveness:   http-get http://:8000/health delay=10s timeout=5s period=10s #success=1 #failure=3
    Readiness:  http-get http://:8000/health delay=5s timeout=3s period=5s #success=1 #failure=3
    Environment:
      HOST:   0.0.0.0
      PORT:   8000
      DEBUG:  false
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    True    NewReplicaSetAvailable
Events:
  Normal  ScalingReplicaSet  3m23s  deployment-controller  Scaled up replica set devops-app-558746d98 from 0 to 3
  Normal  ScalingReplicaSet  37s    deployment-controller  Scaled up replica set devops-app-84ccfb98cc from 0 to 1
  Normal  ScalingReplicaSet  24s    deployment-controller  Scaled down replica set devops-app-558746d98 from 3 to 2
  Normal  ScalingReplicaSet  24s    deployment-controller  Scaled up replica set devops-app-84ccfb98cc from 1 to 2
  Normal  ScalingReplicaSet  16s    deployment-controller  Scaled down replica set devops-app-558746d98 from 2 to 1
  Normal  ScalingReplicaSet  16s    deployment-controller  Scaled up replica set devops-app-84ccfb98cc from 2 to 3
  Normal  ScalingReplicaSet  8s     deployment-controller  Scaled down replica set devops-app-558746d98 from 1 to 0
```

### App Access Verification

```bash
# Port-forward service to localhost
kubectl port-forward service/devops-app-service 8080:80 &

# Test endpoints
curl -s http://localhost:8080/
curl -s http://localhost:8080/health
```

```
$ curl -s http://localhost:8080/
{
    "endpoints": [
        {"description": "Service information", "method": "GET", "path": "/"},
        {"description": "Health check", "method": "GET", "path": "/health"}
    ],
    "request": {
        "client_ip": "127.0.0.1",
        "method": "GET",
        "path": "/",
        "user_agent": "curl/8.5.0"
    },
    "runtime": {
        "current_time": "2026-03-25T19:11:27.379992+00:00",
        "timezone": "UTC",
        "uptime_human": "0 hours, 3 minutes",
        "uptime_seconds": 238
    },
    "service": {
        "description": "DevOps course info service",
        "framework": "Flask",
        "name": "devops-info-service",
        "version": "1.0.0"
    },
    "system": {
        "architecture": "x86_64",
        "cpu_count": 8,
        "hostname": "devops-app-84ccfb98cc-t8qmt",
        "platform": "Linux",
        "platform_version": "#100-Ubuntu SMP PREEMPT_DYNAMIC Tue Jan 13 16:40:06 UTC 2026",
        "python_version": "3.13.11"
    }
}

$ curl -s http://localhost:8080/health
{
    "status": "healthy",
    "timestamp": "2026-03-25T19:11:27.409607+00:00",
    "uptime_seconds": 238
}
```

---

## Operations Performed

### Deploy

```bash
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/service.yml
kubectl rollout status deployment/devops-app
```

### Scaling to 5 Replicas

```bash
kubectl scale deployment/devops-app --replicas=5
kubectl rollout status deployment/devops-app
```

```
$ kubectl scale deployment/devops-app --replicas=5
deployment.apps/devops-app scaled

$ kubectl rollout status deployment/devops-app
Waiting for deployment "devops-app" rollout to finish: 3 of 5 updated replicas are available...
Waiting for deployment "devops-app" rollout to finish: 4 of 5 updated replicas are available...
deployment "devops-app" successfully rolled out

$ kubectl get pods -o wide
NAME                          READY   STATUS    RESTARTS   AGE    IP            NODE
devops-app-84ccfb98cc-4jcl6   1/1     Running   0          10s    10.244.0.12   devops-lab9-control-plane
devops-app-84ccfb98cc-gx766   1/1     Running   0          10s    10.244.0.11   devops-lab9-control-plane
devops-app-84ccfb98cc-nzz86   1/1     Running   0          95s    10.244.0.9    devops-lab9-control-plane
devops-app-84ccfb98cc-q5qf4   1/1     Running   0          87s    10.244.0.10   devops-lab9-control-plane
devops-app-84ccfb98cc-t8qmt   1/1     Running   0          108s   10.244.0.8    devops-lab9-control-plane

$ kubectl get deployments
NAME         READY   UP-TO-DATE   AVAILABLE   AGE
devops-app   5/5     5            5           4m34s
```

### Rolling Update

```bash
# Simulate update by changing image (in production: update tag in deployment.yml)
kubectl set image deployment/devops-app devops-app=nginx:alpine
kubectl rollout status deployment/devops-app
```

```
$ kubectl set image deployment/devops-app devops-app=nginx:alpine
deployment.apps/devops-app image updated

$ kubectl rollout status deployment/devops-app
Waiting for deployment "devops-app" rollout to finish: 1 out of 5 new replicas have been updated...
```

### Rollback

```bash
kubectl rollout undo deployment/devops-app
kubectl rollout status deployment/devops-app
kubectl rollout history deployment/devops-app
```

```
$ kubectl rollout undo deployment/devops-app
deployment.apps/devops-app rolled back

$ kubectl rollout status deployment/devops-app
deployment "devops-app" successfully rolled out

$ kubectl rollout history deployment/devops-app
deployment.apps/devops-app
REVISION  CHANGE-CAUSE
1         <none>
3         <none>
4         <none>
```

Revision 4 is the rollback to the original `tovarishdru/devops-python-app:v1.0` image.

### Service Access

```bash
# Port-forward (works with kind — no minikube service command needed)
kubectl port-forward service/devops-app-service 8080:80
# Then: curl http://localhost:8080/health
```

---

## Production Considerations

### Health Checks

| Probe | Path | Rationale |
|-------|------|-----------|
| **Liveness** | `/health` | Detects deadlocks/hangs — restarts the container automatically |
| **Readiness** | `/health` | Prevents traffic to pods still initializing or temporarily overloaded |

Both probes use the existing `/health` endpoint which returns `{"status": "healthy"}` — no extra code needed.

### Resource Limits Rationale

- **Requests** define the minimum guaranteed resources for scheduling. Set conservatively to allow dense packing.
- **Limits** prevent a single pod from consuming all node resources. Set at 2× request to allow burst traffic.
- For production, these values should be tuned based on load testing and actual metrics.

### Production Improvements

1. **Namespace isolation** — deploy to a dedicated namespace (e.g., `production`) instead of `default`
2. **HorizontalPodAutoscaler (HPA)** — auto-scale based on CPU/memory metrics
3. **PodDisruptionBudget (PDB)** — guarantee minimum availability during node maintenance
4. **NetworkPolicy** — restrict pod-to-pod communication
5. **ConfigMaps & Secrets** — externalize configuration and credentials
6. **Image pinning** — use specific digest (`image@sha256:...`) instead of `latest`
7. **Pod anti-affinity** — spread replicas across nodes for true HA

### Monitoring & Observability

- Enable `metrics-server` for `kubectl top pods`
- Integrate with Prometheus + Grafana (Lab 8 stack) via ServiceMonitor
- Use structured JSON logs (already implemented in the app) with Loki/Promtail
- Set up alerts on pod restarts, high error rates, and resource saturation

---

## Challenges & Solutions

### Challenge 1: Non-root UID mismatch

The Dockerfile creates user `appuser` but doesn't set a numeric UID. The pod `securityContext` uses `runAsUser: 999` — this must match the UID assigned by `useradd -r`.

**Solution:** Verified with `docker run --rm tovarishdru/devops-python-app:v1.0 id` that the system user gets UID 999 on Debian-based images. Alternatively, set `runAsNonRoot: true` without a specific UID to let Kubernetes enforce non-root without caring about the exact number.

### Challenge 2: Rolling update with `maxUnavailable: 0`

With `maxUnavailable: 0` and `maxSurge: 1`, the rolling update to a broken image (`nginx:alpine` with wrong health probe path) stalled — only 1 pod was updated and it failed readiness, so Kubernetes correctly stopped the rollout.

**Solution:** `kubectl rollout undo` immediately restored the previous working revision. This demonstrated that `maxUnavailable: 0` is the correct production setting — it prevented any downtime during the failed update.

### Key Learnings

- Kubernetes **reconciliation loop** continuously compares desired state (manifest) with actual state and corrects drift
- **Labels and selectors** are the glue between Deployments, ReplicaSets, Services, and Ingress — they must match exactly
- **Probes** are critical: without them, Kubernetes sends traffic to pods that aren't ready yet
- `kubectl describe` and `kubectl logs` are the primary debugging tools — always check Events section in describe output
- `maxUnavailable: 0` + `maxSurge: 1` is the safest rolling update strategy — zero downtime guaranteed
