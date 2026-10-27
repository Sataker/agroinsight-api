import pytest

from src.api.deps import create_access_token


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("path", [
    "/api/v1/recomendacoes/",
    "/api/v1/fazendas/",
    "/api/v1/alertas/",
])
def test_protected_routes_reject_missing_token(client, path):
    assert client.get(path).status_code == 403


def test_protected_routes_reject_forged_token(client):
    r = client.get("/api/v1/recomendacoes/", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_token_roundtrip():
    import uuid
    from jose import jwt
    from src.config import get_settings

    user_id = uuid.uuid4()
    s = get_settings()
    payload = jwt.decode(create_access_token(user_id), s.jwt_secret, algorithms=[s.jwt_algorithm])
    assert payload["sub"] == str(user_id)
