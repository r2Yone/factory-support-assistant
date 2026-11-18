# Observabilidad: ¿qué pasó con la petición X?

Parte del producto de `spec/01-architecture.md` y le agrega lo necesario para responder, con datos, qué pasó con cualquier petición, y para medir qué tan bien resuelve la mesa de ayuda en primer nivel.

## Lo que debe hacer

1. **Un id por petición.** Si el cliente manda el encabezado `X-Request-ID` y es seguro (de 1 a 128 caracteres `A-Z a-z 0-9 . _ : -`), se usa ese valor; si no, se genera un UUID. Toda respuesta lo devuelve en `X-Request-ID`, y `POST /ask` también en el cuerpo, como `request_id`. Es el **folio** que la persona da a soporte.
2. **Cómo terminó cada pregunta.** `POST /ask` agrega `outcome` a su respuesta, con uno de estos valores:
   - `solved`: se entregó la solución de un artículo de la base de conocimiento.
   - `escalated`: se transfirió con un equipo humano.
   - `needs_detail`: se pidió a la persona que describiera mejor su problema.
   - `incomplete`: el agente llegó al tope de vueltas sin responder.
3. **Log en JSON, una línea por evento**, en la salida estándar. Cada línea lleva `ts` (ISO 8601 en UTC), `service`, `event` y `request_id`. Eventos:
   - `request`: `method`, `path`, `status` y `latency_ms`, uno por cada petición.
   - `agent_run`: `question_chars`, `history_messages`, `steps`, `tools`, `outcome`, `team`, `article_id`, `input_tokens`, `output_tokens` y `stopped`. Con `LOG_CONVERSATION_TEXT=true` agrega también `question` (la pregunta tal como la escribió la persona) y `answer` (la respuesta que se le dio).
     - `article_id`: el id del artículo (`KB-####`) cuya solución se entregó; `null` si el `outcome` no es `solved`.
   - `audit`: uno por cada herramienta que ejecuta el agente, con `action: "tool_call"` y `tool`, más:
     - `search_knowledge_base`: `problem_chars`, `category` y `article_ids` (los ids encontrados; vacío si no hubo solución). Así se ven los huecos de la base de conocimiento por categoría.
     - `escalate_to_human`: `category` y `team`.
   - `error`: si algo truena, con el tipo de error (no el mensaje). La respuesta es `500` con `{"detail": "internal error", "request_id": ...}`.

   **Texto de la conversación en el log.** La pregunta y la respuesta solo se registran en `agent_run` y solo con `LOG_CONVERSATION_TEXT=true` (el valor por omisión), para revisar qué preguntó la persona y qué se le contestó. Con `false`, `agent_run` no lleva `question` ni `answer`, y el resto del log no cambia. En cualquier caso, **nunca** se registra el texto del historial, ni el texto del problema en `audit`, ni en `request` o `error`.

   Advertencia: las personas describen sus problemas con sus palabras y pueden incluir datos personales. Antes de producción hay que decidir si `LOG_CONVERSATION_TEXT` se queda encendida y quién puede leer el log.
4. **`GET /metrics`** de este proceso:
   `{"pid", "requests", "error_rate", "latency_ms": {"p50", "p95"}, "tokens": {"input", "output"}, "outcomes": {"solved", "escalated", "needs_detail", "incomplete"}, "self_service_rate", "slo": {"p95_ms_target", "met"}}`.
   - `error_rate`: fracción de peticiones con código `5xx`.
   - `self_service_rate`: `solved` entre el total de preguntas respondidas por `POST /ask` (`0` si no hay ninguna). Es el indicador de la mesa de primer nivel: cuántos problemas se resuelven sin un humano.
   - `met` es `true` si el p95 está por debajo de `SLO_P95_MS`.
   - Solo se guardan las últimas 1000 latencias, para que la memoria no crezca sin límite.
5. **Trazas en LangSmith (opcional).** Con `LANGSMITH_TRACING=true` y `LANGSMITH_API_KEY`, cada corrida del agente, cada llamada al modelo y cada herramienta quedan como trazas (`@traceable`), con el `request_id` en sus metadatos. Si `HIDE_INPUTS`/`HIDE_OUTPUTS` valen `true`, no se mandan entradas ni salidas. Sin la clave, el producto funciona igual y no intenta conectarse.
6. **La página web** muestra el `request_id` de cada respuesta con el texto `request_id: <id>`. Si hubo transferencia, el aviso `data-testid="escalation"` también lo muestra como folio: «Te transferimos con <team>. Folio: <request_id>», para que el agente humano encuentre la conversación en el log.

## Configuración

| Variable | Por omisión | Para qué |
| --- | --- | --- |
| `SERVICE_NAME` | `support-assistant` | Campo `service` del log |
| `SLO_P95_MS` | `2000` | Meta de latencia p95 en milisegundos |
| `LOG_CONVERSATION_TEXT` | `true` | Registrar la pregunta y la respuesta en el evento `agent_run` (`true` o `false`) |
| `LANGSMITH_TRACING` | `false` | Enciende las trazas |
| `HIDE_INPUTS` / `HIDE_OUTPUTS` | `true` | No mandar a LangSmith el texto de preguntas ni respuestas (valor seguro por omisión) |

La clave `LANGSMITH_API_KEY` se lee del entorno y nunca se escribe en el log ni en el código.

## Reglas

- Cada línea del log se escribe en cuanto ocurre el evento (sin esperar a llenar un búfer), para que se pueda seguir en vivo.
- La hora se obtiene a través de un reloj inyectado (no `datetime.now()` directo), para que las pruebas sean deterministas. El log, la latencia y las métricas usan ese reloj.
- `create_app()` recibe también el reloj, las métricas, el destino del log y el generador de ids, para que las pruebas inyecten los suyos.
- Se agrega `langsmith` a `requirements.txt`.
- El producto tiene `README.md` (qué es, cómo correrlo, sus variables y cómo buscar una petición por su folio en el log) y `doc/` con la arquitectura y los ADR.
- Todo lo de `spec/01-architecture.md` sigue funcionando.

## Cómo se comprueba

- `uv run python -m verification unit`: pruebas del producto, con cobertura de 80 % o más.
- `uv run python -m verification contract`: el contrato de la arquitectura y el de la observabilidad.
- `uv run python -m verification qa`: el estilo de QA.md (pylint, 88 columnas, sin emojis, documentos en su lugar).
- `qa-style` revisa lo que un script no ve y escribe `output/qa-review.md`, que empieza con `APROBADO` o `CAMBIOS`.
