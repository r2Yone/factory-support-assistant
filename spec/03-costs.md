# Costos: abaratar cada respuesta sin empeorarla

Parte del producto de `spec/01-architecture.md` y `spec/02-observability.md`. Agrega el modelo real (Cloudflare Workers AI a través de AI Gateway) y cuatro palancas de costo. Cada palanca se mide: si baja la calidad, no se usa.

## Lo que debe hacer

1. **Modelo real** con `MODEL_PROVIDER=gateway`: llama a `https://gateway.ai.cloudflare.com/v1/{CF_ACCOUNT_ID}/{CF_GATEWAY_ID}/workers-ai/v1/chat/completions` con `Authorization: Bearer {CF_API_TOKEN}` y el cuerpo `{"model", "messages", "max_tokens", "temperature"}`.
   - El primer mensaje es un **prompt de sistema** que explica al modelo su papel (primer nivel de la mesa de ayuda), el protocolo JSON, las dos herramientas y sus argumentos, y estas reglas: buscar en la base de conocimiento antes de responder, responder solo con soluciones que vengan de la base de conocimiento y citar el id del artículo, transferir con `escalate_to_human` cuando la búsqueda no da artículos o la persona pide hablar con alguien, y pedir más detalle si el mensaje no describe un problema. Responder siempre en español.
   - Los tokens se leen de `usage.prompt_tokens` y `usage.completion_tokens`.
   - Si la llamada falla, la API responde `502 {"detail": "model unavailable", "request_id": ...}` y el log registra un evento `error` con el tipo de error. El mensaje de error nunca incluye el token, la cuenta ni el cuerpo de la respuesta del proveedor. Sin reintentos: el costo y la latencia deben ser predecibles.
   - Con `gateway`, faltar cualquiera de las tres variables `CF_*` impide arrancar; el error nombra la variable, nunca su valor.
2. **Palanca 1: enrutamiento.** Una regla en código (no otro modelo) elige el modelo por pregunta:
   - `MODEL_LARGE` si `ROUTING=false`, si la pregunta pasa de `ROUTER_MAX_CHARS` caracteres, o si contiene, como palabra o frase completa y sin distinguir mayúsculas ni acentos, «por qué», «explica», «varios», «todos», «otra vez» o «sigue» (problemas que piden razonar o que se repiten).
   - `MODEL_SMALL` en cualquier otro caso.
   - El motivo queda en `route`: `routing_disabled`, `long_question`, `keyword:<palabra>` o `default`.
3. **Palanca 2: ventana de historial.** Al modelo solo se mandan los últimos `HISTORY_WINDOW` mensajes del historial.
4. **Palanca 3: tope de salida.** `MODEL_MAX_TOKENS` en cada llamada.
5. **Palanca 4: caché de AI Gateway.** Con `CACHE_TTL_SECONDS` mayor que 0 se manda el encabezado `cf-aig-cache-ttl`. Si el gateway responde `cf-aig-cache-status: HIT`, esa llamada cuenta como cacheada y no cuesta. En una mesa de ayuda muchas personas reportan el mismo problema con las mismas palabras: la caché aprovecha esa repetición.
6. **Costo por respuesta.** Con los precios de `data/model_prices.json` (copia de `spec/model_prices.json`, en USD por millón de tokens). `POST /ask` agrega a su respuesta `model`, `route` (el motivo del enrutador), `cached_calls` y `cost_usd`. El evento `agent_run` del log agrega `model`, `route`, `cached_calls` y `cost_usd`.
7. **Costo en las métricas.** `/metrics` agrega:
   - `cost_usd`: el costo acumulado de este proceso.
   - `cost_per_solved_usd`: `cost_usd` entre las preguntas con `outcome` `solved` (`0` si no hay ninguna). Es lo que cuesta resolver un problema sin un humano.
8. **El modelo simulado también tiene precio.** Con `MODEL_PROVIDER=fake` hay dos modelos simulados que se llaman como `MODEL_SMALL` y `MODEL_LARGE`. Responden igual (las reglas de `spec/01-architecture.md`), pero el costo se calcula con el precio de su nombre. Así las palancas se pueden medir sin red y sin gastar cuota.
9. Un modelo configurado que no esté en la tabla de precios impide arrancar.

## Configuración nueva

| Variable | Por omisión | Para qué |
| --- | --- | --- |
| `CF_ACCOUNT_ID`, `CF_GATEWAY_ID`, `CF_API_TOKEN` | vacía, `default`, vacía | Cuenta, gateway y token de Cloudflare (el token es secreto) |
| `MODEL_SMALL` | `@cf/meta/llama-3.1-8b-instruct-fast` | Modelo barato |
| `MODEL_LARGE` | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | Modelo capaz |
| `ROUTING` | `true` | Enrutamiento por pregunta |
| `ROUTER_MAX_CHARS` | `80` | Preguntas más largas van al modelo capaz |
| `HISTORY_WINDOW` | `6` | Mensajes de historial que se mandan |
| `MODEL_MAX_TOKENS` | `300` | Tope de tokens de salida |
| `MODEL_TEMPERATURE` | `0` | Con 0 las evaluaciones son repetibles |
| `CACHE_TTL_SECONDS` | `0` | Caché del gateway (0: apagada) |
| `PRICES_PATH` | `data/model_prices.json` | Precios por modelo |

Se agrega `product/.env.example` con **todas** las variables del producto, sin valores secretos (los secretos van vacíos). `CF_ACCOUNT_ID` y `CF_API_TOKEN` nunca se escriben en el log, en un error ni en el `repr` de la configuración.

## Configuración desde `.env`

La persona configura el producto en un archivo `product/.env` (copia de `.env.example` con sus valores), no con variables escritas en la terminal.

- Al arrancar, el producto lee el archivo que indica `ENV_FILE` con `python-dotenv`. Aplica a **todas** las variables del producto, no solo a las de costos.
- Si una variable existe en el entorno y también en el archivo, **gana la del entorno** (no se sobrescribe).
- `ENV_FILE` vale `.env` por omisión. Una ruta relativa se resuelve contra la raíz de `product/`. Si el archivo no existe, se arranca solo con el entorno, sin error. Con `ENV_FILE=none` no se lee ningún archivo: así corren las verificaciones de la fábrica, aisladas del `.env` de la persona.
- El archivo se lee solo al construir la configuración desde el entorno real (al arrancar con `uvicorn app.main:app`). Las pruebas que pasan su propia configuración a `create_app()` no lo leen.
- `.env` nunca se sube al repositorio ni se copia a otro lado. Su contenido nunca se escribe en el log ni en un error.

| Variable | Por omisión | Para qué |
| --- | --- | --- |
| `ENV_FILE` | `.env` | Archivo de configuración que se lee al arrancar (`none`: ninguno) |

## Robustez con el modelo real

Un modelo real no copia la pregunta tal cual ni respeta siempre los textos de la especificación. El código, no el modelo, garantiza estas reglas:

1. **Buscar con las palabras de la persona.** `search_knowledge_base` busca con la unión de las palabras de la pregunta de esta petición (el campo `question` de `POST /ask`, no el historial) y las del `problem` que manda el modelo. La normalización, la clasificación y el puntaje son los de `spec/01-architecture.md`. Así, si el modelo reformula el problema («recuperar contraseña» en lugar de «olvidé mi contraseña»), no se pierde el artículo.
2. **Mensaje de transferencia fijo.** Cuando `escalate_to_human` se ejecuta sin error, el agente termina el bucle en esa misma vuelta con la respuesta exacta `Te comunico con <team>.`, sin volver a llamar al modelo. El modelo no puede redactar la transferencia ni prometer algo que el sistema no hace (por ejemplo, que alguien se pondrá en contacto).
   - Esto cambia `spec/01-architecture.md`: una transferencia después de buscar toma 2 vueltas, no 3. `tools_used`, `escalated`, `team` y `outcome` no cambian.
   - Además ahorra una llamada al modelo por transferencia, que se refleja en `cost_usd`.
3. **Base de conocimiento actualizada.** `spec/knowledge_base.json` agregó palabras clave a KB-0003 para las formas comunes de pedir una contraseña olvidada. Se vuelve a copiar a `product/data/knowledge_base.json`.
4. Las pruebas unitarias cubren la regla 1 con un modelo de prueba que reformula el problema: el contrato no la puede ver, porque el modelo simulado manda el mensaje completo como `problem`.

## Reglas

- Para el modelo real se usa `httpx`, con el cliente HTTP inyectado: las pruebas nunca llaman a la red (usan `httpx.MockTransport`).
- Se agrega `python-dotenv` a `requirements.txt` (además de las librerías que ya permite `spec/01-architecture.md`).
- Todo lo de `spec/01-architecture.md` y `spec/02-observability.md` sigue funcionando.
- `README.md` explica cómo crear `product/.env` a partir de `.env.example`, cómo usar el modelo real y qué variables de Cloudflare hacen falta.

## Pruebas de punta a punta (las escribe `qa-e2e`)

En `product/e2e/`, con pytest-playwright y el producto corriendo con el modelo simulado:

- Describir un problema con solución, enviarlo y ver la respuesta y su `request_id`.
- Describir un problema sin solución y ver el aviso de transferencia `data-testid="escalation"` con el equipo y el folio.
- Una pregunta vacía muestra un mensaje de error en español.
- Una segunda pregunta mantiene la conversación anterior en pantalla.

## Cómo se comprueba

- `verification unit`, `contract` y `qa`, como antes.
- `uv run python -m verification e2e`: las pruebas de Playwright pasan.
- `uv run python -m verification evaluate`: corre el set de evaluación (`verification/eval_set.json`) dos veces con el modelo simulado, cada pregunta con un historial largo de relleno.
  - **Línea base:** `ROUTING=false` y sin ventana.
  - **Con palancas:** la configuración por omisión.
  - Pasa solo si la calidad no baja y el costo sí baja.
