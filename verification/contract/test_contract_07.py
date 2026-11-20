"""Contrato de la página: el texto, el diseño y lo que no debe cambiar."""

import re

import httpx

from verification.server import PRODUCT

WELCOME = (
    "Bienvenido al sitio de soporte con IA. Describe tu problema y buscaremos una "
    "solución, si no la encontramos, te transferimos con el equipo que puede ayudarte."
)
EXAMPLES = (
    "No me puedo conectar a la VPN desde mi casa",
    "Olvidé mi contraseña",
    "Mi teclado tiene teclas que no funcionan",
)


def page(api):
    """El HTML de la página, con los espacios de más reducidos a uno."""
    html = httpx.get(f"{api.base_url}/").text
    return re.sub(r"\s+", " ", html)


def test_the_page_shows_the_new_welcome_text(api):
    html = page(api)
    assert WELCOME in html
    assert "Cuéntanos qué te pasa" not in html


def test_the_page_offers_three_examples(api):
    html = page(api)
    assert html.count('data-testid="example"') == 3
    for example in EXAMPLES:
        assert example in html


def test_the_page_keeps_its_test_ids(api):
    html = page(api)
    for test_id in ("question", "send", "answer", "escalation"):
        assert f'data-testid="{test_id}"' in html


def test_the_page_adapts_to_dark_mode_phones_and_reduced_motion(api):
    html = page(api)
    assert "prefers-color-scheme: dark" in html
    assert "prefers-reduced-motion" in html
    assert 'name="viewport"' in html


def test_the_page_loads_nothing_from_other_sites(api):
    assert not re.search(r'(src|href)\s*=\s*"(https?:)?//', page(api))


def test_the_dead_code_is_gone():
    app = PRODUCT / "app"
    assert "def build_model(" not in (app / "llm.py").read_text(encoding="utf-8")
    assert "def build_tracer(" not in (app / "tracing.py").read_text(encoding="utf-8")
