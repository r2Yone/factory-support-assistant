# Producción: publicarlo de forma segura

Parte del producto de `spec/01-architecture.md` a `spec/03-costs.md`. Lo cierra con acceso por clave, límite de peticiones y reglas de compliance que se revisan solas. Lo empaqueta en un contenedor, con un pipeline de CI que los ingenieros pueden ver, y lo publica en Render solo si el pipeline pasa.

## Lo que debe hacer

### Seguridad (los hace `security`)

1. **Una clave por cliente.**
   - `API_KEYS` tiene la forma `cliente:clave,cliente2:clave2`.
   - `POST /ask` y `GET /metrics` exigen el encabezado `X-API-Key`. Sin clave o con una inválida, responden `401 {"detail": "invalid or missing API key", "request_id": ...}`.
   - `GET /`, `GET /health` y `/docs` no piden clave.
   - Las claves se comparan con `hmac.compare_digest`.
   - El nombre del cliente va en el log (`client` en los eventos `request`, `agent_run` y `audit`) y en los metadatos de la traza.
   - **La clave nunca se escribe** en el log, en la traza ni en un mensaje de error.
   - Si `API_KEYS` está mal formada, el producto no arranca. El error dice qué entrada falla y su largo, nunca su valor.
2. **Límite de peticiones por cliente.** Más de `RATE_LIMIT_PER_MINUTE` peticiones en un minuto → `429 {"detail": "rate limit exceeded", "request_id": ...}` con el encabezado `Retry-After` (segundos que faltan, al menos 1). El reloj se inyecta.
3. **Gateway autenticado.** El modelo real manda también el encabezado `cf-aig-authorization: Bearer {CF_API_TOKEN}`, para funcionar con el gateway con la autenticación encendida (**Authenticated Gateway** en Cloudflare). El token necesita los permisos **Workers AI: Read** y **AI Gateway: Run**. El encabezado nunca se escribe en el log ni en un error. Las pruebas lo comprueban con `httpx.MockTransport`.
4. **Compliance como código.** Con `ENVIRONMENT=production`, el producto **se niega a arrancar** si:
   - `MODEL_PROVIDER` es `fake`.
   - `API_KEYS` está vacía o alguna clave tiene menos de 16 caracteres.
   - Las trazas están encendidas y `HIDE_INPUTS` o `HIDE_OUTPUTS` no valen `true`.

   El error dice qué regla falla, nunca un valor secreto.

   `doc/compliance-checklist.md` tiene una tabla con tres columnas: la regla, dónde está en el código y cómo se comprueba. Además tiene una sección **«Decisiones aceptadas»** con esta:
   - `LOG_CONVERSATION_TEXT=true` también en producción: el log guarda la pregunta y la respuesta para revisar la calidad del asistente. Las preguntas pueden traer datos personales, así que el acceso a los logs de Render se limita al equipo de soporte, y la decisión se revisa antes de abrir el servicio a más personas. Se apaga con `LOG_CONVERSATION_TEXT=false` sin cambiar código.
5. **La página web** tiene un campo de clave (`data-testid="api-key"`, tipo contraseña).
   - La clave se guarda en `sessionStorage`, nunca en `localStorage` ni en el código de la página, y se manda en `X-API-Key`.
   - Con `401` muestra «Clave inválida». Con `429`, «Demasiadas preguntas; espera N segundos».

### Publicación (la hace `deploy`)

6. **Contenedor.**
   - `Dockerfile` con `python:3.12-slim`, un usuario que no es root y `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`.
   - La imagen incluye `app/` y `data/` (la base de conocimiento y los precios).
   - `.dockerignore` deja fuera `.env`, `tests/`, `e2e/`, `doc/` y los cachés. En el contenedor no hay archivo `.env`: la configuración llega por el entorno de Render.
7. **Pipeline de CI** en `.github/workflows/ci.yml`. Corre en cada push y en cada pull request, con cuatro trabajos encadenados (`needs`), para que los ingenieros vean cada etapa en la pestaña Actions:
   1. `style`: pylint con 88 columnas.
   2. `unit`: pruebas y BDD con cobertura de 80 % o más.
   3. `e2e`: Playwright con el modelo simulado y `ENV_FILE=none`.
   4. `docker`: `docker build` de la imagen.
8. **Render.** `render.yaml` es un Blueprint con un servicio web:
   - El servicio se llama **igual que el repositorio** que da la persona. Así no choca con un servicio que ya exista en su cuenta de Render, porque Render actualizaría ese en lugar de crear uno nuevo.
   - `runtime: docker`, `plan: free`, `healthCheckPath: /health`.
   - `autoDeployTrigger: checksPass`: Render publica solo si el pipeline pasa.
   - Valores fijos: `ENVIRONMENT=production`, `MODEL_PROVIDER=gateway`, `CF_GATEWAY_ID=support-assistant`, `LOG_CONVERSATION_TEXT=true`, `HIDE_INPUTS=true` y `HIDE_OUTPUTS=true`.
   - Los secretos (`API_KEYS`, `CF_ACCOUNT_ID`, `CF_API_TOKEN`) con `sync: false`: se escriben en Render y nunca en el repositorio. Render exige un valor para cada uno al crear el Blueprint, por eso `LANGSMITH_API_KEY`, que es opcional, no va ahí: se agrega en Render > Environment si se encienden las trazas.
9. **Prueba de humo** en `scripts/smoke.py <url>`. Lee la clave de la variable `SMOKE_API_KEY`, nunca de un argumento, y comprueba tres cosas, imprimiendo `[OK]` o `[FAIL]` en cada una:
   - `/health` responde `200`.
   - `/ask` sin clave responde `401`.
   - `/ask` con clave y el problema «No me puedo conectar a la VPN desde mi casa» responde `200`.

## Pruebas de punta a punta (las actualiza `qa-e2e`)

- Las pruebas de `spec/03-costs.md` ahora escriben primero la clave en `data-testid="api-key"`. La clave se lee de la variable `E2E_API_KEY`, que pone la verificación; nunca va escrita en la prueba.
- Una clave equivocada muestra «Clave inválida».

## Configuración nueva

| Variable | Por omisión | Para qué |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | Con `production` se aplican las reglas de compliance |
| `API_KEYS` | vacía | Clientes y claves (secreto) |
| `RATE_LIMIT_PER_MINUTE` | `30` | Peticiones por cliente por minuto |

`product/.env.example` agrega estas variables. `README.md` explica cómo crear una clave, cómo probar con la clave en la página y qué permisos necesita el token de Cloudflare.

## Reglas

- Todo lo de `spec/01-architecture.md`, `spec/02-observability.md` y `spec/03-costs.md` sigue funcionando, ahora con clave.
- No se agregan librerías nuevas a la aplicación.

## Cómo se comprueba

- `verification unit`, `contract`, `qa`, `e2e` y `evaluate`, como antes, ahora con clave.
- Una persona aprueba la publicación. Después, `scripts/publish.py` crea el repositorio privado en GitHub y hace el push.
- `uv run python -m verification production <url>`: la prueba de humo contra Render.
