"""Vansh's monitoring demo service.

A tiny Flask app that exposes Prometheus metrics and writes one log line per request,
with endpoints that behave badly on purpose so dashboards and alerts have something to show.
"""
import logging
import os
import random
import sys
import time

from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("demo-app")

app = Flask(__name__)

REQUESTS = Counter("http_requests_total", "HTTP requests handled", ["method", "endpoint", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request duration in seconds", ["endpoint"],
                    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 1.5, 2, 3))


@app.before_request
def start_timer():
    request.started = time.perf_counter()


@app.after_request
def record(response):
    if request.path != "/metrics":
        elapsed = time.perf_counter() - request.started
        REQUESTS.labels(request.method, request.path, response.status_code).inc()
        LATENCY.labels(request.path).observe(elapsed)
        log.info("%s %s -> %s in %.3fs", request.method, request.path, response.status_code, elapsed)
    return response


@app.get("/")
def index():
    return jsonify(message="Hello from Vansh's monitored app", owner="Vansh", session=20)


@app.get("/health")
def health():
    return "UP", 200


@app.get("/error")
def error():
    log.error("Simulated failure on /error (requested by %s)", request.remote_addr)
    return jsonify(error="simulated failure"), 500


@app.get("/slow")
def slow():
    time.sleep(random.uniform(1.2, 2.0))  # nosec B311 - demo latency, not security
    return jsonify(message="that was slow")


@app.get("/cpu")
def cpu():
    end = time.perf_counter() + 1.0
    n = 0
    while time.perf_counter() < end:
        n += 1
    return jsonify(message="burned one second of CPU", loops=n)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")))
