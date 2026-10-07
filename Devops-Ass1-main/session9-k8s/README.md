# Session 9: Kubernetes Fundamentals and Cluster Architecture

**Name:** Vansh Chitransh
**Course:** SST DevOps & Cloud [SWE]
**Session:** 09 - Kubernetes Fundamentals

Everything below was run on my MacBook Air (Apple M5, macOS 27, arm64) with minikube on the Docker driver.

---

## Task 1: Minikube and kubectl installation check

I installed both tools with Homebrew earlier. This confirms the versions the rest of the sessions use.

```bash
minikube version
kubectl version --client
```

Output on my machine:

```
minikube version: v1.39.0
commit: 7a9f6a841470a207de8cf4bafcccee0969d8ba10

Client Version: v1.37.0
Kustomize Version: v5.8.1
```

![Minikube and kubectl versions](screenshots/01-version-check.png)

---

## Task 2: Starting the minikube cluster

```bash
minikube start
```

I already had a `minikube` profile on this laptop, so minikube reused the existing Docker container instead of creating a new one. That is why the log says "based on existing profile" rather than "Creating docker container". The cluster runs Kubernetes v1.37.0 on containerd 2.3.4.

```
* minikube v1.39.0 on Darwin 27.0 (arm64)
* Using the docker driver based on existing profile
* Starting "minikube" primary control-plane node in "minikube" cluster
* Pulling base image v0.0.51 ...
* Preparing Kubernetes v1.37.0 on containerd 2.3.4 ...
* Verifying Kubernetes components...
  - Using image gcr.io/k8s-minikube/storage-provisioner:v5
* Enabled addons: storage-provisioner, default-storageclass
* Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default
```

![minikube start](screenshots/02-minikube-start.png)

---

## Task 3: Cluster status and node health

```bash
minikube status
kubectl get nodes -o wide
```

All four components report healthy and the single node is `Ready`. The node's internal IP `192.168.49.2` lives on Docker's internal network, which matters later when I try to reach NodePorts from macOS.

```
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured

NAME       STATUS   ROLES           AGE    VERSION   INTERNAL-IP    EXTERNAL-IP   OS-IMAGE                         KERNEL-VERSION            CONTAINER-RUNTIME
minikube   Ready    control-plane   5d4h   v1.37.0   192.168.49.2   <none>        Debian GNU/Linux 12 (bookworm)   7.0.12-linuxkit (arm64)   containerd://2.3.4
```

![minikube status and nodes](screenshots/03-minikube-status.png)

---

## Task 4: Stopping the cluster

```bash
minikube stop
minikube status
```

`minikube stop` powers the node off over SSH and keeps the profile on disk, so the next `minikube start` brings back the same cluster. After stopping, every component shows `Stopped`.

```
* Stopping node "minikube"  ...
* Powering off "minikube" via SSH ...
* 1 node stopped.

minikube
type: Control Plane
host: Stopped
kubelet: Stopped
apiserver: Stopped
kubeconfig: Stopped
```

![minikube stop](screenshots/04-minikube-stop.png)

---

## Task 5: Kubernetes architecture in my own words

Kubernetes splits into a control plane that decides what should run, and worker nodes that actually run it. On minikube both halves live on one node, which is why `kubectl get nodes` shows a single `control-plane` entry.

```
                    CONTROL PLANE
  +-----------+   +----------------+   +----------------+
  |   etcd    |<->| kube-apiserver |<->| kube-scheduler |
  +-----------+   +-------+--------+   +----------------+
                          |
                  +-------v-----------------+
                  | kube-controller-manager |
                  +-------------------------+
                          |
          --------------------------------------
          |                                    |
   WORKER NODE                           WORKER NODE
  +------------+  +------------+       +------------+  +------------+
  |  kubelet   |  | kube-proxy |       |  kubelet   |  | kube-proxy |
  +-----+------+  +------------+       +-----+------+  +------------+
        |                                    |
  +-----v------+                       +-----v------+
  | containerd |                       | containerd |
  +-----+------+                       +-----+------+
        |                                    |
   [Pod] [Pod]                          [Pod] [Pod]
```

### Control plane

- **kube-apiserver** is the only thing anyone talks to. `kubectl`, the scheduler, the controllers and the kubelets all go through its REST API. It validates requests and is the only component allowed to read or write etcd.
- **etcd** is the key-value database holding the whole desired state of the cluster: every Deployment, Service, Secret and their current status. Lose etcd and you lose the cluster's memory.
- **kube-scheduler** watches for Pods that have no node assigned and picks one, looking at CPU and memory requests, node selectors, taints and affinity rules. It only decides; it does not start anything.
- **kube-controller-manager** runs the reconciliation loops. The ReplicaSet controller keeps the replica count right, the Node controller notices dead nodes, the Endpoint controller keeps Services pointed at live Pod IPs. Each loop compares current state with desired state and fixes the difference.

### Worker node

- **kubelet** is the agent on each node. It receives PodSpecs from the API server, asks the container runtime to pull images and start containers, runs the liveness and readiness probes, and reports status back.
- **kube-proxy** programs iptables or IPVS rules so that a Service's ClusterIP and NodePort actually forward to the right Pod IPs.
- **Container runtime** does the low-level work of running containers. My minikube uses containerd 2.3.4, talking to the kubelet over the Container Runtime Interface (CRI).
- **Pod** is the smallest unit Kubernetes schedules: one or more containers that share an IP, port space and volumes. Usually one main container plus optional init or sidecar containers.

### What happens when I run `kubectl apply -f pod.yml`

1. `kubectl` sends the manifest to the **kube-apiserver**, which authenticates me and validates the object.
2. The API server writes the desired Pod into **etcd**.
3. The **kube-scheduler** sees an unscheduled Pod and binds it to a node.
4. The **kubelet** on that node sees the binding, asks **containerd** to pull the image and start the container, then runs probes.
5. When a Service selects the Pod, the Endpoint controller in **kube-controller-manager** adds the Pod IP, and **kube-proxy** on every node updates its rules so traffic reaches it.
