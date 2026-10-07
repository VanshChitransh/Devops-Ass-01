# TicketHub: DevOps capstone (Session 21)

**Name:** Vansh Chitransh
**Course:** SST DevOps & Cloud [SWE]
**Repository:** https://github.com/VanshChitransh/Devops-Ass-01

TicketHub is a small helpdesk ticketing application: people raise tickets, support staff triage, assign and resolve them. The application itself is deliberately modest. The point of this project is the road from my laptop to a monitored Kubernetes deployment, with tests, security scans, a container registry, infrastructure as code, Helm, Ingress, autoscaling and dashboards along the way.

```
developer laptop
   │  git push
   ▼
GitHub Actions ── pytest ── vite build ── Bandit ── pip-audit / npm audit ── Gitleaks
   │                                                                      │
   ▼                                                                      ▼
docker build (backend, frontend, tagged with the commit SHA) ── Trivy ── security gate
   │
   ▼
GHCR  ──►  kind cluster inside the runner: helm upgrade --install + smoke test
   │
   ▼
values-gitops.yaml gets the new SHA  ──►  Argo CD syncs the real cluster
                                                   │
                     Terraform: VPC + EKS on AWS   │   kind on my Mac (this submission)
                                                   ▼
                    Ingress ──► frontend (React + nginx) ──► backend (FastAPI) ──► PostgreSQL
                                        HPA on the backend, Prometheus + Grafana watching /metrics
```

## Repository layout

```
final-devops-project/
├── application/
│   ├── backend/            # FastAPI, SQLAlchemy, Alembic, pytest (10 tests), Dockerfile (non-root)
│   └── frontend/           # React + Vite dashboard, nginx.conf.template, multi-stage Dockerfile (non-root)
├── docker/docker-compose.yml   # postgres + migrate + backend + frontend
├── kubernetes/namespace.yaml
├── helm/tickethub/         # chart: backend, frontend, postgres, configmap, secret, ingress, hpa, servicemonitor
│   ├── values.yaml         # defaults (GHCR images)
│   ├── values-local.yaml   # kind/minikube: local images, ingress on tickethub.local
│   └── values-gitops.yaml  # watched by Argo CD; CI rewrites the image tags
├── monitoring/             # kube-prometheus-stack values, PrometheusRule, Grafana dashboard ConfigMap
├── terraform/              # AWS VPC + EKS (terraform-aws-modules), tfvars.example only
├── gitops/argocd-application.yaml
├── troubleshooting/        # broken-image.yaml, broken-service.yaml
├── scripts/                # seed.sh, load-test.sh
├── screenshots/
└── README.md
.github/workflows/final-project-ci-cd.yml   # at the repository root, as GitHub requires
```

---

## M1. The application

### Backend (FastAPI + PostgreSQL)

| Method | Path | Does |
| --- | --- | --- |
| GET | `/health` | Liveness: the process answers |
| GET | `/ready` | Readiness: runs `SELECT 1` against PostgreSQL, 503 if it fails |
| GET | `/metrics` | Prometheus metrics (requests, latency histogram, in-flight) |
| GET | `/api/tickets` | List, with `?status=` and `?priority=` filters |
| GET | `/api/tickets/stats` | Totals by status and priority, open urgent, unassigned |
| GET | `/api/tickets/{id}` | One ticket, 404 if missing |
| POST | `/api/tickets` | Create (201); priority and status are validated enums |
| PUT | `/api/tickets/{id}` | Partial update |
| DELETE | `/api/tickets/{id}` | Delete (204) |

Swagger UI is at `/docs`. The `tickets` table is created by the Alembic migration `0001_create_tickets.py`; `app/migrate.py` runs the migration with a PostgreSQL advisory lock so that several backend replicas starting together cannot race.

### Frontend (React + Vite, served by nginx)

A dashboard with a sidebar, KPI cards (total, open, in progress, urgent unresolved, unassigned), a filterable ticket table with priority and status badges, one-click assign and advance actions, a create-ticket modal, an activity feed, loading and error states, and a responsive layout down to phone width. The browser only ever talks to `/api/...` on its own origin; nginx proxies that to the backend, so the frontend never needs to know the backend's address.

![Dashboard in the browser](screenshots/01-app-dashboard.png)

![Phone layout](screenshots/01b-app-mobile.png)

![Swagger UI](screenshots/02-api-docs.png)

---

## M2. Tests

```bash
cd application/backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v --cov=app --cov-report=term-missing
```

Ten tests across seven endpoints, run against a throw-away SQLite file that `tests/conftest.py` sets up and tears down for every test. Never the real database. `pytest.ini` puts the project root on the import path and points at `tests/`.

![pytest: 10 passed](screenshots/t-01-pytest.png)

---

## M3. Git and GitHub

Public repository, one folder per session, meaningful commit messages, and `.gitignore` files that keep `.venv/`, `node_modules/`, `dist/`, `.terraform/`, state files, `.env` and the test SQLite file out. The only credentials in the tree are the classroom PostgreSQL password in `values.yaml`, which the chart lets you override with `--set postgres.password=...`.

---

## M4. Docker and Compose

- `backend/Dockerfile`: `python:3.12-slim`, dependencies first for layer caching, runs as user `api` (uid 10001), starts uvicorn.
- `frontend/Dockerfile`: stage one builds the bundle with Node 22, stage two is `nginxinc/nginx-unprivileged` (uid 101, port 8080) with only `dist/` and the nginx template.
- `docker/docker-compose.yml`: `postgres` with a health check, a one-shot `migrate` service, `backend` (waits for the migration to finish, has its own health check on `/ready`), `frontend` (waits for a healthy backend). Port 3000 for the UI, 8000 for the API.

```bash
docker compose -f docker/docker-compose.yml up --build -d
docker compose -f docker/docker-compose.yml ps
```

![compose up and ps](screenshots/t-03-compose-up.png)

![API smoke test, through the backend and through the frontend proxy](screenshots/t-04-api-smoke.png)

![The tickets table and alembic_version in PostgreSQL](screenshots/t-06-db.png)

---

## M5. CI/CD with GitHub Actions

`.github/workflows/final-project-ci-cd.yml` runs on every push to `main` that touches this folder, on pull requests, and on demand.

```
backend-test ─┐
frontend-build┤
sast (bandit) ├─► build-images (backend, frontend; tag = commit SHA) ─► image-scan (Trivy x2) ─► security-gate
sca           │                                                                                        │
secret-scan  ─┘                                                              push-images (GHCR) ◄──────┘
                                                                                     │
                                                      deploy-test (kind in the runner, helm upgrade --install, smoke test)
                                                                                     │
                                                      gitops-update (writes the SHA into values-gitops.yaml, [skip ci])
```

- A failing test stops everything: `build-images` needs all five checks.
- Images are built once, saved as artifacts, and the exact same tar is scanned, pushed and deployed. Tags are the commit SHA, never `latest`.
- Push and deploy run only on `main`, never on pull requests.
- The last job commits the new tag to `values-gitops.yaml`, which is what Argo CD watches. `[skip ci]` and a paths exclusion keep that commit from re-triggering the pipeline.

Images land at `ghcr.io/vanshchitransh/devops-ass-01/tickethub-backend:<sha>` and `.../tickethub-frontend:<sha>`.

---

## M6. Security scanning

Trivy scans both images in the pipeline with `severity: HIGH,CRITICAL`, `ignore-unfixed: true` and `exit-code: 1`, so any fixable high or critical CVE in the Debian or Alpine base, the Python packages or the nginx layer fails the run before anything is pushed. Bandit, pip-audit, `npm audit --audit-level=high` and Gitleaks cover the source, the dependencies and committed secrets. What Trivy scans is the filesystem of the finished image, OS packages plus language packages; a clean result means no known, patched vulnerability of that severity is present in that image at that moment, not that the application is bug-free.

Locally the same checks ran on Session 17's image; see that folder for the Bandit, pip-audit, Gitleaks and Trivy output. The frontend image is scanned the same way in the pipeline.

---

## M7. Terraform: VPC and EKS

`terraform/` describes the production home for TicketHub on AWS:

- `terraform-aws-modules/vpc` 6.x: VPC `10.30.0.0/16`, two public and two private subnets across two Availability Zones, one NAT gateway, the subnet tags EKS needs for load balancers.
- `terraform-aws-modules/eks` 21.x: an EKS control plane with public endpoint access, CoreDNS, kube-proxy and VPC CNI add-ons, and one managed node group of `t3.medium` nodes (desired 2, min 1, max 3) in the private subnets.
- `terraform.tfvars.example` shows the inputs; credentials come from `aws configure`, never from the files.

```bash
cd terraform
terraform init
terraform validate
terraform plan        # needs AWS credentials
terraform apply
aws eks update-kubeconfig --region ap-south-1 --name tickethub-dev-eks
terraform destroy     # when finished, EKS and the NAT gateway are billed by the hour
```

`init` downloaded the modules and providers and `validate` passed. `plan`, `apply` and `destroy` need an AWS account, which I do not have configured on this laptop, so the Kubernetes parts of this submission run on a local kind cluster instead; the chart and the pipeline do not change between the two.

![terraform init, validate, providers](screenshots/t-17-terraform.png)

---

## M8. Kubernetes and Helm

```bash
kind load docker-image tickethub-backend:local tickethub-frontend:local --name session20
kubectl apply -f kubernetes/namespace.yaml
helm upgrade --install tickethub helm/tickethub -n tickethub -f helm/tickethub/values-local.yaml --wait
kubectl get pods,svc,ingress,hpa -n tickethub
helm list -n tickethub
```

What the chart creates: a ConfigMap, a Secret for the database password, a PVC-backed PostgreSQL Deployment and Service, the backend Deployment (two replicas, an init container that runs the migration, readiness on `/ready`, liveness on `/health`, non-root, capabilities dropped) and Service, the frontend Deployment (two replicas) and Service, an Ingress that routes `/api`, `/docs` and `/openapi.json` to the backend and everything else to the frontend, a HorizontalPodAutoscaler on the backend, and optionally a ServiceMonitor.

![helm install and helm list](screenshots/t-08-helm-install.png)

![Pods, Services, Ingress, HPA, PVC](screenshots/t-09-k8s-objects.png)

Ingress: the kind cluster was created without a host port mapping and I have no sudo for `/etc/hosts`, so I reached the ingress-nginx controller through a `kubectl port-forward` on 8088 and pointed `tickethub.local` at it with `curl --resolve`. Seeding five tickets through the Ingress and listing them back:

![Through the Ingress host](screenshots/t-10-ingress-access.png)

![The app served through the Ingress hostname](screenshots/03-ingress-browser.png)

### Autoscaling

`scripts/load-test.sh 150 16` ran sixteen parallel clients against the API for two and a half minutes while `kubectl get hpa -w` watched. CPU went from 5 percent of the request to 191, then 497 percent; the HPA took the backend from 2 to 4 to 5 replicas (the maximum) within a minute and `kubectl top` shows the work spread across all five.

![HPA scaling the backend 2 to 5](screenshots/t-11-hpa.png)

---

## M9. Observability

The backend exposes Prometheus metrics at `/metrics` through `prometheus-fastapi-instrumentator`: `http_requests_total` by handler, method and status class, a latency histogram, and in-flight requests.

![/metrics output](screenshots/t-05-metrics.png)

In the cluster, `monitoring/prometheus-values.yaml` installs `kube-prometheus-stack` (Prometheus, Grafana, node-exporter, kube-state-metrics; Alertmanager off), the chart's ServiceMonitor registers the backend Service as a scrape target, `monitoring/alert-rules.yaml` adds three PrometheusRules (backend down, error rate above 5 percent, p95 above 500 ms), and `monitoring/grafana-dashboard.yaml` is a ConfigMap that Grafana's sidecar turns into the "TicketHub by Vansh" dashboard: targets up, requests per second, error rate, replica count, latency percentiles, requests by status, CPU per pod.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f monitoring/prometheus-values.yaml
helm upgrade tickethub helm/tickethub -n tickethub -f helm/tickethub/values-local.yaml --set monitoring.serviceMonitor.enabled=true --reuse-values
kubectl apply -f monitoring/alert-rules.yaml -f monitoring/grafana-dashboard.yaml
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9091:9090
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80      # admin / admin
```

![Monitoring stack installed](screenshots/t-14-monitoring-install.png)

![ServiceMonitor, rules and dashboard applied](screenshots/t-15-monitoring-wire.png)

![Prometheus targets and rule states from the API](screenshots/t-16-prometheus-targets.png)

![Prometheus targets page](screenshots/05-prometheus-targets.png)

![Grafana dashboard](screenshots/06-grafana-dashboard.png)

---

## Troubleshooting lab

Two things that go wrong in real clusters, reproduced on purpose and fixed with the Session 14 ladder (get, describe, events, logs, fix, verify).

**Broken image.** `troubleshooting/broken-image.yaml` points a Deployment at `tickethub-backend:does-not-exist`. The Pod sits in `ImagePullBackOff`; `describe` and the events name the tag. `kubectl set image` to a real tag and the Pod is Running.

![Broken image lab](screenshots/t-12-lab-broken-image.png)

**Broken Service.** `troubleshooting/broken-service.yaml` selects `app.kubernetes.io/component=backend-typo`. The Service exists but its endpoints are `<none>` while five backend Pods are Running next to it. Comparing `--show-labels` with the selector finds the typo; patching the selector fills the endpoints immediately.

![Broken service lab](screenshots/t-13-lab-broken-service.png)

---

## GitOps

`gitops/argocd-application.yaml` tells Argo CD to deploy `helm/tickethub` with `values-gitops.yaml` into the `tickethub` namespace, automated, with prune and self-heal. Combined with the pipeline's last job, the flow is: push code, pipeline tests, scans, builds, pushes and smoke-tests, pipeline commits the new SHA, Argo CD rolls it out. Nobody runs `kubectl apply` for a release.

---

## Status of this submission

| Module | Done here | Needs |
| --- | --- | --- |
| M1 application, M2 tests, M4 Docker | Yes, with screenshots | |
| M3 Git | Repository and ignores in place | The push of this folder |
| M5 CI/CD, M6 Trivy in CI | Workflow written and validated against the same steps locally | The first push to `main` for a run URL and the GHCR package page |
| M7 Terraform | Code, `init`, `validate` | AWS credentials for `plan`, `apply`, console screenshot, `destroy` |
| M8 Kubernetes and Helm | Yes, on kind, with screenshots | |
| M9 Prometheus and Grafana | Yes, on kind, with screenshots | |
| M10 README and demo | This file | The live demo |

Everything marked "Needs" is a credential or a push I did not want to perform without the account owner; nothing in the code changes for it.
