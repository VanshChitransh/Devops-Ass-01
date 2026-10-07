"""Vansh's DevSecOps demo service.

A small Flask API with a health endpoint, a status endpoint and two calculation endpoints.
It is deliberately simple so the pipeline around it (tests, SAST, SCA, secret scan,
image scan, gate, registry push, Kubernetes deploy) is the interesting part.
"""
import os
import time

from flask import Flask, jsonify, render_template, request

APP_NAME = "vansh-devsecops-api"
VERSION = os.environ.get("APP_VERSION", "1.0.0")
STARTED_AT = time.time()

app = Flask(__name__)


def _numbers(payload):
    """Validate a JSON body with number1 and number2. Returns (a, b) or raises ValueError."""
    if not payload or "number1" not in payload or "number2" not in payload:
        raise ValueError("number1 and number2 are required")
    try:
        return float(payload["number1"]), float(payload["number2"])
    except (TypeError, ValueError) as exc:
        raise ValueError("number1 and number2 must be numbers") from exc


@app.get("/")
def index():
    return render_template("index.html", app_name=APP_NAME, version=VERSION)


@app.get("/health")
def health():
    return jsonify(status="healthy", app=APP_NAME)


@app.get("/api/status")
def status():
    return jsonify(app=APP_NAME, version=VERSION, uptime_seconds=round(time.time() - STARTED_AT, 1), owner="Vansh")


@app.post("/api/add")
def add():
    try:
        a, b = _numbers(request.get_json(silent=True))
    except ValueError as err:
        return jsonify(error=str(err)), 400
    return jsonify(operation="add", result=a + b)


@app.post("/api/multiply")
def multiply():
    try:
        a, b = _numbers(request.get_json(silent=True))
    except ValueError as err:
        return jsonify(error=str(err)), 400
    return jsonify(operation="multiply", result=a * b)


@app.errorhandler(404)
def not_found(_):
    return jsonify(error="not found"), 404


if __name__ == "__main__":
    # Local development only. In the container gunicorn serves the app.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5001")))
