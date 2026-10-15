import pytest
from starlette.testclient import TestClient
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "synthetic-data result" in data["notice"]


def test_api_scenarios_list(client):
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 6
    ids = [s["scenario_id"] for s in scenarios]
    assert "S1" in ids
    assert "S2" in ids
    assert "S6" in ids


def test_api_simulation_run_and_graph(client):
    res = client.post("/api/simulation/run", json={"scenario_id": "S1", "seed": 42, "total_windows": 5})
    assert res.status_code == 200
    data = res.json()
    assert data["scenario_id"] == "S1"

    # Get graph
    graph_res = client.get("/api/simulation/graph?window_index=1")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert "clusters" in graph_data


def test_api_audit_log_and_tamper_demo(client):
    # Run S2 to generate real audit logs
    client.post("/api/simulation/run", json={"scenario_id": "S2", "seed": 42, "total_windows": 3})

    # Fetch audit logs
    logs_res = client.get("/api/audit/logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert logs["total_records"] > 0
    assert logs["is_chain_valid"] is True

    # Tamper with record 2
    tamper_res = client.post("/api/audit/tamper", json={"record_index": 2})
    assert tamper_res.status_code == 200
    t_data = tamper_res.json()
    assert t_data["chain_valid"] is False
    assert t_data["detected_corrupt_index"] == 2
