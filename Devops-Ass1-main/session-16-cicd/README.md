# Session 16: CI/CD with GitHub Actions

**Name:** Vansh Chitransh
**Course:** SST DevOps & Cloud [SWE]
**Session:** 16

A small calculator program with a GitHub Actions pipeline that tests it, builds it, runs a basic security check, and delivers it as a Docker image to GitHub Container Registry.

## Where things live

```
Devops_Ass1/                               <- repository root
├── .github/workflows/
│   └── session-16-ci-cd.yml               # the pipeline; GitHub only reads workflows from the root
└── session-16-cicd/
    ├── app/calculator.py                  # the application (add, subtract, multiply, divide, power, REPL)
    ├── tests/test_calculator.py           # 7 pytest tests
    ├── build.sh                           # produces build/ with the app and build-info.txt
    ├── Dockerfile                         # image used by the deliver job (non-root user)
    ├── requirements.txt                   # pytest
    ├── pytest.ini                         # puts the project root on sys.path
    ├── screenshots/
    └── README.md
```

Because the project sits in a subfolder, the workflow uses a `paths` filter so it only runs when this folder or the workflow changes, and `defaults.run.working-directory: session-16-cicd` so every `run` step starts in the right place.

## The ideas

### CI versus CD

| | Continuous Integration | Continuous Delivery | Continuous Deployment |
| --- | --- | --- | --- |
| Goal | Merge small changes often and catch breakage immediately | Always have a build that could be released | Release every good build automatically |
| Does | Build, test, check | Package and publish an artifact or image | Push to production |
| Human approval | None | Before release | None |
| Here | `test`, `build`, `security-check` | `deliver` publishes an image | Not used |

### GitHub Actions vocabulary

| Term | Meaning | In this pipeline |
| --- | --- | --- |
| Workflow | A YAML file describing an automated process | `session-16-ci-cd.yml` |
| Event | What triggers it | `push` and `pull_request` on `main`, `workflow_dispatch` |
| Job | A group of steps on one runner | `test`, `build`, `security-check`, `deliver` |
| Step | One command (`run`) or reusable action (`uses`) | `pytest -v`, `actions/checkout@v4` |
| Runner | The fresh machine a job runs on | `ubuntu-latest` |
| Secret | Encrypted value hidden from logs | `DEMO_SECRET`, the automatic `GITHUB_TOKEN` |
| Artifact | Files kept from a run for download | `calculator-build` |

### Pipeline shape

```
git push
   │
   ▼
 test (pytest -v)
   │
   ├──────────────┐
   ▼              ▼
 build        security-check
 (build.sh,   (no .env/.pem/.key files,
  artifact)    DEMO_SECRET present?)
   │              │
   └──────┬───────┘
          ▼
       deliver   (main branch only: build image, push to GHCR)
```

`build` and `security-check` both declare `needs: test`, so they run in parallel after the tests and never run at all if a test fails. `deliver` needs both, and its `if:` condition skips it on pull requests and on any branch other than `main`.

## Part 1: run it locally

```bash
cd session-16-cicd
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```

Seven tests, all green. The first run on my machine failed with `ModuleNotFoundError: No module named 'app'` because pytest did not have the project root on its import path; adding `pythonpath = .` to `pytest.ini` fixed it, and that is now committed so the runner sees the same thing.

![pytest -v: 7 passed](screenshots/01-tests.png)

```bash
chmod +x build.sh
./build.sh
cat build/build-info.txt
```

The build script copies the app into `build/` and writes a small manifest with the time, the builder, the commit and the Python version. The same script runs on the GitHub runner, where `GITHUB_SHA` and `GITHUB_ACTOR` fill those fields.

![build.sh and build-info.txt](screenshots/02-build.png)

```bash
python app/calculator.py
```

I fed it `10 + 5`, `2 * 8`, `2 ^ 10` and `q` through a pipe so the whole session fits in one capture.

![Calculator running](screenshots/03-run.png)

## Part 2: the Docker image

```bash
docker build -t session16-calculator .
printf "7 - 2\nq\n" | docker run -i --rm session16-calculator
docker run --rm session16-calculator id
docker images session16-calculator
```

The container runs as the `calc` user (uid 10001), not root, and the image is about 44 MB of content on top of `python:3.12-slim`.

![Docker image built and running](screenshots/04-docker.png)

## Part 3: the secret

The `security-check` job reads a repository secret called `DEMO_SECRET`. It never prints the value, only whether it is set and how long it is. To add it:

```bash
gh secret set DEMO_SECRET --body "hello-github-actions"
gh secret list
```

or in the browser under **Settings > Secrets and variables > Actions**. Once saved, GitHub never shows the value again, and masks it as `***` if it ever appears in a log.

## Part 4: push and watch

```bash
git add .github/workflows/session-16-ci-cd.yml session-16-cicd
git commit -m "Add Session 16 CI/CD pipeline"
git push
gh run watch
```

Expected run: `test` first, then `build` and `security-check` side by side, then `deliver`. The run summary lists the `calculator-build` artifact, which can be downloaded with:

```bash
gh run download --name calculator-build --dir downloaded-build
cat downloaded-build/build-info.txt
```

The delivered image lands at `ghcr.io/vanshchitransh/devops-ass-01/session16-calculator`, tagged both `latest` and `sha-<commit>`:

```bash
docker pull ghcr.io/vanshchitransh/devops-ass-01/session16-calculator:latest
docker run -it --rm ghcr.io/vanshchitransh/devops-ass-01/session16-calculator:latest
```

If the pull is denied, the package visibility has to be switched to public in the package settings.

The GitHub-side screenshots (Actions tab, job logs, artifact, package page) are added after the workflow has run on GitHub; see the status note at the end of this file.

## Part 5: make it fail on purpose

```bash
sed -i '' 's/return a + b$/return a + b + 1/' session-16-cicd/app/calculator.py
git commit -am "Break add on purpose to see CI fail"
git push
gh run watch
```

`test_add` fails (`assert 16 == 15`), so `test` goes red and `build`, `security-check` and `deliver` are all skipped. Nothing broken gets delivered, which is the whole point of CI. Then:

```bash
git revert --no-edit HEAD
git push
```

and the pipeline is green again.

## Part 6: the session's student tasks

| Task | Where |
| --- | --- |
| Add `def power(a, b): return a ** b` | `app/calculator.py` |
| Add `def test_power(): assert power(2, 3) == 8` | `tests/test_calculator.py` |
| Run pytest, all green | Part 1, 7 passed |
| Push to GitHub and check the Test and Build jobs | Part 4 |
| Download `calculator-build` and inspect it | Part 4 |

## What I learned

- CI is the automatic "does this still work" question on every change; CD is "ship the thing that passed".
- Jobs run in parallel unless `needs` says otherwise, and a failed job skips everything downstream.
- Each job is a fresh runner, so each one checks out the code again.
- Secrets are encrypted and masked; `GITHUB_TOKEN` is created per run and `packages: write` is what lets it push to GHCR.
- Artifacts are the way to keep build output from a run; images go to a registry.
- Workflows must live in `.github/workflows/` at the repository root, even for a project in a subfolder.

## Status

Everything in Parts 1 and 2 was run on my laptop and is captured in `screenshots/`. Parts 3 to 5 need the workflow to run on GitHub, which happens on the first push of this folder to `main`.
