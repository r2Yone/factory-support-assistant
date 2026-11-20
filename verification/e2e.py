"""Corre las pruebas de Playwright de ``product/e2e/`` contra el producto vivo."""

import os
import subprocess
import sys

from verification.server import FACTORY_KEY, PRODUCT, running_product

PORT = 8769


def main() -> int:
    """Arranca el producto, corre las pruebas e2e y devuelve su código."""
    if not (PRODUCT / "e2e").is_dir():
        print("[FAIL] e2e: todavía no existe product/e2e/")
        return 1
    command = [sys.executable, "-m", "pytest", "e2e", "-q", "-p", "no:cacheprovider",
               "--base-url", f"http://127.0.0.1:{PORT}"]
    # La página de la demo no pide clave (spec/05-demo.md). E2E_API_KEY se
    # conserva para las pruebas que todavía la lean; nunca va escrita en ellas.
    env = {**os.environ, "E2E_API_KEY": FACTORY_KEY}
    with running_product(PORT, PUBLIC_PAGE="true"):
        code = subprocess.run(command, cwd=PRODUCT, env=env, check=False).returncode
    return code


if __name__ == "__main__":
    sys.exit(main())
