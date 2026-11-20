"""Contrato de las trazas: lo que se ve desde afuera del producto."""

import re
import time

from verification.server import PRODUCT

SPEC = PRODUCT.parent / "spec"
QUESTION = {"question": "No me puedo conectar a la VPN desde mi casa"}
# Se lee antes del archivo de configuración: no tiene sentido listarla en él
READ_BEFORE_THE_FILE = {"ENV_FILE"}


def spec_variables():
    """Las variables de las tablas de configuración de ``spec/``."""
    names = set()
    for spec in SPEC.glob("*.md"):
        for line in spec.read_text(encoding="utf-8").splitlines():
            cells = line.split("|")
            if line.startswith("| `") and len(cells) > 2:
                names.update(re.findall(r"`([A-Z][A-Z0-9_]+)`", cells[1]))
    return names - READ_BEFORE_THE_FILE


def example_variables():
    """Las variables que define ``product/.env.example``, comentadas o no."""
    text = (PRODUCT / ".env.example").read_text(encoding="utf-8")
    return set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", text, flags=re.MULTILINE))


def test_the_latency_target_is_four_seconds(api):
    assert api.get("/metrics").json()["slo"]["p95_ms_target"] == 4000


def test_the_example_lists_every_variable_of_the_specification():
    missing = spec_variables() - example_variables()
    assert not missing, f"Faltan en .env.example: {sorted(missing)}"


def test_render_declares_the_tracing_settings():
    blueprint = (PRODUCT / "render.yaml").read_text(encoding="utf-8")
    for name in ("LANGSMITH_TRACING", "LANGSMITH_PROJECT", "SLO_P95_MS"):
        assert f"key: {name}" in blueprint


def test_an_answer_never_waits_for_langsmith(api_traced):
    started = time.monotonic()
    response = api_traced.post("/ask", json=QUESTION)
    assert response.status_code == 200
    assert "KB-0001" in response.json()["answer"]
    assert time.monotonic() - started < 5
