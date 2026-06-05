"""Sanity tests for the deployment endpoints."""

from tests.conftest import make_deployment, seed


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_empty(client):
    res = client.get("/deployments")
    assert res.status_code == 200
    assert res.json() == []
    assert res.headers["X-Total-Count"] == "0"


def test_list_returns_seeded_deployments(client, session_factory):
    seed(
        session_factory,
        [
            make_deployment(id="deploy_001", service="billing-api", status="failed"),
            make_deployment(id="deploy_002", service="auth-service", status="success"),
        ],
    )
    res = client.get("/deployments")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 2
    assert res.headers["X-Total-Count"] == "2"
    # Response shape matches the documented contract.
    assert set(body[0].keys()) == {
        "id",
        "service",
        "status",
        "duration",
        "timestamp",
        "commit_sha",
    }
    # Timestamps are serialized as ISO-8601 UTC with a trailing "Z".
    assert body[0]["timestamp"].endswith("Z")


def test_filter_by_service(client, session_factory):
    seed(
        session_factory,
        [
            make_deployment(id="deploy_001", service="billing-api"),
            make_deployment(id="deploy_002", service="auth-service"),
        ],
    )
    res = client.get("/deployments", params={"service": "auth-service"})
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["service"] == "auth-service"


def test_filter_by_status(client, session_factory):
    seed(
        session_factory,
        [
            make_deployment(id="deploy_001", status="success"),
            make_deployment(id="deploy_002", status="failed"),
            make_deployment(id="deploy_003", status="failed"),
        ],
    )
    res = client.get("/deployments", params={"status": "failed"})
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_filter_by_service_and_status(client, session_factory):
    seed(
        session_factory,
        [
            make_deployment(id="deploy_001", service="billing-api", status="success"),
            make_deployment(id="deploy_002", service="billing-api", status="failed"),
            make_deployment(id="deploy_003", service="auth-service", status="failed"),
        ],
    )
    res = client.get(
        "/deployments", params={"service": "billing-api", "status": "failed"}
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["id"] == "deploy_002"


def test_invalid_status_filter_returns_422(client):
    res = client.get("/deployments", params={"status": "exploded"})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == 422
    assert body["error"]["status"] == "INVALID_ARGUMENT"
    # Field name is reported without the transport-location prefix ("query.").
    assert body["error"]["details"][0]["field"] == "status"


def test_get_by_id(client, session_factory):
    seed(session_factory, [make_deployment(id="deploy_123", service="billing-api")])
    res = client.get("/deployments/deploy_123")
    assert res.status_code == 200
    assert res.json()["id"] == "deploy_123"


def test_get_unknown_returns_404_envelope(client):
    res = client.get("/deployments/nope")
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == 404
    assert body["error"]["status"] == "NOT_FOUND"
    assert body["error"]["message"] == "Deployment not found"
    # Error responses must carry the correlation id, just like success responses.
    assert res.headers.get("X-Request-ID")
