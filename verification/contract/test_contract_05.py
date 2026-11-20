"""Contrato de la demo pública: la página sin clave, con límites."""

import json

import httpx

from verification.server import importing_product

QUESTION = {"question": "No me puedo conectar a la VPN desde mi casa"}


def ask_without_key(api, headers=None):
    """Pregunta como la página de la demo: sin ``X-API-Key``."""
    return httpx.post(f"{api.base_url}/ask", json=QUESTION, headers=headers)


def test_the_demo_answers_without_a_key(api_public):
    response = ask_without_key(api_public)
    assert response.status_code == 200
    assert "KB-0001" in response.json()["answer"]


def test_the_demo_still_rejects_a_wrong_key(api_public):
    response = ask_without_key(api_public, {"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_the_demo_still_protects_the_metrics(api_public):
    assert httpx.get(f"{api_public.base_url}/metrics").status_code == 401
    metrics = api_public.get("/metrics").json()
    assert metrics["daily_budget_usd"] == 1
    assert metrics["public_cost_today_usd"] >= 0


def test_the_page_asks_for_no_key(api_public):
    page = httpx.get(f"{api_public.base_url}/").text
    assert 'data-testid="question"' in page
    assert 'data-testid="api-key"' not in page


def test_the_limit_counts_the_address_added_by_the_proxy(api_proxy):
    api, _ = api_proxy
    first = {"X-Forwarded-For": "198.51.100.1"}
    spoofed = {"X-Forwarded-For": "203.0.113.9, 198.51.100.1"}
    codes = [ask_without_key(api, headers).status_code
             for headers in (first, first, spoofed)]
    assert codes == [200, 200, 429]
    other = ask_without_key(api, {"X-Forwarded-For": "198.51.100.2"})
    assert other.status_code == 200


def test_the_demo_logs_the_public_client_but_never_the_address(api_proxy):
    api, log = api_proxy
    ask_without_key(api, {"X-Forwarded-For": "198.51.100.77"})
    text = log.read_text(encoding="utf-8")
    runs = [json.loads(line) for line in text.splitlines()
            if line.startswith("{") and '"agent_run"' in line]
    assert any(run.get("client") == "public" for run in runs)
    assert "198.51.100.77" not in text


def test_the_daily_budget_stops_the_demo_but_not_the_keys(api_budget):
    assert ask_without_key(api_budget).status_code == 200
    stopped = ask_without_key(api_budget)
    assert stopped.status_code == 503
    assert stopped.json()["detail"] == "daily budget exhausted"
    assert api_budget.post("/ask", json=QUESTION).status_code == 200


def test_the_demo_needs_a_budget():
    started = importing_product(PUBLIC_PAGE="true", DAILY_BUDGET_USD="0")
    assert started.returncode != 0
