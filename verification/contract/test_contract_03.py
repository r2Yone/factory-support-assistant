"""Contrato de los costos: cada respuesta dice qué modelo usó y cuánto costó."""

import json

from verification.server import PRODUCT

SMALL = "@cf/meta/llama-3.1-8b-instruct-fast"
LARGE = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"


def ask(api, question):
    return api.post("/ask", json={"question": question}).json()


def test_a_simple_problem_goes_to_the_small_model(api):
    body = ask(api, "Mi laptop no enciende")
    assert body["model"] == SMALL
    assert body["route"] == "default"
    assert body["cost_usd"] > 0
    assert body["cached_calls"] == 0


def test_a_problem_that_asks_why_goes_to_the_large_model(api):
    body = ask(api, "¿Por qué se me desconecta la VPN cuando trabajo desde casa?")
    assert body["model"] == LARGE
    assert body["route"].startswith("keyword:")


def test_a_recurring_problem_goes_to_the_large_model(api):
    body = ask(api, "Otra vez no me conecta la VPN")
    assert body["model"] == LARGE


def test_a_long_problem_goes_to_the_large_model(api):
    long_problem = (
        "Desde esta mañana no me puedo conectar a la VPN desde mi casa y ya "
        "reinicié el equipo dos veces sin que cambie nada"
    )
    body = ask(api, long_problem)
    assert body["model"] == LARGE
    assert body["route"] == "long_question"


def test_the_large_model_costs_more_for_the_same_problem(api):
    cheap = ask(api, "Mi laptop no enciende")
    expensive = ask(api, "Otra vez mi laptop no enciende")
    assert expensive["cost_usd"] > cheap["cost_usd"]


def test_the_product_reads_its_config_file(api_from_file):
    body = ask(api_from_file, "Mi laptop no enciende")
    assert body["model"] == LARGE
    assert body["route"] == "routing_disabled"


def test_the_environment_wins_over_the_config_file(api_env_wins):
    body = ask(api_env_wins, "Mi laptop no enciende")
    assert body["model"] == SMALL


def test_a_forgotten_password_finds_its_article(api):
    for question in ("Se me olvidó la contraseña", "Quiero recuperar mi password"):
        body = ask(api, question)
        assert "KB-0003" in body["answer"]
        assert body["escalated"] is False


def test_the_product_knowledge_base_is_a_copy_of_the_specification():
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))

    spec = PRODUCT.parent / "spec" / "knowledge_base.json"
    assert read(PRODUCT / "data" / "knowledge_base.json") == read(spec)


def test_an_escalation_ends_with_the_fixed_message(api):
    body = ask(api, "Mi teclado tiene teclas que no funcionan")
    assert body["answer"] == "Te comunico con Soporte en sitio."
    assert body["steps"] == 2


def test_metrics_add_up_the_cost_and_the_cost_per_solved_problem(api):
    ask(api, "Mi laptop no enciende")
    metrics = api.get("/metrics").json()
    assert metrics["cost_usd"] > 0
    assert 0 < metrics["cost_per_solved_usd"] <= metrics["cost_usd"]
