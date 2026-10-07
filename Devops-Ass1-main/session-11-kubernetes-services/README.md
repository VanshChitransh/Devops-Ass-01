# Session 11: Kubernetes Services and Networking

**Name:** Vansh Chitransh
**Course:** SST DevOps & Cloud [SWE]
**Session:** 11

The five Service types (ClusterIP, NodePort, LoadBalancer, ExternalName, Headless), Services without selectors, how CoreDNS names things, how Deployments and StatefulSets treat pod identity differently, and how I would pick a Service type in production. Everything was run on my minikube cluster (v1.37.0, Docker driver) on my MacBook Air; every screenshot is from that run.

## Folder structure

```
session-11-kubernetes-services/
├── 01-clusterip/
│   ├── app-deployment.yaml      # web-app-clusterip, 3 nginx replicas
│   ├── service.yaml             # ClusterIP web-service-clusterip, 8080 -> 80
│   └── client-pod.yaml          # curl-client (curlimages/curl, has curl + nslookup)
├── 02-nodeport/
│   ├── app-deployment.yaml      # web-app-nodeport, 2 replicas
│   └── service.yaml             # NodePort web-service-nodeport, 80 -> 80, nodePort 30080
├── 03-loadbalancer/
│   ├── app-deployment.yaml      # web-app-loadbalancer, 3 replicas
│   └── service.yaml             # LoadBalancer web-service-loadbalancer, 80 -> 80
├── 04-externalname/
│   ├── service.yaml             # ExternalName external-database-service -> api.github.com
│   └── client-pod.yaml          # dns-test-client
├── 05-headless/
│   ├── service.yaml             # Headless web-service-headless (clusterIP: None)
│   ├── app-statefulset.yaml     # StatefulSet web-stateful, 3 replicas
│   └── client-pod.yaml          # headless-dns-client
├── decision-tree.txt            # Task 11 notes as plain text
├── screenshots/
└── README.md
```

All 12 manifests pass `kubectl apply --dry-run=client` and were applied for real.

One note that applies to several tasks: I am on macOS with the Docker driver, so the node IP `192.168.49.2` is on Docker's internal bridge and my Mac cannot route to it, and `minikube tunnel` needs sudo, which I did not have in the session where I recorded this. Wherever a task needed the node IP I either ran curl from inside the node (`minikube ssh -- curl ...`) or used `minikube service <name> --url`, which opens a loopback tunnel. Task 12 is about exactly this.

---

## Task 1: The four ports

| Port | Lives in | Meaning |
| --- | --- | --- |
| `containerPort` | Pod spec, container | Where the process listens inside the container. Documentation more than enforcement. |
| `targetPort` | Service spec | Pod-side port the Service forwards to. Must match what the container listens on. |
| `port` | Service spec | The Service's own port on its ClusterIP. |
| `nodePort` | Service spec (NodePort or LoadBalancer) | Port 30000 to 32767 opened on every node for outside traffic. |

Packet path for my NodePort Service in Task 3:

```
client -> 192.168.49.2:30080 (nodePort)
       -> 10.106.191.74:80   (Service port on the ClusterIP)
       -> 10.244.0.109:80    (targetPort on a pod)
       -> nginx listening on containerPort 80
```

```bash
kubectl explain pod.spec.containers.ports.containerPort
kubectl explain service.spec.ports.port
kubectl explain service.spec.ports.targetPort
kubectl explain service.spec.ports.nodePort
```

![Port definitions from kubectl explain](screenshots/01-ports.png)

---

## Task 2: ClusterIP

```bash
kubectl apply -f 01-clusterip/app-deployment.yaml -f 01-clusterip/service.yaml
kubectl get pods -l app=web-clusterip -o wide
kubectl get svc web-service-clusterip
kubectl get endpoints web-service-clusterip
kubectl apply -f 01-clusterip/client-pod.yaml
kubectl exec curl-client -- curl -s http://web-service-clusterip:8080 | grep -i "<title>"
kubectl exec curl-client -- curl -s http://web-service-clusterip.default.svc.cluster.local:8080 | grep -i "<title>"
```

The Service got ClusterIP `10.104.56.207` and its endpoints list filled in with the three pod IPs (`10.244.0.105-107`) on port 80 automatically, because the selector `app=web-clusterip` matches the Deployment's pods. From the curl pod, both the short name and the full FQDN return `<title>Welcome to nginx!</title>`, and hitting the raw ClusterIP returns HTTP 200. Nothing outside the cluster can reach this address.

![ClusterIP service and endpoints](screenshots/02-clusterip.png)

---

## Task 3: NodePort

```bash
kubectl apply -f 02-nodeport/app-deployment.yaml -f 02-nodeport/service.yaml
kubectl get svc web-service-nodeport          # 80:30080/TCP
minikube ssh -- curl -sI http://192.168.49.2:30080
minikube service web-service-nodeport --url   # http://127.0.0.1:52006 on my run
curl -sI http://127.0.0.1:52006
```

The Service shows `80:30080/TCP`. Curl against the node IP on 30080, run from inside the node, returns `HTTP/1.1 200 OK` from nginx 1.27.5. The same request from my Mac works through the loopback URL that `minikube service --url` opens.

![NodePort service](screenshots/03-nodeport.png)

---

## Task 4: LoadBalancer

```bash
kubectl apply -f 03-loadbalancer/app-deployment.yaml -f 03-loadbalancer/service.yaml
kubectl get svc web-service-loadbalancer
kubectl describe svc web-service-loadbalancer | grep -E "^Type|^IP:|^NodePort|^Endpoints"
minikube service web-service-loadbalancer --url
```

A LoadBalancer Service is a NodePort Service plus a request to the cloud provider for an external address. Kubernetes allocated the ClusterIP `10.103.3.177` and NodePort `32264` on its own, and the endpoints filled in. `EXTERNAL-IP` stays `<pending>` on my laptop because there is no cloud controller to answer the request. On minikube the usual fix is `minikube tunnel`, which needs sudo and was not available in my recording session, so I reached the Service through `minikube service --url` instead and got the nginx page back. On a real cloud the same manifest would get a public IP within a minute or two.

![LoadBalancer service](screenshots/04-loadbalancer.png)

---

## Task 5: ExternalName

```bash
kubectl apply -f 04-externalname/service.yaml -f 04-externalname/client-pod.yaml
kubectl get svc external-database-service
kubectl get endpoints external-database-service
kubectl exec dns-test-client -- nslookup external-database-service
kubectl exec dns-test-client -- curl -s -k -o /dev/null -w "HTTP %{http_code} from %{remote_ip}\n" https://external-database-service
```

`TYPE ExternalName`, `CLUSTER-IP <none>`, `EXTERNAL-IP api.github.com`, and there is no Endpoints object at all (`kubectl get endpoints` says not found). CoreDNS answers the in-cluster name with a CNAME: `external-database-service.default.svc.cluster.local canonical name = api.github.com`, then resolves that to `20.207.73.85`. The curl reached GitHub's server (the remote IP in the output) and got HTTP 400, which is expected: I sent TLS with the wrong server name, so GitHub refused the request. The point is that the alias resolved and traffic left the cluster.

The `NXDOMAIN` lines above the answer are busybox's nslookup trying each search domain from `/etc/resolv.conf` in turn; the real answer is the `default.svc.cluster.local` one.

![ExternalName service](screenshots/05-externalname.png)

---

## Task 6: Headless Service with a StatefulSet

```bash
kubectl apply -f 05-headless/service.yaml -f 05-headless/app-statefulset.yaml -f 05-headless/client-pod.yaml
kubectl rollout status statefulset/web-stateful --timeout=120s
kubectl get pods -l app=web-headless -o wide
kubectl get svc web-service-headless          # CLUSTER-IP None
kubectl exec headless-dns-client -- nslookup web-service-headless
kubectl exec headless-dns-client -- nslookup web-stateful-0.web-service-headless.default.svc.cluster.local
kubectl exec headless-dns-client -- curl -s http://web-stateful-0.web-service-headless:80 | grep -i "<title>"
```

With `clusterIP: None` there is no virtual IP to load-balance through. `nslookup web-service-headless` returns three A records, one per pod (`10.244.0.115`, `.117`, `.118`), and each pod also has its own stable name: `web-stateful-0.web-service-headless.default.svc.cluster.local` resolves to `10.244.0.115`, and curl to that name works. This is what databases and message brokers need: peers can address a specific replica, not "any replica".

![Headless service](screenshots/06-headless.png)

---

## Task 7: A Service without a selector

Sometimes the backend is not a set of pods: a legacy database on a fixed IP, for example. A Service with no selector gets a ClusterIP but no endpoints, and I attach the backend by writing the Endpoints object myself.

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: vansh-legacy-db
spec:
  ports:
    - protocol: TCP
      port: 3306
      targetPort: 3306
EOF
kubectl get endpoints vansh-legacy-db        # not found: nothing selected

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Endpoints
metadata:
  name: vansh-legacy-db
subsets:
  - addresses:
      - ip: 192.168.1.150
    ports:
      - port: 3306
EOF
kubectl get endpoints vansh-legacy-db        # 192.168.1.150:3306
```

After the second apply, anything in the cluster can talk to `vansh-legacy-db:3306` and kube-proxy forwards it to `192.168.1.150`. Kubernetes 1.33+ prints a warning that the `v1 Endpoints` API is deprecated in favour of EndpointSlices; it still works.

![Manual endpoints](screenshots/07-endpoints.png)

---

## Task 8: CoreDNS and FQDNs

```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide
kubectl get svc -n kube-system kube-dns                 # 10.96.0.10
kubectl exec curl-client -- cat /etc/resolv.conf
kubectl exec curl-client -- nslookup web-service-clusterip
kubectl exec curl-client -- nslookup api.github.com
```

Inside every pod, `/etc/resolv.conf` points at the `kube-dns` Service IP `10.96.0.10` (one CoreDNS pod on my cluster) and carries:

```
search default.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

A Kubernetes FQDN is `<service>.<namespace>.svc.cluster.local`. The search list is why I can type just `web-service-clusterip` and get `web-service-clusterip.default.svc.cluster.local -> 10.104.56.207`.

**Why `ndots:5` costs time.** Any name with fewer than five dots is tried with each search suffix before being tried as-is. `api.github.com` has two dots, so the resolver first asks for `api.github.com.default.svc.cluster.local`, `api.github.com.svc.cluster.local` and `api.github.com.cluster.local`, gets NXDOMAIN three times, and only then asks for the real name. You can see those NXDOMAIN answers in the screenshot. In a service that makes many external calls this adds up; ending the name with a dot (`api.github.com.`) marks it absolute and skips the search list.

![CoreDNS and resolv.conf](screenshots/08-coredns.png)

---

## Task 9: Pod identity, Deployment versus StatefulSet

I kept the Deployment from Task 2 and the StatefulSet from Task 6 running, then deleted one pod from each.

```bash
kubectl get pods -l app=web-clusterip     # web-app-clusterip-5d8d57b975-24phx, -9dj2k, -xkmmf
kubectl get pods -l app=web-headless      # web-stateful-0, -1, -2
kubectl delete pod web-app-clusterip-5d8d57b975-24phx
kubectl get pods -l app=web-clusterip     # replacement is -qqhpc: a brand-new name
kubectl delete pod web-stateful-0
kubectl get pods -l app=web-headless      # web-stateful-0 is back with the same name
```

The Deployment's ReplicaSet created a pod with a fresh random suffix (`qqhpc`), because to a Deployment every pod is interchangeable. The StatefulSet recreated `web-stateful-0` with exactly the same name, and therefore the same DNS entry from Task 6 and the same PVC if it had one. That stable identity is the whole reason StatefulSets exist.

![Pod identity drill](screenshots/09-identity.png)

---

## Task 10: Deployment, StatefulSet, DaemonSet side by side

| | Deployment | StatefulSet | DaemonSet |
| --- | --- | --- | --- |
| Meant for | Stateless services, web and API tiers | Databases, queues, anything with peers or per-replica data | Per-node agents: logs, metrics, networking |
| Pod names | `<name>-<rs hash>-<random>` | `<name>-0`, `<name>-1`, ... | `<name>-<random>`, one per node |
| Identity after a restart | New name, new IP | Same name, same DNS record, same volume | Bound to its node |
| Start and stop order | All at once | Ordered: 0, then 1, then 2; reverse on scale-down | One per node as nodes appear |
| Storage | Shared or ephemeral | `volumeClaimTemplates`: one PVC per pod | Usually hostPath |
| Service pairing | ClusterIP, NodePort, LoadBalancer | Headless Service (`clusterIP: None`) | Usually none |
| Scaling | Any number, any node | By ordinal, one at a time | Follows the node count |
| Examples | nginx, my Node.js and Flask apps | MySQL (Session 10 Task 6), Kafka, Postgres | kube-proxy, kindnet, node-exporter |

```bash
kubectl get deploy,sts,ds -A
```

On my cluster that shows my three Deployments and the `web-stateful` StatefulSet in `default`, and the `kindnet` and `kube-proxy` DaemonSets that minikube itself runs in `kube-system`, one pod each because I have one node.

![Controller matrix evidence](screenshots/10-matrix.png)

---

## Task 11: Choosing a Service type, and why not fifty LoadBalancers

The decision tree I use is in `decision-tree.txt`:

```
Does anything outside the cluster need to reach this workload?
|
+-- NO --> Do clients need each pod's own address (databases, Kafka, anything with peers)?
|          +-- YES --> HEADLESS SERVICE (clusterIP: None) + StatefulSet
|          +-- NO  --> CLUSTERIP (the default)
|
+-- YES --> Is the target actually an outside host (managed DB, payment API)?
            +-- YES --> EXTERNALNAME (a DNS alias, no pods behind it)
            +-- NO  --> Running on a public cloud?
                        +-- YES, HTTP/HTTPS --> ONE LOADBALANCER in front of an INGRESS
                        |                        controller, apps stay CLUSTERIP
                        +-- YES, raw TCP/UDP --> LOADBALANCER per service
                        +-- NO (laptop / on-prem) --> NODEPORT (or Ingress via NodePort)
```

**The cost problem.** Every `type: LoadBalancer` Service on AWS, GCP or Azure provisions a real cloud load balancer, billed by the hour whether or not it carries traffic (roughly $18 to $25 a month each, plus data). Fifty microservices exposed that way is fifty load balancers, so around $900 to $1,250 a month before a single request. The alternative is one LoadBalancer Service in front of an Ingress controller (Session 12), which routes by hostname and path to fifty plain ClusterIP Services. One bill, one public IP, one place for TLS.

![Decision tree](screenshots/11-decision-tree.png)

---

## Task 12: Why `curl <node-ip>:<nodePort>` fails on macOS with the Docker driver

```bash
kubectl get svc web-service-nodeport
curl --connect-timeout 3 -s http://$(minikube ip):30080 || echo "Connection failed as expected"
docker network inspect minikube --format "{{range .IPAM.Config}}{{.Subnet}}{{end}}"   # 192.168.49.0/24
minikube service web-service-nodeport --url        # workaround 1
curl -sI http://127.0.0.1:52071 | head -3
minikube ssh -- curl -sI http://192.168.49.2:30080 | head -3    # workaround 2
```

On Linux the node IP is a real interface on the machine, so NodePorts just work. With the Docker driver on macOS the "node" is a container on a Docker bridge network (`192.168.49.0/24`), and Docker Desktop's Linux VM sits between that network and macOS. Packets from my Mac to `192.168.49.2` have nowhere to go, so the curl times out, as the screenshot shows.

Two ways around it, both shown working:

1. `minikube service <svc> --url` opens an SSH tunnel and prints a `127.0.0.1:<random port>` URL that forwards to the NodePort. It has to stay running in its terminal.
2. Run the request from inside the node with `minikube ssh`, where `192.168.49.2` is local. Good for quick checks.

A third option is `minikube tunnel`, which adds a route on the Mac so node IPs and LoadBalancer IPs become reachable directly. It needs sudo, which I did not have in this session.

![Docker driver NodePort gotcha](screenshots/12-tunnel-gotcha.png)
