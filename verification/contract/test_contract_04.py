"""Contrato de producción: solo entra quien tiene clave, y nadie abusa."""

import httpx

from verification.server import importing_product

QUESTION = {"question": "No me puedo conectar a la VPN desde mi casa"}
LONG_KEY = "k" * 20


def test_asking_without_a_key_returns_401(api):
    response = httpx.post(f"{api.base_url}/ask", json=QUESTION)
    assert response.status_code == 401


def test_asking_with_a_wrong_key_returns_401(api):
    response = api.post("/ask", json=QUESTION, headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_metrics_need_a_key(api):
    assert httpx.get(f"{api.base_url}/metrics").status_code == 401
    assert api.get("/metrics").status_code == 200


def test_health_and_page_need_no_key(api):
    # La página ya no tiene campo de clave (spec/05-demo.md)
    assert httpx.get(f"{api.base_url}/health").status_code == 200
    assert httpx.get(f"{api.base_url}/").status_code == 200


def test_too_many_requests_returns_429_with_retry_after(api_limited):
    codes = [api_limited.post("/ask", json=QUESTION) for _ in range(3)]
    assert [c.status_code for c in codes] == [200, 200, 429]
    assert int(codes[-1].headers["Retry-After"]) > 0


def test_production_refuses_the_fake_model():
    started = importing_product(
        ENVIRONMENT="production", MODEL_PROVIDER="fake", API_KEYS="a:" + LONG_KEY
    )
    assert started.returncode != 0


def production(api_keys):
    """Variables de producción válidas salvo, quizá, ``api_keys``."""
    return {
        "ENVIRONMENT": "production", "MODEL_PROVIDER": "gateway",
        "API_KEYS": api_keys, "CF_ACCOUNT_ID": "account", "CF_API_TOKEN": "token",
    }


def test_production_starts_when_every_rule_holds():
    started = importing_product(**production("a:" + LONG_KEY))
    assert started.returncode == 0, started.stderr


def test_production_refuses_a_short_key_without_leaking_it():
    started = importing_product(**production("a:Xq7-tiny"))
    assert started.returncode != 0
    assert "Xq7-tiny" not in started.stderr


def test_a_broken_api_keys_never_leaks_the_key():
    started = importing_product(API_KEYS="secret-value-without-client")
    assert started.returncode != 0
    assert "secret-value-without-client" not in started.stderr
