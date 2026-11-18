# Support Assistant: fábrica de agentes

Asistente de soporte técnico de primer nivel: la persona describe su problema, el asistente lo clasifica y busca
una solución en la base de conocimiento de la mesa de ayuda (`spec/knowledge_base.json`). Si no la encuentra, la
transfiere con el equipo humano de esa categoría.

No se programa a mano: una fábrica de agentes de Claude Code lo construye a partir de la especificación de `spec/`,
y una persona aprueba el plan y revisa el resultado.

## Cómo trabaja la fábrica

| Paso | Quién | Patrón |
| --- | --- | --- |
| Plan | `architect` y tú lo apruebas | Humano en el lazo |
| Pruebas primero | `qa-unit` | TDD |
| Código | El especialista de la especificación: `developer` (arquitectura) u `observability` | |
| unit → contract → qa | El código decide; al primer fallo se corrige (máximo 2) | Encadenamiento con compuertas |
| Revisión contra QA.md | `qa-style` devuelve APROBADO o CAMBIOS (máximo 2 vueltas) | Evaluador-optimizador |
| Pipeline y reporte | `scripts/pipeline.py` con la bitácora | |

## Preparar

```powershell
uv venv --python 3.12
uv pip install -r requirements.txt
uv run python scripts/verify.py
```

## Correr la fábrica

La primera vez que abres `claude` en esta carpeta te pregunta **«Do you trust the files in this folder?»**:
responde que sí. Sin esa confianza, Claude Code ignora los permisos de `.claude/settings.json` y los agentes no pueden
correr las verificaciones.

Ejecuta `claude` y, dentro, escribe `/factory` con la especificación que quieres construir, en orden:

1. `/factory architecture`: `spec/01-architecture.md`, el asistente que busca soluciones o transfiere.
2. `/factory observability`: `spec/02-observability.md`, folio por petición, logs JSON, métricas y trazas.

Al terminar tendrás:

- `output/plan.md`: el plan que aprobaste.
- `output/qa-review.md`: la revisión de QA.
- `output/report.md`: el estado de la corrida.
- `output/pipeline.md`: el diagrama del pipeline (vista previa de Markdown).

## Comprobar

```powershell
uv run python -m verification unit
uv run python -m verification contract
uv run python -m verification qa
cd product
uv run uvicorn app.main:app
```

Abre http://127.0.0.1:8000 y describe un problema, por ejemplo:

- «No me puedo conectar a la VPN desde mi casa»: hay solución en la base de conocimiento.
- «Mi teclado tiene teclas que no funcionan»: no hay solución, te transfiere con Soporte en sitio.
- «Quiero hablar con una persona»: te transfiere con la Mesa de Servicio General.
