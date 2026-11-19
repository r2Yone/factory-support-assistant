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
