# Session 17: CI/CD with DevSecOps gates

**Name:** Vansh Chitransh
**Course:** SST DevOps & Cloud [SWE]
**Session:** 17

A small Flask API with a pipeline that scans the source code, the dependencies, the repository files and the Docker image, and only publishes and deploys the image if every check is green.

## Where things live

```
Devops_Ass1/                               <- repository root
├── .github/workflows/
│   └── session-17-devsecops.yml           # the pipeline (nine jobs)
└── session-17-devsecops/
    ├── app/                               # Flask app: app.py, templates/, static/
    ├── tests/test_app.py                  # 8 pytest tests
    ├── k8s/deployment.yaml                # 2 replicas, probes, non-root, read-only filesystem, limits
    ├── k8s/service.yaml                   # NodePort 30017
    ├── Dockerfile                         # python:3.12-slim, gunicorn, user appuser (uid 10001)
    ├── requirements.txt                   # Flask, gunicorn
    ├── requirements-dev.txt               # plus pytest, pytest-cov, bandit, pip-audit
    ├── pytest.ini
    ├── screenshots/
    └── README.md
```

## The app

| Endpoint | Does |
| --- | --- |
| `GET /` | A one-page description of the service |
| `GET /health` | `{"status": "healthy"}`, used by the Kubernetes probes |
| `GET /api/status` | App name, version, uptime, owner |
| `POST /api/add` | Adds `number1` and `number2`, 400 on bad input |
| `POST /api/multiply` | Multiplies them |

It is deliberately tiny. The pipeline around it is the point.

## What each check catches

| Check | Looks at | Tool | Blocks when |
| --- | --- | --- | --- |
| Unit tests | Does my code do what I think | pytest with coverage | Any test fails |
| SAST | My own source, without running it | Bandit, plus CodeQL for the Security tab | Bandit finds medium or high severity |
| SCA | Third-party packages I depend on | pip-audit | A dependency has a known CVE |
| Secret scan | Files that look like keys, tokens, passwords | Gitleaks | Anything matches |
| Image scan | The built image: OS packages and Python packages | Trivy | A fixable HIGH or CRITICAL CVE |
| Gate | All of the above | `needs:` in the workflow | Any required job is not green |

```
push
 │
 ├── test ──────┐
 ├── sast ──────┤
 ├── sca ───────┼──► docker-build ──► image-scan ──► security-gate ──► push (GHCR) ──► deploy (kind)
 └── secret ────┘        (built once, saved as artifact: the scanned image is the shipped image)
```

Design decisions: the image is built exactly once and passed between jobs as a tar artifact; every scanner exits non-zero on findings so it can really block; pushing and deploying only happen on `main`, never on pull requests; the deploy job creates a throw-away kind cluster inside the runner because a GitHub runner cannot reach my laptop's cluster.

## Part 1: run the app and tests locally

```bash
cd session-17-devsecops
python3.11 -m venv ~/.venvs/session17
source ~/.venvs/session17/bin/activate
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing
```

8 tests pass with 93 percent coverage. (The venv lives outside the project on purpose so the secret scan does not crawl thousands of library files.)

![8 tests passing with coverage](screenshots/01-tests.png)

```bash
python app/app.py
curl http://localhost:5001/health
curl http://localhost:5001/api/status
curl -X POST http://localhost:5001/api/add -H "Content-Type: application/json" -d '{"number1": 10, "number2": 20}'
```

![App answering curl](screenshots/02-app-run.png)

## Part 2: run every scanner locally first

### SAST: Bandit

```bash
bandit -r app -ll
```

No issues. One thing I avoided on purpose: binding Flask's dev server to `0.0.0.0` in code, which Bandit flags as B104. The container binds through gunicorn instead.

![Bandit clean](screenshots/03-bandit.png)

### SCA: pip-audit, and a real finding

```bash
pip-audit -r requirements.txt
```

The first run was not clean: `Flask 3.1.2` has a published advisory, `PYSEC-2026-2151`, fixed in 3.1.3.

![pip-audit finds PYSEC-2026-2151 in Flask 3.1.2](screenshots/04-pip-audit-finding.png)

The fix is a one-line pin change, after which pip-audit reports nothing. This is exactly what SCA is for: my own code had no bug, but the library underneath it did.

![Flask bumped to 3.1.3, pip-audit clean](screenshots/04-pip-audit.png)

### Secret scan: Gitleaks

```bash
gitleaks detect --no-git --source . --redact --verbose
```

![Gitleaks: no leaks found](screenshots/05-gitleaks.png)

### Image scan: Trivy

```bash
docker build -t session17-python:local .
docker run --rm session17-python:local id
trivy image --severity HIGH,CRITICAL --ignore-unfixed session17-python:local
```

The container runs as `appuser` (uid 10001). Trivy scanned the Debian 13 base and every Python package and found no fixable HIGH or CRITICAL vulnerability.

![Image built, runs as uid 10001, Trivy clean](screenshots/06-trivy.png)

## Part 3: the Kubernetes manifests, on minikube

The Deployment has an `__IMAGE__` placeholder that the pipeline fills in. Locally I pointed it at the image I just built.

```bash
minikube image load session17-python:local
kubectl create namespace s17-demo
sed "s|__IMAGE__|session17-python:local|" k8s/deployment.yaml | kubectl apply -n s17-demo -f -
kubectl apply -n s17-demo -f k8s/service.yaml
kubectl rollout status deployment/session17-python -n s17-demo
kubectl get pods,svc -n s17-demo
```

Two pods Running, a NodePort Service, and the pod security context confirms `runAsNonRoot` with uid 10001. The container also has a read-only root filesystem and all capabilities dropped.

![Two pods and the service](screenshots/07-k8s-deploy.png)

```bash
kubectl port-forward -n s17-demo svc/session17-python 5051:80
curl http://localhost:5051/health
kubectl delete namespace s17-demo
```

![Health check through the Service](screenshots/08-k8s-health.png)

## Part 4: push and watch the pipeline

```bash
git add .github/workflows/session-17-devsecops.yml session-17-devsecops
git commit -m "Add Session 17 DevSecOps pipeline"
git push
gh run watch
```

Expected: the four checks in parallel, then Docker Build, Image Scan, Security Gate, Push and Deploy, all green; the image at `ghcr.io/vanshchitransh/devops-ass-01/session17-python:<commit sha>`; CodeQL results under **Security > Code scanning**; and the deploy job's smoke test printing the `/health` and `/api/status` responses from inside the kind cluster.

## Part 5: proving the gates block

Each demo lives on its own branch and pull request, so `main` stays clean and nothing is published. After each one, close the PR and delete the branch.

| Demo | Change | Expected result |
| --- | --- | --- |
| Secret leak | Add `app/leaked_config.py` with a random fake `API_KEY` generated on the spot | Secret Scan fails, every later job skipped |
| Vulnerable dependency | Pin `Flask==2.2.4` | SCA fails; pip-audit names the CVEs and the fixed versions |
| Unsafe code | Add a function that calls `eval()` | SAST fails on Bandit B307 |
| Old base image | `FROM python:3.9-slim` | Image Scan fails on HIGH and CRITICAL findings in old Debian packages; the gate stays closed |

```bash
git switch -c demo/secret-leak
printf 'API_KEY = "%s"\n' "$(openssl rand -base64 36 | tr -d '/+=\n' | cut -c1-32)" > session-17-devsecops/app/leaked_config.py
git add session-17-devsecops/app/leaked_config.py && git commit -m "Demo: commit a fake API key"
git push -u origin demo/secret-leak
gh pr create --fill --base main && gh pr checks --watch
gh pr close demo/secret-leak --delete-branch && git switch main
```

The other three follow the same pattern with the change named in the table.

## What I learned

- SAST, SCA, secret scanning and image scanning each find a different class of problem. pip-audit found a real one in this project while the code itself was clean.
- A gate is nothing more than `needs:` plus tools that exit non-zero. A scanner that only prints is not a control.
- Build once, scan that artifact, ship that artifact. Rebuilding between jobs means the scanned image is not the deployed image.
- `--ignore-unfixed` keeps the gate about things I can act on today.
- Non-root user, read-only filesystem, dropped capabilities, resource limits and probes make the Kubernetes side safer with a few lines of YAML.
- A secret that was committed once is in history forever; rotate it, do not just delete the file.

## Status

Parts 1 to 3 were run on my laptop and are in `screenshots/`. Parts 4 and 5 run on GitHub after the first push of this folder to `main`.
