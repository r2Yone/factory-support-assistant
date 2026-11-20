"""Corre una verificación del producto y termina con su código de salida.

Uso: ``uv run python -m verification <paso>``, con uno de estos pasos:

- ``unit``: las pruebas que escribió qa-unit, con cobertura de 80 % o más.
- ``contract [NN]``: las pruebas de la fábrica contra el producto corriendo. Con
  ``NN`` (por ejemplo ``05``), solo los contratos de las especificaciones 01 a NN:
  los de una especificación que todavía no se construye no cuentan.
- ``qa``: la parte de QA.md que revisa un programa (``verification/qa.py``).
- ``e2e``: las pruebas de Playwright que escribió qa-e2e (``verification/e2e.py``).
- ``evaluate``: costo y calidad contra la línea base (``verification/evaluate.py``).
- ``production <url>``: la prueba de humo contra Render (``verification.production``).

Código 0: pasa. Cualquier otro: falla, y la salida dice por qué.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCT = ROOT / "product"
PYTEST = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
STEPS = {
    "unit": (PYTEST + ["tests", "--cov=app", "--cov-fail-under=80"], PRODUCT),
    "contract": (PYTEST + ["verification/contract"], ROOT),
    "qa": ([sys.executable, "-m", "verification.qa"], ROOT),
    "e2e": ([sys.executable, "-m", "verification.e2e"], ROOT),
    "evaluate": ([sys.executable, "-m", "verification.evaluate"], ROOT),
    "production": ([sys.executable, "-m", "verification.production"], ROOT),
}
# Las verificaciones nunca leen el archivo de configuración de la persona
# (spec/03-costs.md): corren solo con el entorno que ponen ellas.
ISOLATED = {"ENV_FILE": "none"}
# El producto se publica solo, sin la fábrica: sus pruebas corren en una copia
# de product/ fuera de la fábrica, igual que en el CI. Lo que queda fuera de la
# copia nunca se sube o no es del producto.
STANDALONE = {"unit"}
NOT_COPIED = shutil.ignore_patterns(
    ".env", ".git", ".venv", "__pycache__", ".coverage", "*.log"
)


def _run_in(command: list[str], folder: Path, step: str) -> int:
    """Corre ``command`` en ``folder`` o, si ``step`` lo pide, en una copia aislada.

    :param command: Comando y argumentos.
    :param folder: Carpeta donde corre.
    :param step: Nombre del paso.
    :return: Código de salida del comando.
    """
    env = {**os.environ, **ISOLATED}
    if step not in STANDALONE:
        return subprocess.run(command, cwd=folder, env=env, check=False).returncode
    with tempfile.TemporaryDirectory() as temporary:
        copy = Path(temporary) / "product"
        shutil.copytree(folder, copy, ignore=NOT_COPIED)
        return subprocess.run(command, cwd=copy, env=env, check=False).returncode


def contracts_up_to(number: int) -> list[str]:
    """Los archivos de contrato de las especificaciones 01 a ``number``.

    ``test_contract.py`` es el de la 01; los demás llevan su número.

    :param number: Número de la última especificación construida.
    :return: Rutas relativas a la raíz de la fábrica.
    """
    folder = ROOT / "verification" / "contract"
    files = [folder / "test_contract.py"] + [
        folder / f"test_contract_{n:02d}.py" for n in range(2, number + 1)
    ]
    return [path.relative_to(ROOT).as_posix() for path in files if path.exists()]


def run(step: str, extra: list[str] | None = None) -> int:
    """Corre la verificación ``step`` e imprime ``[OK]`` o ``[FAIL]``.

    ``extra`` son argumentos para el paso, por ejemplo la URL de ``production``.
    """
    if step not in STEPS:
        print(f"Uso: python -m verification {{{'|'.join(STEPS)}}}")
        return 2
    command, folder = STEPS[step]
    if not (PRODUCT / "app").is_dir():
        print(f"[FAIL] {step}: todavía no existe product/app/")
        return 1
    extra = list(extra or [])
    if step == "contract" and extra and extra[0].isdigit():
        command = PYTEST + contracts_up_to(int(extra.pop(0)))
    code = _run_in(command + extra, folder, step)
    print(f"[{'OK' if code == 0 else 'FAIL'}] {step}")
    return code


if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2:]))
