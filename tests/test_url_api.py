from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def test_create_resolve_and_analyze_url(client: TestClient) -> None:
    created = client.post(
        "/api/v1/urls",
        json={"url": "https://example.com/a", "customAlias": "demo-link"},
    )
    assert created.status_code == 201
    assert created.json()["shortCode"] == "demo-link"

    redirect = client.get("/demo-link", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://example.com/a"

    analytics = client.get("/api/v1/urls/demo-link/analytics")
    assert analytics.status_code == 200
    assert analytics.json()["redirectCount"] == 1
    assert analytics.json()["lastAccessedAt"] is not None


def test_duplicate_alias_has_structured_conflict(client: TestClient) -> None:
    payload = {"url": "https://example.com", "customAlias": "duplicate"}
    assert client.post("/api/v1/urls", json=payload).status_code == 201
    response = client.post("/api/v1/urls", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALIAS_CONFLICT"


def test_expired_url_returns_gone(client: TestClient) -> None:
    expires = (datetime.now(UTC) + timedelta(milliseconds=50)).isoformat()
    response = client.post(
        "/api/v1/urls", json={"url": "https://example.com", "expiresAt": expires}
    )
    assert response.status_code == 201
    import time

    time.sleep(0.06)
    redirect = client.get(f"/{response.json()['shortCode']}", follow_redirects=False)
    assert redirect.status_code == 410
    assert redirect.json()["error"]["code"] == "URL_EXPIRED"


def test_delete_is_persistent(client: TestClient) -> None:
    client.post(
        "/api/v1/urls",
        json={"url": "https://example.com", "customAlias": "delete-me"},
    )
    assert client.delete("/api/v1/urls/delete-me").status_code == 204
    assert client.get("/api/v1/urls/delete-me").status_code == 404


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "healthy"}
