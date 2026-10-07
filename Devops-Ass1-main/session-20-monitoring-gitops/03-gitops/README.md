# GitOps with Argo CD

**Name:** Vansh Chitransh
**Session:** 20, Task 3

## What GitOps is

GitOps runs infrastructure and applications with **Git as the single source of truth**. I change the system by changing files and pushing; an agent inside the cluster notices and makes the real cluster match. Nobody runs `kubectl apply` by hand.

| Idea | Meaning |
| --- | --- |
| Git is the source of truth | The desired state lives in a repository; the cluster is a copy of it |
| Declarative | Files say *what* should exist (`replicas: 2`), not the steps to get there |
| Versioned and auditable | Every change is a commit with an author, a message and a diff |
| Pull-based | The agent in the cluster pulls from Git; the cluster needs no inbound access and CI needs no cluster credentials |
| Continuous reconciliation | The agent keeps comparing live state with Git and corrects drift |

```
 push     ┌──────────┐  pull/compare  ┌──────────┐  apply  ┌─────────────┐
──────────► Git      ├───────────────► Argo CD   ├────────► Kubernetes  │
          │ desired  │                │ reconciler│         │ actual     │
          └──────────┘                └─────▲─────┘         └──────┬─────┘
                                            └──── drift detected ──┘
```

Why it is better than a pipeline that runs `kubectl apply`:

| | Push (classic CI/CD) | Pull (GitOps) |
| --- | --- | --- |
| Who deploys | The pipeline, with cluster credentials | An agent inside the cluster |
| Manual changes | Persist until the next deploy | Reverted automatically (self-heal) |
| Rollback | Re-run an old pipeline | `git revert` |
| Source of truth | Pipeline plus cluster | Git |

The two common tools are Argo CD (used here, has a UI) and Flux. The usual flow: CI builds an image and commits the new tag into the config repo; Argo CD rolls it out. My final project's pipeline does exactly that in its last job.

## What this demo deploys

```
03-gitops/
├── app/                        # the folder Argo CD watches
│   ├── namespace.yaml          # session20-gitops
│   ├── deployment.yaml         # vansh-gitops-app, 2 replicas of http-echo
│   └── service.yaml            # ClusterIP
├── argocd-application.yaml     # tells Argo CD what to watch and where to deploy
├── screenshots/
└── README.md
```

The Application object stays outside `app/` on purpose; if it were inside, Argo CD would try to manage its own definition.

| Field | Value |
| --- | --- |
| `repoURL` | `https://github.com/VanshChitransh/Devops-Ass-01.git` (this repository) |
| `path` | `session-20-monitoring-gitops/03-gitops/app` |
| `targetRevision` | `main` |
| Destination | namespace `session20-gitops`, same cluster |
| `automated.prune` | Objects deleted from Git are deleted from the cluster |
| `automated.selfHeal` | Manual cluster changes are reverted |
| `CreateNamespace=true` | Namespace created on first sync |

## Step by step

### 1. Cluster and Argo CD

I use the kind cluster `session20` that already has Argo CD installed from the class walkthrough.

```bash
kind get clusters
kubectl config use-context kind-session20
kubectl get pods -n argocd
```

![Cluster and Argo CD pods](screenshots/01-cluster-argocd.png)

If Argo CD is not installed:

```bash
kind create cluster --name session20
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 2. Push the manifests

Argo CD reads from GitHub, so `app/` has to be on `main` first.

```bash
git add session-20-monitoring-gitops
git commit -m "Add Session 20 monitoring and GitOps demo"
git push
```

### 3. Register the Application

```bash
kubectl apply -f session-20-monitoring-gitops/03-gitops/argocd-application.yaml
kubectl get applications -n argocd -w
```

![Application registered](screenshots/02-register-app.png)

Until the push, Argo CD shows no sync status because the path does not exist on GitHub yet. After the push it reports `Synced` and `Healthy` within a minute.

### 4. What Argo CD created

```bash
kubectl get all -n session20-gitops
```

Namespace, Deployment with two Pods, and Service, none of them applied by hand.

### 5. The UI

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open https://localhost:8080, accept the self-signed certificate, log in as `admin`. The application tile shows the resource tree: Application, Deployment, ReplicaSet, two Pods, Service.

### 6. Change the system through Git

```bash
sed -i '' 's/replicas: 2/replicas: 3/' session-20-monitoring-gitops/03-gitops/app/deployment.yaml
git commit -am "Scale the GitOps app to three replicas"
git push
kubectl annotate application vansh-gitops-app -n argocd argocd.argoproj.io/refresh=hard --overwrite   # skip the 3-minute poll
kubectl get deployment vansh-gitops-app -n session20-gitops -w
```

The Deployment goes to `3/3` with no `kubectl apply` anywhere.

### 7. Self-healing

```bash
kubectl scale deployment vansh-gitops-app -n session20-gitops --replicas=1
kubectl get pods -n session20-gitops -w
```

Within moments the replicas return to 3. Git says 3, so Argo CD treats my manual scale as drift and corrects it. The only way to change the system is through Git.

### 8. Rollback with Git

```bash
git revert --no-edit HEAD
git push
kubectl annotate application vansh-gitops-app -n argocd argocd.argoproj.io/refresh=hard --overwrite
kubectl get deployment vansh-gitops-app -n session20-gitops -w
```

Back to 2 replicas. A rollback is just another commit, with a full audit trail.

### 9. Clean up

```bash
kubectl delete -f session-20-monitoring-gitops/03-gitops/argocd-application.yaml
kubectl get all -n session20-gitops
```

The finalizer on the Application removes everything it deployed.

## Status

Step 1 and the registration in step 3 are captured. Steps 4 to 9 need the manifests on GitHub, so their captures are added right after the push.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| Application shows no status or a path error | Files not pushed yet, or wrong `path` / `repoURL`. `kubectl describe application vansh-gitops-app -n argocd` |
| `OutOfSync` that never syncs | `syncPolicy.automated` missing; sync from the UI or add it |
| Git change not visible | Argo CD polls every 3 minutes; use the `refresh=hard` annotation |
| Manual change not reverted | `selfHeal: true` is required |
| `argocd-redis` shows `Unknown` after a cluster restart | Let it restart; `kubectl rollout restart deployment argocd-redis -n argocd` if it stays stuck |

## Viva answers, in my own words

1. **Monitoring vs observability**: known signals and alerts, versus enough data to explain the unknown.
2. **Metrics vs logs vs traces**: numbers over time, single events, the path of one request.
3. **Prometheus** pulls and stores metrics and evaluates alert rules.
4. **Grafana** draws what Prometheus (and others) hold.
5. **GitOps** means Git holds the desired state and an in-cluster agent makes the cluster match it.
6. **Git is the source of truth** because every change to the system goes through a commit, so the repository is always the authoritative description.
7. **Argo CD** compares Git with the cluster and syncs the difference.
8. **Desired state** is what the files say should exist.
9. **Actual state** is what the API server says exists right now.
10. **Reconciliation** is the loop that compares the two and acts on the difference.
11. **Self-healing** means a manual change to the cluster is detected as drift and undone.
12. **Replicas 2 to 3 in Git**: Argo CD sees the diff, marks the app OutOfSync, auto-syncs, and the Deployment scales to three Pods.
