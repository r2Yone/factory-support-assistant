"""Arranca el producto con el modelo simulado para probarlo por HTTP.

Las verificaciones no importan el código del producto: le hablan como un
cliente, así que valen sin importar cómo lo haya escrito el agente.
"""

import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

PRODUCT = Path(__file__).resolve().parent.parent / "product"
# Clave de prueba de la fábrica: no es un secreto, solo existe en estas corridas
FACTORY_KEY = "factory-key-0123456789"
DEFAULTS = {
    "MODEL_PROVIDER": "fake",
    "API_KEYS": f"factory:{FACTORY_KEY}",
    "RATE_LIMIT_PER_MINUTE": "1000",
    # Nunca se lee el archivo de configuración de la persona; una prueba puede
    # apuntar ENV_FILE a un archivo temporal suyo.
    "ENV_FILE": "none",
}


@contextmanager
def running_product(port: int, log_file: Path | None = None, **env: str):
    """Corre ``uvicorn app.main:app`` en ``port`` mientras dure el bloque.

    El cliente que entrega ya manda la clave de la fábrica en ``X-API-Key``.
    Con ``log_file``, la salida estándar del producto (su log JSON) se guarda
    en ese archivo para que las pruebas la lean.
    """
    settings = {**os.environ, **DEFAULTS, **env}
    command = [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)]
    with open(log_file or os.devnull, "w", encoding="utf-8") as output:
        server = subprocess.Popen(
            command, cwd=PRODUCT, env=settings,
            stdout=output if log_file else None,
        )
        yield from _serve(server, port)


def importing_product(**env: str) -> subprocess.CompletedProcess:
    """Importa ``app.main`` con ``env`` y devuelve el proceso terminado.

    Sirve para comprobar que una configuración impide arrancar, sin abrir un
    puerto. Nunca lee el archivo de configuración de la persona.
    """
    settings = {**os.environ, "ENVIRONMENT": "development", "ENV_FILE": "none", **env}
    command = [sys.executable, "-c", "import app.main"]
    return subprocess.run(command, cwd=PRODUCT, env=settings, capture_output=True,
                          text=True, timeout=30, check=False)


def _serve(server: subprocess.Popen, port: int):
    """Espera a que el producto responda, entrega el cliente y lo detiene."""
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(40):
            try:
                httpx.get(f"{url}/health", timeout=1)
                break
            except httpx.TransportError:
                time.sleep(0.25)
        yield httpx.Client(
            base_url=url, timeout=10, headers={"X-API-Key": FACTORY_KEY}
        )
    finally:
        server.terminate()
        server.wait(timeout=10)
