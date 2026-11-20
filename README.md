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
| Código | El especialista de la especificación: `developer`, `observability`, `costs` (con `qa-e2e` en paralelo) o `security`, `deploy` y `qa-e2e` en paralelo | Paralelización |
| unit → contract → qa | El código decide; al primer fallo se corrige (máximo 2) | Encadenamiento con compuertas |
| Revisión contra QA.md | `qa-style` devuelve APROBADO o CAMBIOS (máximo 2 vueltas) | Evaluador-optimizador |
| Publicar (solo `production`) | Tú apruebas; `scripts/publish.py` hace el push y Render despliega si el CI pasa | Humano en el lazo |
| Prueba de humo | Si falla, `triage` decide quién corrige (máximo 2 ciclos) | Enrutamiento |
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
3. `/factory costs`: `spec/03-costs.md`, modelo real de Cloudflare, palancas de costo y pruebas en el navegador.
   La primera vez instala el navegador de las pruebas con `uv run playwright install chromium`.
4. `/factory production support-assistant`: `spec/04-production.md`, claves por cliente, límite de peticiones,
   compliance, contenedor, CI y Render. Al final te pide aprobación para publicar, crea el repositorio privado
   `support-assistant` en GitHub (necesitas `gh auth login`) y te guía para crear el servicio en Render y correr la
   prueba de humo.
5. `/factory demo support-assistant`: `spec/05-demo.md`, la página pública sin clave para una demostración, con
   límite de preguntas por IP y tope de gasto diario. Se publica igual que `production`.
6. `/factory traces support-assistant`: `spec/06-traces.md`, tokens, costo y etiquetas en las trazas de LangSmith,
   `.env.example` completo y la meta de latencia p95 de 4 segundos. Se publica igual que `production`.

Desde `costs`, el producto se configura en `product/.env` (copia de `product/.env.example` con tus valores). Las
verificaciones de la fábrica nunca leen ese archivo (`ENV_FILE=none`): siempre corren con el modelo simulado.

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
