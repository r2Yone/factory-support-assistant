# Support Assistant: fábrica de agentes

Asistente de soporte técnico de primer nivel: la persona describe su problema, el asistente lo clasifica y busca
una solución en la base de conocimiento de la mesa de ayuda (`spec/knowledge_base.json`). Si no la encuentra, la
transfiere con el equipo humano de esa categoría.

No se programa a mano: una fábrica de agentes de Claude Code lo construye a partir de la especificación de `spec/`,
y una persona aprueba el plan y revisa el resultado.

Hay dos repositorios:

| Repositorio | Qué contiene | Para qué |
| --- | --- | --- |
| `factory-support-assistant` (este) | La fábrica: especificaciones, agentes, hooks y verificaciones | Construir o cambiar el producto |
| `support-assistant` | El producto que construyó la fábrica | Usar el asistente o publicarlo; su README explica cómo correrlo solo |

## Cómo trabaja la fábrica

| Paso | Quién | Patrón |
| --- | --- | --- |
| Plan | `architect` y tú lo apruebas | Humano en el lazo |
| Pruebas primero | `qa-unit` | TDD |
| Código | Los especialistas de la especificación (ver la tabla de «Correr la fábrica»), en paralelo cuando no dependen entre sí | Paralelización |
| unit → contract → qa → e2e → evaluate | El código decide; al primer fallo se corrige (máximo 2) | Encadenamiento con compuertas |
| Revisión contra QA.md | `qa-style` devuelve APROBADO o CAMBIOS (máximo 2 vueltas) | Evaluador-optimizador |
| Publicar (las que publican) | Tú apruebas; `scripts/publish.py` hace el push y Render despliega si el CI pasa | Humano en el lazo |
| Prueba de humo | Si falla, `triage` decide quién corrige (máximo 2 ciclos) | Enrutamiento |
| Pipeline y reporte | `scripts/pipeline.py` con la bitácora | |

## Requisitos

### En tu computadora

| Herramienta | Para qué | Cómo comprobarla |
| --- | --- | --- |
| Git | Clonar los repositorios | `git --version` |
| Python 3.12 | El producto y las verificaciones | `python --version` |
| [uv](https://docs.astral.sh/uv/) | La fábrica corre todo con `uv run` | `uv --version` |
| [Claude Code](https://claude.com/claude-code) | Los agentes y el orquestador `/factory` (necesita tu propia suscripción) | `claude --version` |
| [GitHub CLI](https://cli.github.com/) | `scripts/publish.py` crea el repositorio del producto en **tu** cuenta | `gh auth status` (si no, `gh auth login`) |
| Docker (opcional) | Probar la imagen del producto antes de publicarla | `docker --version` |

### Cuentas

Cada persona usa las suyas; ninguna clave va en el repositorio.

| Servicio | ¿Obligatorio? | Qué necesitas |
| --- | --- | --- |
| GitHub | Sí | Acceso a los dos repositorios (son privados: pide que te agreguen como colaborador) |
| Cloudflare | Para el modelo real | Account ID; un AI Gateway creado (su nombre va en `CF_GATEWAY_ID`); un token con **Workers AI: Read** y **AI Gateway: Run** |
| Render | Para publicar | Una cuenta conectada a GitHub |
| LangSmith | No | Una API key, si quieres trazas |

Las verificaciones de la fábrica nunca usan estas cuentas: corren con el modelo simulado, sin red y sin gastar.

## Preparar

```powershell
git clone https://github.com/r2Yone/factory-support-assistant.git
cd factory-support-assistant
uv venv --python 3.12
.venv\Scripts\activate
uv pip install -r requirements.txt
uv run playwright install chromium
uv run python scripts/verify.py
```

`scripts/verify.py` comprueba la fábrica misma (sus pruebas, pylint y que no haya emojis).

### El producto: reconstruir

- **Reconstruir desde cero.**  Es lento, y el código no será idéntico al del respositorio `support-assistant` publicado, porque lo escriben los agentes. Con `production`, `publish.py` crea el repositorio del producto en tu cuenta de GitHub.

## Correr la fábrica

La primera vez que abres `claude` en esta carpeta te pregunta **«Do you trust the files in this folder?»**:
responde que sí. Sin esa confianza, Claude Code ignora los permisos de `.claude/settings.json` y los agentes no pueden
correr las verificaciones.

Ejecuta `claude` y, dentro, escribe `/factory` con la especificación que quieres construir, en el siguiente orden:

| Comando | Especificación | Especialistas |
| --- | --- | --- |
| `/factory architecture` | `spec/01-architecture.md`: el asistente que busca soluciones o transfiere | `developer` |
| `/factory observability` | `spec/02-observability.md`: folio por petición, logs JSON, métricas y trazas | `observability` |
| `/factory costs` | `spec/03-costs.md`: modelo real de Cloudflare, palancas de costo y pruebas en el navegador | `costs` y `qa-e2e` |
| `/factory production support-assistant` | `spec/04-production.md`: claves por cliente, límite de peticiones, compliance, contenedor, CI y Render | `security`, `deploy` y `qa-e2e` |
| `/factory demo support-assistant` | `spec/05-demo.md`: la página pública sin clave, con límite por IP y tope de gasto diario | `security`, `deploy` y `qa-e2e` |
| `/factory traces support-assistant` | `spec/06-traces.md`: tokens, costo y etiquetas en LangSmith; meta de latencia de 4 s | `observability` y `deploy` |
| `/factory page support-assistant` | `spec/07-page.md`: Diseña la página y el texto que tiene | `developer` y `qa-e2e` |

- Las **factory que publican son:**
- `production`, `demo`, `traces` y `page`. La segunda palabra (`support-assistant`) es el nombre del repositorio
  del producto y del servicio de Render. Al final te piden aprobación para publicar: cada publicación necesita la
  suya, porque `scripts/publish.py` borra `output/approved.txt` al publicar. Después te guían para revisar el CI en
  la pestaña Actions, crear o actualizar el servicio en Render y correr la prueba de humo.
- `--aprobar` aprueba el plan por adelantado; publicar siempre se pregunta.

Al terminar tendrás:

- `output/plan.md`: el plan que aprobaste.
- `output/qa-review.md`: la revisión de QA.
- `output/report.md`: el estado de la corrida.
- `output/pipeline.md`: el diagrama del pipeline (vista previa de Markdown).

### Tu configuración del producto

El producto se configura en `product/.env`: copia `product/.env.example` y completa tus valores. Las verificaciones
de la fábrica nunca leen ese archivo (`ENV_FILE=none`). El mínimo para usar el modelo real y la página:

```
MODEL_PROVIDER=gateway
CF_ACCOUNT_ID=<tu-account-id>
CF_GATEWAY_ID=<el-nombre-de-tu-gateway>
CF_API_TOKEN=<tu-token>
API_KEYS=<tu-nombre>:<una-clave-generada>
PUBLIC_PAGE=true
```

Para generar una clave: `uv run python -c "import secrets; print(secrets.token_urlsafe(24))"`. Sin las variables
`CF_*` y con `MODEL_PROVIDER=fake` (el valor por omisión), responde el modelo simulado.

## Comprobar

Las mismas compuertas que usa la fábrica. `contract` lleva el número de la última especificación construida:

```powershell
uv run python -m verification unit
uv run python -m verification contract 07
uv run python -m verification qa
uv run python -m verification e2e
uv run python -m verification evaluate
```

`unit` corre sobre una copia aislada de `product/`, igual que el CI: una prueba que lea algo de fuera del producto
falla aquí, antes de publicar.

Para probarlo a mano, con `PUBLIC_PAGE=true` en tu `product/.env`:

```powershell
cd product
uv run uvicorn app.main:app
```

Abre http://127.0.0.1:8000 y describe un problema, por ejemplo:

- «No me puedo conectar a la VPN desde mi casa»: hay solución en la base de conocimiento.
- «Mi teclado tiene teclas que no funcionan»: no hay solución, te transfiere con Soporte en sitio.
- «Quiero hablar con una persona»: te transfiere con la Mesa de Servicio General.

Contra el servicio publicado, la prueba de humo (la clave va en una variable, nunca en el comando):

```powershell
$env:SMOKE_API_KEY = "<tu clave, sin el nombre del cliente>"
uv run python -m verification production https://<tu-servicio>.onrender.com
```
