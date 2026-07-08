import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_transaction_roundtrip(client):
    r = client.post("/transactions", json={"class_detected": "paper", "confidence": 0.9})
    assert r.status_code == 200
    assert r.json()["class_detected"] == "paper"
    r = client.get("/transactions?limit=5")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_stats(client):
    r = client.get("/stats")
    assert r.status_code == 200
    assert "total_today" in r.json()
