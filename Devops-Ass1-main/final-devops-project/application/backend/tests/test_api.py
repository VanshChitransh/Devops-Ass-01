def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_ready_checks_database(client):
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready", "database": "ok"}


def test_create_ticket(client, sample):
    res = client.post("/api/tickets", json=sample)
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == 1
    assert body["title"] == sample["title"]
    assert body["status"] == "open"
    assert body["assignee"] == ""


def test_create_rejects_bad_priority(client, sample):
    res = client.post("/api/tickets", json={**sample, "priority": "whenever"})
    assert res.status_code == 422


def test_list_and_filter(client, sample):
    client.post("/api/tickets", json=sample)
    client.post("/api/tickets", json={**sample, "title": "Printer out of toner", "priority": "low"})
    assert len(client.get("/api/tickets").json()) == 2
    high = client.get("/api/tickets", params={"priority": "high"}).json()
    assert [t["title"] for t in high] == ["Laptop will not boot"]


def test_get_missing_ticket_is_404(client):
    res = client.get("/api/tickets/999")
    assert res.status_code == 404
    assert res.json()["detail"] == "ticket not found"


def test_update_ticket(client, sample):
    ticket_id = client.post("/api/tickets", json=sample).json()["id"]
    res = client.put(f"/api/tickets/{ticket_id}", json={"status": "in_progress", "assignee": "vansh"})
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"
    assert res.json()["assignee"] == "vansh"
    assert res.json()["title"] == sample["title"]  # untouched fields stay


def test_delete_ticket(client, sample):
    ticket_id = client.post("/api/tickets", json=sample).json()["id"]
    assert client.delete(f"/api/tickets/{ticket_id}").status_code == 204
    assert client.get(f"/api/tickets/{ticket_id}").status_code == 404


def test_stats(client, sample):
    client.post("/api/tickets", json={**sample, "priority": "urgent"})
    client.post("/api/tickets", json={**sample, "priority": "urgent", "status": "resolved"})
    client.post("/api/tickets", json={**sample, "assignee": "vansh"})
    stats = client.get("/api/tickets/stats").json()
    assert stats["total"] == 3
    assert stats["by_status"]["open"] == 2
    assert stats["by_priority"]["urgent"] == 2
    assert stats["open_urgent"] == 1
    assert stats["unassigned"] == 2


def test_metrics_endpoint_is_prometheus_format(client):
    client.get("/api/tickets")
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "http_requests_total" in res.text
