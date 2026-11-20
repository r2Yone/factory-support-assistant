"""Pruebas de la prueba de humo, con un servidor simulado (sin red)."""

import httpx

from verification import production


def fake_render(checks_keys=True, healthy=True, public=False):
    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200 if healthy else 503)
        key = request.headers.get("X-API-Key")
        if key is None:
            return httpx.Response(200 if public else 401)
        return httpx.Response(200 if key == "good-key" or not checks_keys else 401)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_a_healthy_protected_service_passes(capsys):
    assert production.smoke("https://x", "good-key", fake_render())
    assert capsys.readouterr().out.count("[OK]") == 3


def test_a_public_demo_that_checks_keys_passes():
    assert production.smoke("https://x", "good-key", fake_render(public=True))


def test_a_service_that_accepts_any_key_fails():
    open_service = fake_render(checks_keys=False)
    assert not production.smoke("https://x", "good-key", open_service)


def test_a_sleeping_service_fails():
    assert not production.smoke("https://x", "good-key", fake_render(healthy=False))


def test_the_key_must_come_from_the_environment(monkeypatch, capsys):
    monkeypatch.delenv("SMOKE_API_KEY", raising=False)
    assert production.main(["https://x"]) == 2
    assert "SMOKE_API_KEY" in capsys.readouterr().out
