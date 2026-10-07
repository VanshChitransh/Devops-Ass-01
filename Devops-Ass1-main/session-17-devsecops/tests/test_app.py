import pytest

from app.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"vansh-devsecops-api" in res.data


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"


def test_status_fields(client):
    body = client.get("/api/status").get_json()
    assert body["app"] == "vansh-devsecops-api"
    assert body["owner"] == "Vansh"
    assert body["uptime_seconds"] >= 0


def test_add(client):
    res = client.post("/api/add", json={"number1": 10, "number2": 20})
    assert res.status_code == 200
    assert res.get_json()["result"] == 30


def test_multiply(client):
    res = client.post("/api/multiply", json={"number1": 6, "number2": 7})
    assert res.get_json()["result"] == 42


def test_add_missing_field(client):
    res = client.post("/api/add", json={"number1": 1})
    assert res.status_code == 400
    assert "required" in res.get_json()["error"]


def test_add_not_a_number(client):
    res = client.post("/api/add", json={"number1": "ten", "number2": 2})
    assert res.status_code == 400


def test_unknown_route_is_json_404(client):
    res = client.get("/nope")
    assert res.status_code == 404
    assert res.get_json() == {"error": "not found"}
