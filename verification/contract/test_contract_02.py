"""Contrato de la observabilidad: cada petición se puede rastrear y medir."""

import json
import time
import uuid

OUTCOMES = {"solved", "escalated", "needs_detail", "incomplete"}
VPN_PROBLEM = "No me puedo conectar a la VPN desde mi casa"
KEYBOARD_PROBLEM = "Mi teclado tiene teclas que no funcionan"


def agent_run(log, request_id):
    """Busca en el log el evento ``agent_run`` de una petición.

    Espera hasta 2 segundos a que el producto escriba la línea.
    """
    for _ in range(20):
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.startswith("{"):
                continue
            event = json.loads(line)
            if event.get("event") == "agent_run" and (
                event.get("request_id") == request_id
            ):
                return event
        time.sleep(0.1)
    raise AssertionError(f"no hay agent_run para {request_id} en el log")


def ask(api, question, **headers):
    return api.post("/ask", json={"question": question}, headers=headers)


def test_every_response_carries_a_request_id(api):
    request_id = api.get("/health").headers["X-Request-ID"]
    assert uuid.UUID(request_id)


def test_the_client_request_id_is_kept(api):
    response = ask(api, "Mi laptop no enciende", **{"X-Request-ID": "folio-123"})
    assert response.headers["X-Request-ID"] == "folio-123"
    assert response.json()["request_id"] == "folio-123"


def test_an_unsafe_client_request_id_is_replaced(api):
    response = ask(api, "Mi laptop no enciende", **{"X-Request-ID": "a" * 200})
    assert uuid.UUID(response.headers["X-Request-ID"])


def test_every_answer_says_how_it_ended(api):
    solved = ask(api, "No me puedo conectar a la VPN desde mi casa").json()
    escalated = ask(api, "Mi teclado tiene teclas que no funcionan").json()
    needs_detail = ask(api, "Hola").json()
    assert solved["outcome"] == "solved"
    assert escalated["outcome"] == "escalated"
    assert needs_detail["outcome"] == "needs_detail"


def test_the_step_cap_is_reported_as_incomplete(api_one_step):
    body = ask(api_one_step, "No me puedo conectar a la VPN desde mi casa").json()
    assert body["outcome"] == "incomplete"


def test_metrics_report_latency_tokens_and_slo(api):
    ask(api, "No me puedo conectar a la VPN desde mi casa")
    metrics = api.get("/metrics").json()
    assert metrics["requests"] >= 1
    assert set(metrics["latency_ms"]) == {"p50", "p95"}
    assert metrics["tokens"]["input"] > 0
    assert isinstance(metrics["slo"]["met"], bool)


def test_metrics_report_outcomes_and_the_self_service_rate(api):
    ask(api, "No me puedo conectar a la VPN desde mi casa")
    ask(api, "Mi teclado tiene teclas que no funcionan")
    metrics = api.get("/metrics").json()
    assert set(metrics["outcomes"]) == OUTCOMES
    assert metrics["outcomes"]["solved"] >= 1
    assert metrics["outcomes"]["escalated"] >= 1
    assert 0 < metrics["self_service_rate"] < 1


def test_home_page_shows_the_request_id(api):
    assert "request_id" in api.get("/").text


def test_the_log_shows_the_question_the_answer_and_the_article(api_logged):
    client, log = api_logged
    ask(client, VPN_PROBLEM, **{"X-Request-ID": "log-solved"})
    event = agent_run(log, "log-solved")
    assert event["question"] == VPN_PROBLEM
    assert "cliente de VPN" in event["answer"]
    assert event["article_id"] == "KB-0001"
    assert event["outcome"] == "solved"


def test_an_escalated_question_is_logged_without_an_article(api_logged):
    client, log = api_logged
    ask(client, KEYBOARD_PROBLEM, **{"X-Request-ID": "log-escalated"})
    event = agent_run(log, "log-escalated")
    assert event["question"] == KEYBOARD_PROBLEM
    assert "Soporte en sitio" in event["answer"]
    assert event["article_id"] is None
    assert event["team"] == "Soporte en sitio"


def test_the_conversation_text_can_be_left_out_of_the_log(api_private):
    client, log = api_private
    ask(client, VPN_PROBLEM, **{"X-Request-ID": "log-private"})
    event = agent_run(log, "log-private")
    assert "question" not in event
    assert "answer" not in event
    assert event["article_id"] == "KB-0001"
    assert VPN_PROBLEM not in log.read_text(encoding="utf-8")
