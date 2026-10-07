# Monitoring demo: Prometheus, Grafana and alerts

**Name:** Vansh Chitransh
**Session:** 20, Task 1

A small Flask service watched by Prometheus and Grafana. The demo shows **metrics, logs, alerts, CPU, memory and application health** in three states: healthy, overloaded, and down. Everything ran with Docker Compose on my MacBook; every screenshot is from that run.

## What monitoring means here

Collect numbers about the system, draw them, and raise an alert when a rule is broken. The question it answers is *is the system healthy right now?*

| Signal | Where it comes from in this demo |
| --- | --- |
| Metrics (request count, errors, latency) | The app's `/metrics` endpoint |
| Logs (one line per request, `ERROR` lines on failures) | The app's stdout, via `docker compose logs` |
| Alerts | Five rules in `prometheus/alerts.yml` |
| CPU | `process_cpu_seconds_total` (app) and `node_cpu_seconds_total` (host) |
| Memory | `process_resident_memory_bytes` (app) and `node_memory_*` (host) |
| Application health | The `up` metric: 1 when Prometheus can scrape the app, 0 when it cannot |

## Architecture

```
            scrape /metrics every 5s
   ┌───────────────────────────────────────────┐
   │                                           │
┌──┴─────────┐  ┌───────────────┐  ┌───────────▼──────────┐  PromQL   ┌─────────────┐
│ demo app   │  │ node-exporter │  │ Prometheus  :9090    │◄──────────│ Grafana     │
│ Flask :8000│  │ host CPU/mem  │  │ stores time series   │           │ :3000       │
└────────────┘  └──────▲────────┘  │ evaluates alert rules│           │ 12 panels   │
                       └───────────┤                      │           └─────────────┘
                                   └──────────────────────┘
```

Prometheus **pulls**: every five seconds it fetches `/metrics` from each target. Grafana never stores anything; it asks Prometheus and draws the answer.

## Files

```
01-monitoring/
├── docker-compose.yml                       # app, node-exporter, Prometheus, Grafana
├── load.sh                                  # normal | errors | slow | cpu traffic for N seconds
├── app/app.py, requirements.txt, Dockerfile # Flask app with a /metrics endpoint, non-root image
├── prometheus/prometheus.yml                # three scrape jobs, 5s interval, rule file
├── prometheus/alerts.yml                    # five alert rules
├── grafana/provisioning/datasources/        # Prometheus data source, created automatically
├── grafana/provisioning/dashboards/         # dashboard provider
├── grafana/dashboards/app-monitoring.json   # the 12-panel dashboard
└── screenshots/
```

## The app

| Endpoint | Behaviour | Used to show |
| --- | --- | --- |
| `/` | JSON greeting | Normal traffic |
| `/health` | `UP` | Health check |
| `/error` | HTTP 500 and an `ERROR` log line | Error rate, error logs |
| `/slow` | Sleeps 1.2 to 2 seconds | Latency |
| `/cpu` | Busy-loops for one second | CPU |
| `/metrics` | Prometheus text format | Everything above |

Two custom metrics: `http_requests_total` (counter, labelled by method, endpoint and status) and `http_request_duration_seconds` (histogram). The Prometheus client library adds the process CPU and memory metrics on its own.

## Alert rules

| Alert | Fires when | For |
| --- | --- | --- |
| `AppDown` | `up{job="app"} == 0` | 15s |
| `HighErrorRate` | 5xx share of requests over the last minute above 20 percent | 30s |
| `HighLatency` | p95 response time above 1 second | 30s |
| `HostHighCPU` | Host CPU above 80 percent | 1m |
| `HostHighMemory` | Host memory above 85 percent | 1m |

The `for` duration is what stops a single bad scrape from paging anyone: the rule goes inactive, then pending while the condition holds, then firing once the duration has passed. The values are short here so the demo turns around in a minute.

## Running it

```bash
cd session-20-monitoring-gitops/01-monitoring
docker compose up -d --build
docker compose ps
```

| Service | URL | Login |
| --- | --- | --- |
| App | http://localhost:8000 | none |
| Prometheus | http://localhost:9090 | none |
| Grafana | http://localhost:3000 | `admin` / `admin` (anonymous viewer access is also on, classroom only) |

The app is on 8000 because macOS AirPlay already uses 5000. One Docker Desktop detail: node-exporter cannot mount the Mac's root filesystem, so it reports the Linux VM that runs Docker rather than macOS itself; on a Linux host, add the `/:/host:ro,rslave` mount back.

![All four containers running](screenshots/10-compose-ps.png)

### 1. Every target is UP

Prometheus's targets page lists `app`, `node` and `prometheus`, all `UP`. This is application health from the monitor's point of view.

![Targets page](screenshots/01-targets.png)

### 2. Raw metrics and logs

```bash
curl -s localhost:8000/metrics | grep -E "^(http_requests_total|process_cpu_seconds_total|process_resident_memory_bytes)"
docker compose logs app --tail 10
docker compose logs app | grep ERROR
```

The metric lines are totals; the log lines are individual events. The counter says `/error` returned one 500; the log says who asked for it and when.

![Metrics from the app](screenshots/12-app-metrics.png)

![Logs with an ERROR line](screenshots/11-app-logs.png)

### 3. Traffic and PromQL

```bash
./load.sh normal 45
```

```promql
sum by (endpoint) (rate(http_requests_total[1m]))
```

`rate(...[1m])` turns an ever-growing counter into requests per second; `sum by (endpoint)` adds the series up per endpoint. Through the API the same query reported about 14 requests per second during the load.

![PromQL graph of requests per second by endpoint](screenshots/02-query-graph.png)

![Load, targets and rule states from the API](screenshots/13-load-promql.png)

### 4. Grafana while healthy

Dashboards > "Vansh Session 20 Application Monitoring", loaded automatically from `grafana/dashboards/`.

![Dashboard, healthy](screenshots/03-grafana-healthy.png)

| Panel | Query idea | Golden signal |
| --- | --- | --- |
| App status | `up{job="app"}` | Availability |
| Requests / sec | `sum(rate(http_requests_total[1m]))` | Traffic |
| Error rate | 5xx rate divided by all requests | Errors |
| p95 latency | `histogram_quantile(0.95, ...)` | Latency |
| App CPU, app memory | `process_cpu_seconds_total`, `process_resident_memory_bytes` | Saturation |
| Host CPU and memory | `node_cpu_seconds_total`, `node_memory_*` | Saturation |

### 5. No alerts firing

![Alerts page, all inactive](screenshots/04-alerts-inactive.png)

### 6. Cause trouble

```bash
./load.sh errors 100 &
./load.sh slow 100 &
./load.sh cpu 100 &
```

About 75 seconds later the error share was 63 percent and p95 latency 1.44 seconds, so `HighErrorRate` and `HighLatency` went pending and then firing. The logs filled with `ERROR Simulated failure on /error` lines.

![Alerts firing](screenshots/05-alerts-firing.png)

![Dashboard under load](screenshots/06-grafana-under-load.png)

![Rule states and the numbers behind them](screenshots/14-alerts-firing.png)

### 7. Stop the app

```bash
docker compose stop app
```

Forty seconds later `up{job="app"}` is 0, the status tile reads DOWN and `AppDown` fires. No request failed in the logs, because nothing was running to fail; that is exactly why the `up` metric exists.

![AppDown firing](screenshots/07-alert-app-down.png)

![Dashboard with the app down](screenshots/08-grafana-app-down.png)

![up metric and rule states](screenshots/15-app-down.png)

### 8. Bring it back

```bash
docker compose start app
./load.sh normal 45
```

Status back to UP and every rule back to inactive once its condition stopped being true.

![Dashboard after recovery](screenshots/09-grafana-recovered.png)

![Recovered](screenshots/16-recovered.png)

### Clean up

```bash
docker compose down -v
```

![Cleanup](screenshots/17-cleanup.png)

## Troubleshooting notes

| Problem | Cause and fix |
| --- | --- |
| node-exporter exits with "path / is mounted on / but it is not a shared or slave mount" | Docker Desktop on macOS. Remove the root mount (done in this compose file). |
| Port 5000 busy | macOS AirPlay. The app publishes 8000. |
| Grafana panels say "No data" | Send traffic first; `rate()` needs about a minute of samples. |
| A target shows DOWN | `docker compose ps`, then `docker compose logs <service>`. |

## What I learned

- Prometheus pulls metrics; the application only has to expose a text endpoint.
- A counter only goes up, so I always look at it through `rate()`. A histogram is what makes p95 and p99 possible, and the p95 line showed a problem the average would have hidden.
- Alerts need a `for` window, or a single slow request pages someone.
- Metrics say that something is wrong; logs say what happened. I needed both in step 6.
- `up` is the simplest and most important signal: it is the only one that notices a service that is not running at all.
