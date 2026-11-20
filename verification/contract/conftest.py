"""El producto corriendo, para las pruebas de contrato."""

import pytest

from verification.server import running_product


@pytest.fixture(scope="session")
def api():
    """El producto con su configuración por omisión."""
    with running_product(8765) as client:
        yield client


@pytest.fixture(scope="session")
def api_one_step():
    """El producto con el bucle limitado a una sola vuelta."""
    with running_product(8766, AGENT_MAX_STEPS="1") as client:
        yield client


@pytest.fixture(scope="session")
def api_limited():
    """El producto con un límite de dos peticiones por minuto."""
    with running_product(8770, RATE_LIMIT_PER_MINUTE="2") as client:
        yield client


@pytest.fixture(scope="session")
def api_public():
    """El producto en modo demo, con un tope de gasto que no se alcanza."""
    with running_product(8775, PUBLIC_PAGE="true", DAILY_BUDGET_USD="1") as client:
        yield client


@pytest.fixture(scope="session")
def api_proxy(tmp_path_factory):
    """El modo demo detrás de un proxy, con dos preguntas por IP y su log."""
    log = tmp_path_factory.mktemp("proxy") / "product.log"
    with running_product(
        8776, log_file=log, PUBLIC_PAGE="true", TRUST_PROXY="true",
        PUBLIC_RATE_LIMIT_PER_MINUTE="2",
    ) as client:
        yield client, log


@pytest.fixture(scope="session")
def api_budget():
    """El modo demo con un tope que se agota en la primera pregunta."""
    with running_product(
        8777, PUBLIC_PAGE="true", DAILY_BUDGET_USD="0.000001"
    ) as client:
        yield client


@pytest.fixture(scope="session")
def api_traced():
    """El producto con las trazas encendidas y LangSmith inalcanzable."""
    with running_product(
        8778, LANGSMITH_TRACING="true", LANGSMITH_API_KEY="factory-not-a-real-key",
        LANGSMITH_ENDPOINT="http://127.0.0.1:9",
    ) as client:
        yield client


@pytest.fixture(scope="session")
def api_logged(tmp_path_factory):
    """El producto con su configuración por omisión y su log en un archivo."""
    log = tmp_path_factory.mktemp("logged") / "product.log"
    with running_product(8771, log_file=log) as client:
        yield client, log


@pytest.fixture(scope="session")
def config_file(tmp_path_factory):
    """Un archivo de configuración temporal que apaga el enrutamiento."""
    path = tmp_path_factory.mktemp("config") / "support.env"
    path.write_text("ROUTING=false\n", encoding="utf-8")
    return path


@pytest.fixture(scope="session")
def api_from_file(config_file):
    """El producto configurado con el archivo temporal."""
    with running_product(8773, ENV_FILE=str(config_file)) as client:
        yield client


@pytest.fixture(scope="session")
def api_env_wins(config_file):
    """El producto con el archivo temporal y ``ROUTING=true`` en el entorno."""
    with running_product(8774, ENV_FILE=str(config_file), ROUTING="true") as client:
        yield client


@pytest.fixture(scope="session")
def api_private(tmp_path_factory):
    """El producto con ``LOG_CONVERSATION_TEXT=false`` y su log en un archivo."""
    log = tmp_path_factory.mktemp("private") / "product.log"
    with running_product(8772, log_file=log, LOG_CONVERSATION_TEXT="false") as client:
        yield client, log
