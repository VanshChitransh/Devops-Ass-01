# Observability: metrics, logs and traces

**Name:** Vansh Chitransh
**Session:** 20, Task 2

## Monitoring versus observability

| | Monitoring | Observability |
| --- | --- | --- |
| The question | "Is it healthy right now?" | "Why is it behaving like this?" |
| Starts from | Signals I chose in advance | Rich data I can slice for questions I did not plan |
| Output | Dashboards and alerts | The cause of a problem I have never seen before |
| Example | "p95 latency is above 1 second" | "p95 is high only for `/slow`, only since 13:08, because the thread pool is saturated" |

Monitoring is a subset of observability. The Session 20 demo in `01-monitoring` is monitoring: I decided up front to watch request rate, errors, latency, CPU and memory, and I wrote five alert rules. Observability is what I would need the day something breaks that none of those five rules anticipated.

## The three pillars

### Metrics: numbers over time

Counters, gauges and histograms with labels. Small, cheap, fast to query, ideal for dashboards and alerts.

```
http_requests_total{endpoint="/error", method="GET", status="500"}  312
```

They answer *how much, how often, how fast*. Their weakness is that they are summaries: a counter says errors went up, not which request failed or why.

### Logs: records of single events

One line per thing that happened, with a timestamp. The demo app writes one line per request and an `ERROR` line when `/error` is hit:

```
2026-10-07 13:08:46 ERROR Simulated failure on /error (requested by 192.168.65.1)
2026-10-07 13:08:46 INFO GET /error -> 500 in 0.000s
```

They answer *what exactly happened*. Their weakness is volume and cost at scale, and that a request crossing ten services leaves ten unrelated log files unless something ties them together.

### Traces: the path of one request

A trace is a tree of spans, one per step, each with a start time and a duration, across every service the request touched.

```
trace 7f3a: POST /checkout                       810 ms
 ├─ cart-service       load cart                  35 ms
 ├─ payment-service    charge card               640 ms   <-- here
 │   └─ bank-gateway   authorise                 600 ms
 └─ inventory-service  reserve items              55 ms
```

They answer *where did the time go, which service failed*. The cost is that every service must be instrumented, and traces are usually sampled.

### How I use the three together

```
metric  -> alert: error rate is 25%
trace   -> the failing spans are all in payment-service
log     -> payment-service: "connection pool exhausted"
```

| Pillar | Tells me | Cost |
| --- | --- | --- |
| Metrics | That something is wrong | Low |
| Traces | Where it is | Medium to high |
| Logs | Why it happened | High |

A trace ID stamped on every log line is what lets me jump from the slow span straight to its logs.

## Why observability is needed

- Modern systems are distributed; one user action crosses many services and no single box has the whole story.
- Failures are unpredictable; nobody can write an alert for every way a system breaks, so I need data I can explore afterwards.
- Faster recovery: less guessing means lower time to detect and to fix.
- Safer releases: compare before and after a deploy, roll back with evidence rather than a feeling.
- Cost and performance: see which service is slow or wasteful.
- Reliability targets (SLOs) need measurements.

The **four golden signals** are the minimum for any service: **latency, traffic, errors, saturation**. My Grafana dashboard in `01-monitoring` has one panel for each.

## Tools

| Need | Open source | Commercial / cloud |
| --- | --- | --- |
| Metrics | Prometheus, VictoriaMetrics, Mimir | Datadog, New Relic, CloudWatch |
| Dashboards | Grafana | Datadog, CloudWatch dashboards |
| Alerting | Alertmanager, Grafana Alerting | PagerDuty, Opsgenie |
| Logs | Loki, Elasticsearch + Kibana (EFK), Fluent Bit | Splunk, CloudWatch Logs |
| Traces | Jaeger, Tempo, Zipkin | Datadog APM, AWS X-Ray |
| Instrumentation standard | OpenTelemetry | supported by nearly every vendor |
| Host metrics | node-exporter | CloudWatch agent |

OpenTelemetry is the vendor-neutral way to produce all three signals from code once and send them anywhere. The usual free stack is LGTM: Loki (logs), Grafana (UI), Tempo (traces), Mimir or Prometheus (metrics).

## Observability in Kubernetes

Every layer needs watching: the cluster, the nodes, the Pods, and the application inside them.

| Layer | What to watch | How |
| --- | --- | --- |
| Built in | Pod phase, events, logs, resource use | `kubectl get`, `describe`, `logs`, `get events`, `top` |
| Resource metrics | CPU and memory per Pod and node | metrics-server (also powers `kubectl top` and the HPA, see Session 13) |
| Object state | Replicas, restarts, phases | kube-state-metrics |
| Node and container health | CPU, memory, disk, network | node-exporter, cAdvisor inside the kubelet |
| Application | Requests, errors, latency | The app exposes `/metrics`; Prometheus scrapes it |
| Logs | Every container's stdout | A log agent per node (Fluent Bit, Promtail) shipping to Loki or Elasticsearch |
| Traces | Calls between services | OpenTelemetry SDKs, a collector, Jaeger or Tempo |

The one-command way to get most of this is the `kube-prometheus-stack` Helm chart: Prometheus, Alertmanager, Grafana, node-exporter, kube-state-metrics and a set of dashboards. Prometheus then finds applications through `ServiceMonitor` objects. My final project does exactly that: the backend exposes `/metrics`, the Helm chart ships a ServiceMonitor, and the dashboard in `final-devops-project/monitoring/` reads from it.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
kubectl top nodes; kubectl top pods -A
kubectl logs <pod> --previous
kubectl get events --sort-by=.lastTimestamp
```

## How the demo maps to the pillars

| Pillar | In `01-monitoring` |
| --- | --- |
| Metrics | Complete: Prometheus scraping, PromQL, Grafana, five alert rules |
| Logs | `docker compose logs app`; a real setup ships them to Loki or Elasticsearch |
| Traces | Explained only. The demo is one service, so there is no multi-service journey to trace |

## Summary

Monitoring watches known signals; observability lets me explain unknown problems. Metrics detect, traces locate, logs explain. In Kubernetes, start with `kubectl`, add metrics-server, then Prometheus and Grafana, then a log pipeline, then tracing as the system grows.
