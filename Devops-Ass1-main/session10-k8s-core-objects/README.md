# Session 10: Kubernetes Core Objects - Pods, Controllers and Deployment Strategies

**Name:** Vansh Chitransh
**Course:** SST DevOps & Cloud [SWE]
**Session:** 10

I wrote every manifest in this folder myself and ran each task against my local minikube cluster (v1.37.0, Docker driver, one node) on my MacBook Air. All terminal screenshots are from those runs. Where the macOS Docker driver got in the way (NodePorts are not reachable from the Mac itself) I say so and show what I did instead.

## Folder structure

```
session10-k8s-core-objects/
├── pod.yml                     # Task 2: nginx-pod
├── hello.yml                   # Task 4: hello-pod (busybox, runs once)
├── replicaset.yml              # Task 6: nginx-rs
├── pod-lifecycle/              # Task 3 and 5: 12 lifecycle manifests
├── k8s-core-objects/
│   ├── statefulset.yml         # Task 6: mysql StatefulSet + headless Service
│   └── daemonset.yml           # Task 7: node-exporter DaemonSet
├── daemonset/node-agent-ds.yaml  # Task 7: busybox host agent
├── deployment/                 # Task 9: web v1/v2
├── 01-rolling-update/          # Task 8: app-rolling v1/v2 + NodePort 30010
├── 02-blue-green/              # Task 11: app-blue / app-green + myapp-service (30020)
├── 03-canary/                  # Task 12: app-stable / app-canary + shared Service (30030)
├── 04-recreate/                # Task 13: app-recreate v1/v2 + Service (30040)
├── troubleshooting/            # Task 9: broken-image + selector-mismatch
└── screenshots/
```

All 35 manifests pass `kubectl apply --dry-run=client`. Every one of them was also applied for real, as the screenshots show.

---

## Task 1: Cluster health check

```bash
kubectl version
kubectl cluster-info
kubectl get nodes -o wide
```

Client and server are both v1.37.0. The API server is reachable on a localhost port that minikube forwards into the Docker container, and CoreDNS is running. My cluster has one node that is both control plane and worker.

```
Kubernetes control plane is running at https://127.0.0.1:51232
CoreDNS is running at https://127.0.0.1:51232/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

NAME       STATUS   ROLES           AGE    VERSION   INTERNAL-IP    OS-IMAGE                         CONTAINER-RUNTIME
minikube   Ready    control-plane   5d4h   v1.37.0   192.168.49.2   Debian GNU/Linux 12 (bookworm)   containerd://2.3.4
```

![Cluster health](screenshots/01-cluster-health.png)

---

## Task 2: A plain Pod (`pod.yml`)

The manifest has the four required top-level fields: `apiVersion`, `kind`, `metadata` and `spec`. It runs one `nginx:1.27-alpine` container.

```bash
kubectl apply -f pod.yml
kubectl get pods
kubectl get pods -o wide
kubectl logs nginx-pod
kubectl delete -f pod.yml
kubectl get pods
```

The pod was `1/1 Running` within six seconds, got pod IP `10.244.0.4` on node `minikube`, and the logs show nginx 1.27.5 starting its worker processes. After the delete, `kubectl get pods` returns nothing.

![nginx pod operations](screenshots/02-nginx-pod-operations.png)

---

## Task 3: ErrImagePull and ImagePullBackOff

`pod-lifecycle/06-imagepullbackoff.yaml` asks for `nginx:this-tag-does-not-exist-vansh`. The API server accepts the object (the YAML is valid), but the kubelet cannot pull the image.

```bash
kubectl apply -f pod-lifecycle/06-imagepullbackoff.yaml
kubectl get pods lifecycle-image-error
kubectl describe pod lifecycle-image-error | grep -A 10 Events:
kubectl delete -f pod-lifecycle/06-imagepullbackoff.yaml
```

The status column shows `ErrImagePull` right after each failed attempt, and the events show the kubelet alternating between `Pulling`, `Failed ... not found`, `ErrImagePull` and `BackOff` / `ImagePullBackOff` with a growing delay between attempts.

![ImagePullBackOff](screenshots/03-imagepullbackoff-error.png)

---

## Task 4: Watching a short-lived pod (`hello.yml`)

`hello-pod` runs busybox, prints one line, sleeps three seconds and exits 0. With `restartPolicy: Never` it ends in `Completed`.

I started `kubectl get pods -w` in a second terminal before applying, so the watch caught every transition:

```
hello-pod   0/1     Pending             0          0s
hello-pod   0/1     ContainerCreating   0          0s
hello-pod   1/1     Running             0          0s
hello-pod   0/1     Completed           0          4s
```

`kubectl logs hello-pod` prints `Hello from Vansh busybox pod`.

![Pod lifecycle stages](screenshots/04-pod-lifecycle-stages.png)

---

## Task 5: Pod lifecycle and probes lab (`pod-lifecycle/`)

| File | Pod | What it shows on my cluster |
| --- | --- | --- |
| `01-running.yaml` | `lifecycle-running` | Normal Running pod |
| `02-pending.yaml` | `lifecycle-pending` | Requests 900Gi memory, stays `Pending` with `FailedScheduling: 0/1 nodes are available: 1 Insufficient memory` |
| `03-succeeded.yaml` | `lifecycle-succeeded` | Exit 0 with `restartPolicy: Never` |
| `04-failed.yaml` | `lifecycle-failed` | Exit 1 with `restartPolicy: Never` |
| `05-crashloopbackoff.yaml` | `lifecycle-crashloop` | Exits 1 every time, `restartPolicy: Always`. RESTARTS climbs (2, then 3) and the events show `Back-off restarting failed container` |
| `06-imagepullbackoff.yaml` | `lifecycle-image-error` | Task 3 above |
| `07-readiness.yaml` | `lifecycle-readiness` | `Running` but `0/1`: readiness probe `cat /tmp/ready` fails because the file never exists |
| `08-liveness.yaml` | `lifecycle-liveness` | Healthy for 10s, then `/tmp/healthy` is removed. Liveness probe fails, kubelet kills and restarts the container, RESTARTS goes 0 to 1 |
| `09-startup.yaml` | `lifecycle-startup` | Startup probe (30 x 2s) gates the liveness probe until nginx answers |
| `10-init-container.yaml` | `lifecycle-init` | Shows `Init:0/1` first, then `Running` after `init-setup` finishes |
| `11-multi-container.yaml` | `lifecycle-multi-container` | nginx plus a busybox sidecar, `READY 2/2` |
| `12-termination.yaml` | `lifecycle-termination` | Traps SIGTERM, cleans up for 8s. `kubectl delete` took 9.5s instead of returning instantly |

One thing I noticed: on Kubernetes v1.37 with containerd, the STATUS column for the crashing pod reads `Error` between restarts rather than `CrashLoopBackOff`. The back-off itself is visible in the events (`Warning BackOff ... Back-off restarting failed container`) and in the restart counter.

Commands I ran, from inside `pod-lifecycle/`:

```bash
kubectl apply -f 02-pending.yaml && kubectl get pod lifecycle-pending
kubectl describe pod lifecycle-pending | grep -A 5 Events:

kubectl apply -f 05-crashloopbackoff.yaml && kubectl get pod lifecycle-crashloop
kubectl logs lifecycle-crashloop
kubectl describe pod lifecycle-crashloop | grep BackOff

kubectl apply -f 07-readiness.yaml && kubectl get pod lifecycle-readiness
kubectl apply -f 08-liveness.yaml && kubectl get pod lifecycle-liveness   # RESTARTS 1 after ~40s
kubectl apply -f 09-startup.yaml && kubectl describe pod lifecycle-startup | grep -E "Startup:|Liveness:"

kubectl apply -f 10-init-container.yaml && kubectl get pod lifecycle-init
kubectl logs lifecycle-init -c init-setup
kubectl apply -f 11-multi-container.yaml && kubectl logs lifecycle-multi-container -c sidecar
kubectl apply -f 12-termination.yaml && time kubectl delete -f 12-termination.yaml
```

![Probes and crash loop](screenshots/05-lifecycle-probes-crashloop.png)

![Init container, sidecar and graceful termination](screenshots/05-lifecycle-init-multicontainer.png)

---

## Task 6: ReplicaSet and StatefulSet

**ReplicaSet.** `nginx-rs` keeps three nginx pods. I deleted one pod by hand (`nginx-rs-fmsxx`) and four seconds later a replacement (`nginx-rs-h5nzd`) was already Running. The ReplicaSet never dropped below `3/3` in `kubectl get rs`.

**StatefulSet.** `mysql` has three replicas, a headless Service (`clusterIP: None`) and a `volumeClaimTemplates` entry, so each pod gets its own 1Gi PersistentVolumeClaim. The pods are named by ordinal (`mysql-0`, `mysql-1`, `mysql-2`) and the PVCs follow the same pattern (`data-mysql-0` ... `data-mysql-2`), all `Bound` through minikube's `standard` storage class.

```bash
kubectl apply -f replicaset.yml
kubectl get rs nginx-rs; kubectl get pods -l app=nginx
kubectl delete pod <one nginx-rs pod>; kubectl get pods -l app=nginx
kubectl delete -f replicaset.yml

kubectl apply -f k8s-core-objects/statefulset.yml
kubectl get statefulset mysql; kubectl get pods -l app=mysql -o wide; kubectl get pvc; kubectl get svc mysql
kubectl delete -f k8s-core-objects/statefulset.yml
```

![ReplicaSet and StatefulSet](screenshots/06-controllers-rs-statefulset.png)

---

## Task 7: DaemonSets

A DaemonSet runs exactly one pod per eligible node. My cluster has one node, so DESIRED, CURRENT and READY are all `1` for both `node-exporter` (`prom/node-exporter:v1.8.2`) and my lighter `node-agent` (busybox that prints the node name it landed on, read from `spec.nodeName` through the downward API). The agent's log line is `node-agent alive on minikube`.

```bash
kubectl apply -f k8s-core-objects/daemonset.yml
kubectl get ds node-exporter; kubectl get pods -l app=node-exporter -o wide
kubectl apply -f daemonset/node-agent-ds.yaml
kubectl get ds node-agent; kubectl logs -l app=node-agent
```

![DaemonSet verification](screenshots/07-daemonset-verification.png)

---

## Task 8: Rolling update and rollback (`01-rolling-update/`)

`app-rolling` has four replicas, `maxSurge: 1` and `maxUnavailable: 0`, and a readiness probe so a new pod only counts once nginx answers. v1 uses `nginx:1.25-alpine`, v2 uses `nginx:1.27-alpine`.

```bash
kubectl apply -f deployment-v1.yaml -f service.yaml
kubectl rollout status deployment/app-rolling
kubectl apply -f deployment-v2.yaml
kubectl rollout status deployment/app-rolling
kubectl get pods -l app=app-rolling --show-labels
kubectl rollout history deployment/app-rolling
kubectl rollout undo deployment/app-rolling
kubectl rollout status deployment/app-rolling
```

What the output shows:

- During the v2 rollout the status went `1 out of 4 new replicas`, `2 out of 4`, `3 out of 4`, then `1 old replicas are pending termination`. With `maxSurge: 1` there were never more than five pods, and with `maxUnavailable: 0` four were always serving.
- Right after the rollout, `--show-labels` shows four `version=v2` pods Running and the last `version=v1` pod Terminating.
- `rollout history` lists revisions 1 and 2. After `rollout undo` the pods are back on `version=v1` (new hash `65948c9c69`) and history shows revisions 2 and 3, because a rollback is itself a new revision.

![Rolling update and rollback](screenshots/08-rolling-update-and-rollback.png)

---

## Task 9: Troubleshooting drills (`troubleshooting/`)

**Drill 1: broken image during a rollout.** I applied a healthy `web` deployment (`deployment/deployment-v1.yaml`), then `broken-image.yaml`, which is the same Deployment with `nginx:1.99-does-not-exist`. The rollout created one surge pod, which sat in `ImagePullBackOff`, while the three old pods stayed `Running`. `kubectl rollout status --timeout=30s` timed out, and the Deployment condition still said `Available True MinimumReplicasAvailable`, meaning users were never affected. `kubectl rollout undo` removed the bad pod.

**Drill 2: selector does not match the template.** `selector-mismatch.yaml` selects `app: foo` but labels the pods `app: bar`. `kubectl apply --dry-run=client` says `created (dry run)` because that check only happens on the server. The real apply is rejected:

```
The Deployment "selector-error-demo" is invalid: spec.template.metadata.labels: Invalid value: {"app":"bar"}: `selector` does not match template `labels`
```

Fixing the label (`sed "s/app: bar/app: foo/" selector-mismatch.yaml | kubectl apply -f -`) makes it go through and the Deployment reaches `1/1`.

![Troubleshooting drills](screenshots/09-troubleshooting-drills.png)

---

## Task 10: Concepts in my own words

**The four ports.** `containerPort` is where the process listens inside the container. `targetPort` is where the Service sends traffic on the pod, and must match it. `port` is the Service's own port on its ClusterIP. `nodePort` (30000 to 32767) is opened on every node for traffic from outside. For a NodePort Service the path is `client -> nodeIP:nodePort -> clusterIP:port -> podIP:targetPort`.

**Labels and selectors.** Labels are key-value tags on objects (`app=myapp`, `slot=blue`). Selectors are how ReplicaSets, Deployments and Services find the pods they own or route to. In Task 11 the whole blue-green switch is just changing one selector value.

**Four deployment strategies.**

- RollingUpdate: replace pods gradually, no downtime, both versions run briefly. Default.
- Recreate: kill every old pod, then start the new ones. Downtime, but never two versions at once.
- Blue-Green: run both versions fully, flip the Service selector. Instant switch and instant rollback, needs double capacity.
- Canary: send a small share of traffic to the new version by running a few new pods behind the same Service, then grow it.

**maxSurge and maxUnavailable.** For `replicas: 4`, `maxSurge: 1`, `maxUnavailable: 0`: at most 5 pods exist during the rollout, and at least 4 are available the whole time. That is exactly what I saw in Task 8.

**Requests and limits.** A request is what the scheduler reserves for the pod (Task 5's 900Gi request could not be placed anywhere). A limit is the ceiling enforced by cgroups: CPU over the limit is throttled, memory over the limit gets the container OOM-killed. `1Gi` is 2^30 bytes, `1G` is 10^9 bytes.

---

## Task 11: Blue-Green (`02-blue-green/`)

Both `app-blue` and `app-green` run three `hashicorp/http-echo` pods that answer with their own colour and version. `myapp-service` (NodePort 30020) has selector `app=myapp,slot=blue` in `service-blue.yaml` and `slot=green` in `service-green.yaml`.

```bash
kubectl apply -f deployment-blue.yaml -f deployment-green.yaml
kubectl apply -f service-blue.yaml
kubectl describe svc myapp-service | grep Selector; kubectl get endpoints myapp-service
minikube ssh -- curl -s http://$(minikube ip):30020      # BLUE ENVIRONMENT - Vansh app v1
kubectl apply -f service-green.yaml
kubectl describe svc myapp-service | grep Selector; kubectl get endpoints myapp-service
minikube ssh -- curl -s http://$(minikube ip):30020      # GREEN ENVIRONMENT - Vansh app v2
kubectl apply -f service-blue.yaml                        # instant rollback
minikube ssh -- curl -s http://$(minikube ip):30020      # BLUE ENVIRONMENT - Vansh app v1
```

The endpoints list switched from the three blue pod IPs (`10.244.0.76-78`) to the three green ones (`10.244.0.79-81`) the moment the selector changed. No pod was restarted.

About the curl: with the Docker driver on macOS the node IP `192.168.49.2` is not routable from the Mac, so I ran curl from inside the node with `minikube ssh`. That still goes through the NodePort.

![Blue-green cutover](screenshots/11-blue-green-cutover.png)

---

## Task 12: Canary (`03-canary/`)

`app-stable` (9 pods, answers `STABLE v1`) and `app-canary` (1 pod, answers `CANARY v2`) share one Service, `myapp-canary-service`, whose selector is only `app=myapp-canary`. kube-proxy spreads connections across all ten endpoints, so the canary gets roughly one request in ten.

I measured it with 30 requests from a curl pod inside the cluster:

| Pods (stable : canary) | Result of 30 requests |
| --- | --- |
| 9 : 1 | 29 STABLE v1, 1 CANARY v2 |
| 7 : 3 | 23 STABLE v1, 7 CANARY v2 |
| 9 : 0 (canary aborted) | 10 of 10 STABLE v1 |

```bash
kubectl apply -f deployment-stable.yaml -f service.yaml -f deployment-canary.yaml
kubectl get pods -l app=myapp-canary --show-labels
kubectl exec curl-client -- sh -c 'for i in $(seq 1 30); do curl -s http://myapp-canary-service; done' | sort | uniq -c
kubectl scale deployment app-canary --replicas=3; kubectl scale deployment app-stable --replicas=7
kubectl scale deployment app-canary --replicas=0; kubectl scale deployment app-stable --replicas=9
```

![Canary traffic split](screenshots/12-canary-traffic-split.png)

---

## Task 13: Recreate and the downtime window (`04-recreate/`)

`app-recreate` uses `strategy.type: Recreate`. I ran two extra terminals before applying v2: one with `kubectl get pods -w`, one with a curl loop from the in-cluster curl pod that prints `[OUTAGE]` whenever nothing answers.

The watch shows all three v1 pods go to `Terminating` together, and only after they are gone do the three v2 pods appear as `Pending`, `ContainerCreating`, `Running`. The curl loop shows the gap:

```
VERSION: v1
VERSION: v1
[OUTAGE] no pods answering
VERSION: v2 (UPGRADED)
VERSION: v2 (UPGRADED)
```

The outage was short here because http-echo starts in well under a second and the image was already cached. A heavier app would leave a much longer gap, which is why Recreate is only acceptable when two versions truly cannot coexist.

`kubectl rollout undo` brought back v1 (again with a full stop-then-start), and a final curl returned `VERSION: v1`.

![Recreate outage](screenshots/13-recreate-downtime-outage.png)
