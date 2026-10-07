# Session 13: Kubernetes Storage, HPA and Probes

**Name:** Vansh Chitransh
**Course:** SST DevOps & Cloud [SWE]
**Session:** 13

Three things a real app needs that a plain Deployment does not give you: storage that outlives the Pod, scaling that follows load, and health checks that keep bad Pods out of traffic. Everything here was run on my minikube cluster (v1.37.0, Docker driver, one node) and every screenshot is from that run.

## Folder structure

```
session-13-storage-hpa-probes/
├── 01-kubernetes-volumes/
│   ├── emptydir-pod.yaml      # emptyDir: lives and dies with the Pod
│   ├── hostpath-pod.yaml      # hostPath: a directory on the node
│   ├── pv.yaml                # static PersistentVolume vansh-pv (1Gi, class "manual")
│   ├── pvc.yaml               # claim vansh-pvc that binds to it
│   ├── pod.yaml               # storage-demo Pod mounting the claim at /data
│   └── dynamic-pvc.yaml       # claim against the "standard" StorageClass, no PV written by hand
├── 02-hpa/
│   ├── deployment.yaml        # hpa-demo: nginx with a 100m CPU request
│   ├── service.yaml           # hpa-demo-service
│   └── hpa.yaml               # 1 to 5 replicas, target 50% CPU
├── 03-mini-project/
│   ├── namespace.yaml         # production-webapp
│   ├── pvc.yaml               # web-data, 500Mi
│   ├── deployment.yaml        # web-app: 2 replicas, startup + readiness + liveness probes, /data volume
│   ├── service.yaml           # web-service
│   └── hpa.yaml               # web-app-hpa, 2 to 5 replicas at 50% CPU
├── screenshots/
└── README.md
```

All 14 manifests pass `kubectl apply --dry-run=client` and were applied for real.

## Setup

HPA needs CPU numbers, so the metrics-server addon has to be on.

```bash
minikube start
minikube addons enable metrics-server
minikube status
kubectl get nodes
kubectl get storageclass
kubectl top nodes
```

`kubectl top nodes` answering is the proof that metrics-server works. The only StorageClass is `standard`, backed by `k8s.io/minikube-hostpath`, and it is the default.

![Setup](screenshots/00-setup.png)

---

## Task 1: Volumes

### 1.1 emptyDir: gone with the Pod

```bash
kubectl apply -f 01-kubernetes-volumes/emptydir-pod.yaml
kubectl exec emptydir-demo -- sh -c 'echo "Hello from Vansh via emptyDir" > /data/message.txt'
kubectl exec emptydir-demo -- cat /data/message.txt
kubectl delete pod emptydir-demo
kubectl apply -f 01-kubernetes-volumes/emptydir-pod.yaml
kubectl exec emptydir-demo -- cat /data/message.txt      # No such file or directory
```

The file is there while the Pod lives and gone the moment the Pod is recreated. emptyDir is scratch space shared between containers of one Pod, nothing more.

![emptyDir write](screenshots/01-emptydir.png)

![emptyDir gone after recreate](screenshots/02-emptydir-gone.png)

### 1.2 hostPath: lands on the node

```bash
kubectl apply -f 01-kubernetes-volumes/hostpath-pod.yaml
kubectl exec hostpath-demo -- sh -c 'echo "Hello from Vansh via hostPath" > /data/message.txt'
minikube ssh -- cat /tmp/vansh-hostpath-data/message.txt
```

The same bytes are visible on the node's own filesystem. That is also why hostPath is a bad idea for real apps: the data is tied to one node, and a Pod rescheduled elsewhere will not see it.

![hostPath on the node](screenshots/03-hostpath.png)

### 1.3 Static PV and PVC

```bash
kubectl apply -f 01-kubernetes-volumes/pv.yaml      # vansh-pv: Available
kubectl apply -f 01-kubernetes-volumes/pvc.yaml     # vansh-pvc: Bound, and the PV flips to Bound
kubectl apply -f 01-kubernetes-volumes/pod.yaml
```

The PV starts `Available`. The claim asks for 500Mi of class `manual` with ReadWriteOnce, which matches, so both become `Bound` and the PV shows `default/vansh-pvc` as its claim.

![Static PV and PVC bound](screenshots/04-static-pv.png)

### 1.4 Data survives the Pod

```bash
kubectl exec storage-demo -- sh -c 'echo "Hello from Vansh via PersistentVolume" > /data/message.txt'
kubectl delete pod storage-demo
kubectl apply -f 01-kubernetes-volumes/pod.yaml
kubectl exec storage-demo -- cat /data/message.txt      # still there
```

Same test as 1.1, opposite result. The file lives in the PV, so a brand-new Pod mounting the same claim reads it back.

![PV data survives](screenshots/05-pv-persists.png)

### 1.5 Dynamic provisioning

```bash
kubectl describe storageclass standard
kubectl apply -f 01-kubernetes-volumes/dynamic-pvc.yaml
kubectl get pvc dynamic-pvc
kubectl get pv
```

I never wrote a PV for this claim. The `standard` StorageClass created `pvc-d733feb4-...` on demand, 200Mi, reclaim policy `Delete`, and bound it within seconds. That is what every cloud cluster does with EBS, Persistent Disk and friends.

![Dynamic provisioning](screenshots/06-dynamic.png)

Cleanup: `kubectl delete -f 01-kubernetes-volumes/`.

---

## Task 2: HPA

### 2.1 Deploy

```bash
kubectl apply -f 02-hpa/deployment.yaml -f 02-hpa/service.yaml
```

The container requests `100m` CPU. Without a request the HPA has nothing to compute a percentage against.

![hpa-demo running](screenshots/07-hpa-deploy.png)

### 2.2 Metrics and the HPA object

```bash
kubectl get pods -n kube-system | grep metrics-server
kubectl top nodes
kubectl top pods
kubectl apply -f 02-hpa/hpa.yaml
kubectl get hpa
kubectl describe hpa hpa-demo
```

Right after creation the target reads `<unknown>/50%` and `describe` shows `FailedGetResourceMetric` warnings. That is normal: metrics-server needs about a minute of samples for a new Pod. In the screenshots the target fills in once samples exist.

![metrics-server and HPA](screenshots/08-hpa-metrics.png)

### 2.3 Load and scale-out

```bash
kubectl run load-generator --image=busybox:1.36 --restart=Never -- /bin/sh -c "while true; do wget -q -O- http://hpa-demo-service; done"
for i in 2 3 4; do kubectl run load-generator-$i ...; done     # nginx is light, one generator is not enough
kubectl get hpa -w                                              # second terminal
```

What the watch showed on my cluster:

| Time | CPU target | Replicas |
| --- | --- | --- |
| 60s | 7% / 50% | 1 |
| 2m | 116% / 50% | 1 |
| 2m15s | 116% / 50% | 3 |
| 3m | 58% / 50% | 3 |
| 4m | 41% / 50% | 3 |

At 116 percent the HPA computed `ceil(1 x 116 / 50) = 3` replicas and scaled to 3 in one step; with three Pods sharing the load, utilisation dropped under the target and it stopped there. `describe hpa` records the step as `SuccessfulRescale: New size: 3; reason: cpu resource utilization (percentage of request) above target`, and `kubectl top pods` shows each Pod at about 41m.

![HPA scaling up](screenshots/09-hpa-scale-up.png)

![Scaled Pods and HPA events](screenshots/10-hpa-scaled.png)

### 2.4 Stop the load and scale-in

```bash
kubectl delete pod load-generator load-generator-2 load-generator-3 load-generator-4
kubectl get hpa -w
```

CPU fell to 0 percent within a minute, but the replica count stayed at 3 for the default five-minute stabilisation window, then went 3 to 2 to 1 over the next two minutes. The window exists so a short dip in traffic does not throw Pods away that will be needed again.

![HPA scaling down](screenshots/11-hpa-scale-down.png)

### How the number is computed

`desiredReplicas = ceil(currentReplicas x currentUtilisation / targetUtilisation)`, clamped to `minReplicas`..`maxReplicas`. A request of 100m and usage of 50m is 50 percent. One Pod at 116 percent with a 50 percent target gives 3.

Cleanup: `kubectl delete -f 02-hpa/`.

---

## Task 3: Mini project, a production-shaped web app

Namespace `production-webapp`, a 500Mi PVC mounted at `/data`, two nginx replicas with startup, readiness and liveness probes and CPU requests, a ClusterIP Service, and an HPA from 2 to 5 replicas at 50 percent CPU.

```
                     Service web-service :80
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
      web-app pod        web-app pod        web-app pod (added by HPA)
      startup/readiness/liveness probes, cpu request 100m
            └──────────── HPA web-app-hpa (50% CPU) ◄── metrics-server
      /data ── PVC web-data (500Mi RWO) ── StorageClass standard
```

### 3.1 to 3.3 Deploy

```bash
kubectl apply -f 03-mini-project/namespace.yaml -f 03-mini-project/pvc.yaml
kubectl apply -f 03-mini-project/deployment.yaml -f 03-mini-project/service.yaml
kubectl apply -f 03-mini-project/hpa.yaml
```

![Namespace and PVC](screenshots/12-mp-namespace-pvc.png)

![Deployment and Service](screenshots/13-mp-deploy.png)

![HPA created](screenshots/14-mp-hpa.png)

### 3.4 Storage persistence

```bash
POD_NAME=$(kubectl get pods -n production-webapp -l app=web-app -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n production-webapp "$POD_NAME" -- sh -c 'echo "Student: Vansh" > /data/student.txt'
kubectl delete pod -n production-webapp "$POD_NAME"
NEW_POD=$(kubectl get pods -n production-webapp -l app=web-app -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n production-webapp "$NEW_POD" -- cat /data/student.txt     # Student: Vansh
```

![Write and delete](screenshots/15-mp-persist-write.png)

![Read from the replacement Pod](screenshots/16-mp-persist-read.png)

### 3.5 Service

```bash
kubectl port-forward -n production-webapp svc/web-service 8080:80
curl http://localhost:8080
```

![nginx through the Service](screenshots/17-mp-service.png)

### 3.6 HPA under load

Same load generators as Task 2, in the namespace. The HPA went from 2 to 3 replicas when CPU hit 62 percent, settled at 41 to 46 percent with three Pods, and after the load was removed and the five-minute window passed, returned to 2.

![Scale up to 3](screenshots/18-mp-scale-up.png)

![Scale back to 2](screenshots/19-mp-scale-down.png)

### 3.7 Bonus: readiness gating

```bash
kubectl patch deployment web-app -n production-webapp --type=json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/does-not-exist"}]'
kubectl get pods -n production-webapp
kubectl get endpoints -n production-webapp web-service
```

This produced something more interesting than "all Pods unready". Patching a Deployment starts a rolling update, and the new Pod (`web-app-8577565fb7-ktxfk`) came up `Running` but `0/1` because nginx answers 404 on `/does-not-exist`. Because it never became Ready, the rollout stopped there: the Deployment's `maxUnavailable` kept the two old, healthy Pods serving, and the Service endpoints still listed exactly those two. Readiness failures remove a Pod from traffic without restarting it, and here they also stopped a bad rollout from ever reaching users.

![Readiness gating](screenshots/20-mp-readiness.png)

### 3.8 Bonus: liveness restart loop

```bash
kubectl apply -f 03-mini-project/deployment.yaml      # restore
kubectl patch deployment web-app -n production-webapp --type=json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/httpGet/path","value":"/crash"}]'
kubectl get pods -n production-webapp -w
```

The liveness probe hits `/crash`, nginx returns 404, and after three failures five seconds apart the kubelet restarts the container: the watch shows `RESTARTS` ticking to 1 about 15 seconds after the new Pods start, and the cycle repeats. Liveness restarts; readiness only unplugs. Restoring the manifest brought both replicas back to `1/1`.

![Liveness restarts](screenshots/21-mp-liveness.png)

### Probe cheat sheet

| Probe | Question | On failure |
| --- | --- | --- |
| Startup | Has the process finished booting? | Container restarted; other probes wait until it passes |
| Readiness | Can this Pod take traffic right now? | Pod IP removed from Service endpoints; no restart |
| Liveness | Is the container still alive? | Kubelet restarts the container |

### Things that went wrong and how I checked

| Symptom | Check | Cause | Fix |
| --- | --- | --- | --- |
| HPA shows `<unknown>/50%` | `kubectl top pods -n production-webapp` | metrics-server not ready, or no CPU request | Wait a minute; keep `cpu: 100m` in the request |
| One load generator did not move the needle | `kubectl top pods` | nginx serves a static page in microseconds | Start three more generators |
| Pods did not all go unready in 3.7 | `kubectl get endpoints` | A Deployment rolls out gradually and keeps old Pods until new ones are Ready | Expected behaviour; see 3.7 |

Cleanup: `kubectl delete namespace production-webapp`.

---

## What I took away

- emptyDir is per-Pod scratch, hostPath is per-node, and a PVC is the only one that survives rescheduling.
- A PV is the storage; a PVC is the request for it; a StorageClass is the factory that makes PVs on demand.
- The HPA is arithmetic on `usage / request`. No request, no scaling. It scales out fast and in slowly, on purpose.
- Readiness protects users from a Pod; liveness protects a Pod from itself; startup protects slow apps from liveness.
