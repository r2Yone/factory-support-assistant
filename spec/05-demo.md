# Demo pública: la página sin clave, con límites

Parte del producto de `spec/01-architecture.md` a `spec/04-production.md`. Es para una demostración: cualquiera con la URL puede usar la página sin escribir una clave. Para que nadie gaste de más, las preguntas sin clave tienen un límite por dirección IP y un **tope de gasto diario**. Las integraciones siguen entrando con su `X-API-Key`, como antes.

## Lo que debe hacer

### Seguridad (los hace `security`)

1. **Modo demo.** Con `PUBLIC_PAGE=true`, `POST /ask` acepta peticiones **sin** el encabezado `X-API-Key`:
   - Se atienden como el cliente `public`: así aparecen en el log (`client`), en la auditoría y en la traza.
   - Una petición **con** `X-API-Key` se valida como antes: con una clave inválida responde `401`; con una válida es de su cliente, con su propio límite, y no cuenta para el tope de la demo.
   - `GET /metrics` sigue exigiendo clave.
   - Con `PUBLIC_PAGE=false` (por omisión), todo es como en `spec/04-production.md`: sin clave, `401`.
2. **Límite por dirección IP.** Las peticiones de `public` se limitan a `PUBLIC_RATE_LIMIT_PER_MINUTE` por minuto **por dirección IP**, con la misma respuesta que el límite por cliente: `429 {"detail": "rate limit exceeded", "request_id": ...}` y `Retry-After`.
   - La IP es la de la conexión. Con `TRUST_PROXY=true` (en Render, que pone un proxy delante), es la **última** entrada de `X-Forwarded-For`, la que agrega el proxy; nunca la primera, que la puede escribir cualquiera.
   - **La IP nunca se escribe** en el log, en la auditoría ni en la traza: es un dato personal.
3. **Tope de gasto diario.** El producto suma el `cost_usd` de las peticiones de `public` del día (en UTC, con el reloj inyectado).
   - Antes de llamar al modelo, si lo gastado hoy llega o pasa `DAILY_BUDGET_USD`, responde `503 {"detail": "daily budget exhausted", "request_id": ...}` sin llamar al modelo. Al día siguiente vuelve a responder.
   - El evento `request` del log registra el `503`, y un evento `budget_exhausted` (con `spent_usd` y `budget_usd`) se escribe **una sola vez por día**, la primera vez que se alcanza el tope.
   - La suma vive en la memoria del proceso: si el servicio se reinicia (en Render gratis se duerme tras 15 minutos sin uso), empieza en cero. Para una demo es aceptable; se documenta en `doc/compliance-checklist.md`, en «Decisiones aceptadas».
   - `/metrics` agrega `public_cost_today_usd` y `daily_budget_usd`.
4. **Configuración válida.** Con `PUBLIC_PAGE=true`, el producto **no arranca** si `DAILY_BUDGET_USD` no es mayor que 0 o `PUBLIC_RATE_LIMIT_PER_MINUTE` no es mayor que 0. En producción siguen las reglas de `spec/04-production.md` (también hace falta `API_KEYS`, para `/metrics` y la prueba de humo).
5. **La página web ya no pide clave.** Se quita el campo `data-testid="api-key"`; la página nunca manda `X-API-Key` ni guarda nada en `sessionStorage`.
   - Con `401` muestra «Esta página necesita el modo demo (PUBLIC_PAGE=true)».
   - Con `429`, «Demasiadas preguntas; espera N segundos».
   - Con `503` por el tope, «La demo alcanzó su límite de hoy. Vuelve mañana».

### Publicación (la hace `deploy`)

6. **Render.** `render.yaml` agrega los valores fijos `PUBLIC_PAGE=true`, `TRUST_PROXY=true`, `PUBLIC_RATE_LIMIT_PER_MINUTE=5` y `DAILY_BUDGET_USD=0.50`. Lo demás no cambia.
   - El trabajo `e2e` del CI arranca el producto con `PUBLIC_PAGE=true`, igual que la verificación de la fábrica.
7. **Prueba de humo.** `scripts/smoke.py` cambia su segunda comprobación: en lugar de «`/ask` sin clave responde `401`», comprueba «`/ask` con una clave equivocada responde `401`». Así sirve con y sin modo demo.

## Pruebas de punta a punta (las actualiza `qa-e2e`)

- La verificación arranca el producto con `PUBLIC_PAGE=true`. Las pruebas ya no escriben una clave: se quita el uso de `E2E_API_KEY` y la prueba de la clave equivocada.
- Se agrega: la página no tiene campo de clave y responde una pregunta sin ella.

## Configuración nueva

| Variable | Por omisión | Para qué |
| --- | --- | --- |
| `PUBLIC_PAGE` | `false` | Modo demo: `/ask` sin clave, con límites |
| `PUBLIC_RATE_LIMIT_PER_MINUTE` | `5` | Preguntas sin clave por IP por minuto |
| `DAILY_BUDGET_USD` | `0.50` | Tope de gasto diario de las preguntas sin clave |
| `TRUST_PROXY` | `false` | Leer la IP de `X-Forwarded-For` (solo detrás de un proxy, como Render) |

`product/.env.example` agrega estas variables. `README.md` explica el modo demo, sus límites y cómo encenderlo en el equipo propio (`PUBLIC_PAGE=true` en `product/.env`).

## Reglas

- Todo lo de las especificaciones anteriores sigue funcionando.
- No se agregan librerías nuevas.

## Cómo se comprueba

- `verification unit`, `contract`, `qa`, `e2e` y `evaluate`, como antes.
- Una persona aprueba la publicación. Después, `scripts/publish.py` hace el push y Render redespliega cuando el CI pasa.
- `uv run python -m verification production <url>`: la prueba de humo contra Render.
