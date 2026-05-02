# StatefulSet & Persistent Storage

## 1. StatefulSet Overview

### Why StatefulSet over Deployment

Deployments treat all pods as interchangeable — they get random names, share storage, and can be created or destroyed in any order. This works well for stateless applications like web servers and APIs

StatefulSets provide guarantees that stateful applications require:

- **Stable, unique network identifiers** — pods are named with ordinal indices (`app-0`, `app-1`, `app-2`) instead of random suffixes, and each pod gets a stable DNS record via a headless service
- **Stable, persistent storage** — each pod receives its own PersistentVolumeClaim through `volumeClaimTemplates`. The PVC persists even when the pod is deleted
- **Ordered, graceful deployment and scaling** — pods are created sequentially (0, then 1, then 2) and terminated in reverse order

### Comparison

| Feature | Deployment | StatefulSet |
|---------|------------|-------------|
| Pod Names | Random suffix (`app-abc123`) | Ordered index (`app-0`, `app-1`) |
| Storage | Shared PVC or none | Per-pod PVC via `volumeClaimTemplates` |
| Scaling | Any order (parallel) | Ordered (0 -> 1 -> 2 up, reverse down) |
| Network ID | Random, changes on restart | Stable DNS name per pod |
| Use Case | Stateless apps (web servers, APIs) | Stateful apps (databases, queues) |

### Typical StatefulSet Workloads

- Databases (PostgreSQL, MySQL, MongoDB) — need stable identity for replication
- Message queues (Kafka, RabbitMQ) — brokers identified by stable IDs
- Distributed systems (Elasticsearch, Cassandra) — nodes join cluster by name

### Headless Services

A headless service (`clusterIP: None`) does not allocate a cluster IP. Instead, it creates individual DNS A records for each pod behind it:

```
<pod-name>.<headless-service>.<namespace>.svc.cluster.local
```

This enables direct pod-to-pod communication by name, which is essential for stateful applications that need peer discovery

---

## 2. Resource Verification

```
$ kubectl get po,sts,svc,pvc

NAME               READY   STATUS    RESTARTS   AGE
pod/devops-app-0   1/1     Running   0          47s
pod/devops-app-1   1/1     Running   0          32s
pod/devops-app-2   1/1     Running   0          20s

NAME                          READY   AGE
statefulset.apps/devops-app   3/3     47s

NAME                          TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)        AGE
service/devops-app            NodePort    10.43.60.14   <none>        80:30082/TCP   47s
service/devops-app-headless   ClusterIP   None          <none>        80/TCP         47s
service/kubernetes            ClusterIP   10.43.0.1     <none>        443/TCP        9m2s

NAME                                      STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
persistentvolumeclaim/data-devops-app-0   Bound    pvc-efb43100-6ec4-46d3-ae60-1172b6dfef5a   100Mi      RWO            local-path     47s
persistentvolumeclaim/data-devops-app-1   Bound    pvc-b17755d5-2adb-4edb-845c-0915b0b96c8e   100Mi      RWO            local-path     32s
persistentvolumeclaim/data-devops-app-2   Bound    pvc-3dfb2363-dae0-4651-bc36-4fa0f02ab4de   100Mi      RWO            local-path     20s
```

Three pods with ordinal names (`devops-app-0`, `-1`, `-2`), a StatefulSet with 3/3 ready replicas, a headless service with `ClusterIP: None`, and three individually bound PVCs — one per pod

---

## 3. Network Identity

DNS resolution from inside `devops-app-0`, resolving all three pods via the headless service:

```
$ kubectl exec devops-app-0 -- python3 -c "
import socket
for i in range(3):
    name = f'devops-app-{i}.devops-app-headless'
    ip = socket.gethostbyname(name)
    print(f'{name} -> {ip}')
"

devops-app-0.devops-app-headless -> 10.42.0.12
devops-app-1.devops-app-headless -> 10.42.0.14
devops-app-2.devops-app-headless -> 10.42.0.16
```

Each pod resolves to its own unique IP via the naming pattern `<pod>.<headless-service>`. The full FQDN is:

```
devops-app-0.devops-app-headless.default.svc.cluster.local
devops-app-1.devops-app-headless.default.svc.cluster.local
devops-app-2.devops-app-headless.default.svc.cluster.local
```

These DNS names remain stable even after pod restarts

---

## 4. Per-Pod Storage Evidence

The application exposes a `/visits` endpoint that reads and increments a counter stored in a file on the persistent volume (`/data/visits`). Each pod has its own PVC, so visit counts are independent

Pod 0 (hit 3 times):

```
{"pod":"devops-app-0","timestamp":"2026-05-01T15:48:34.172247+00:00","visits":1}
{"pod":"devops-app-0","timestamp":"2026-05-01T15:48:34.571317+00:00","visits":2}
{"pod":"devops-app-0","timestamp":"2026-05-01T15:48:34.971060+00:00","visits":3}
```

Pod 1 (hit 2 times — starts from 1, independent of pod-0):

```
{"pod":"devops-app-1","timestamp":"2026-05-01T15:48:35.404993+00:00","visits":1}
{"pod":"devops-app-1","timestamp":"2026-05-01T15:48:35.807376+00:00","visits":2}
```

Pod 2 (hit 1 time — starts from 1, independent of pod-0 and pod-1):

```
{"pod":"devops-app-2","timestamp":"2026-05-01T15:48:36.244959+00:00","visits":1}
```

Each pod maintains its own isolated visit counter, confirming that `volumeClaimTemplates` provides separate persistent storage per pod

---

## 5. Persistence Test

### Before deletion

```
$ kubectl exec devops-app-0 -- cat /data/visits
3
```

### Pod deletion

```
$ kubectl delete pod devops-app-0
pod "devops-app-0" deleted from default namespace
```

### After restart

The StatefulSet controller automatically recreates `devops-app-0` with the same name and reattaches the same PVC:

```
$ kubectl get pods
NAME           READY   STATUS    RESTARTS   AGE
devops-app-0   1/1     Running   0          36s
devops-app-1   1/1     Running   0          4m31s
devops-app-2   1/1     Running   0          4m19s

$ kubectl exec devops-app-0 -- cat /data/visits
3
```

The file still contains `3`. Hitting the visits endpoint increments it to `4`:

```
{"pod":"devops-app-0","timestamp":"2026-05-01T15:50:27.260598+00:00","visits":4}
```

The PVC `data-devops-app-0` persisted through pod deletion. When the StatefulSet recreated the pod, it reattached the same volume, preserving all data
