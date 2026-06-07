def test_health_endpoint_reports_api_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}


def test_db_health_endpoint_reports_database_status(client):
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_redis_health_endpoint_reports_redis_status(client):
    response = client.get("/health/redis")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
