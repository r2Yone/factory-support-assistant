# Trazas: ver en LangSmith qué hizo el asistente y cuánto costó

Parte del producto de `spec/01-architecture.md` a `spec/05-demo.md`. Las trazas de `spec/02-observability.md` ya muestran los pasos de cada corrida; esta especificación les agrega los tokens, el costo y las etiquetas para filtrar, sin mandar nunca un secreto ni, en producción, el texto de la conversación.

## Lo que debe hacer

### Observabilidad (la hace `observability`)

1. **La llamada al modelo es una traza de tipo `llm`.** `model_complete` se registra con `run_type="llm"` y con los metadatos `ls_provider` (`cloudflare` o `fake`) y `ls_model_name` (el modelo usado). Sus salidas incluyen `usage_metadata` con `input_tokens`, `output_tokens` y `total_tokens`. Así LangSmith muestra los tokens de cada llamada.
2. **Ocultar el texto sin perder el consumo.** Con `HIDE_OUTPUTS=true`, de las salidas solo se manda `usage_metadata`; el texto de la respuesta nunca sale. Con `HIDE_INPUTS=true` no se manda ninguna entrada. Se hace con `hide_outputs`/`hide_inputs` como funciones del `langsmith.Client`, no como `true`/`false`.
3. **La corrida dice cómo terminó.** Al terminar, la traza `agent_run` agrega a sus metadatos: `model`, `route`, `outcome`, `escalated`, `team`, `article_id`, `cached_calls`, `cost_usd`, `steps` y `client` (además del `request_id` que ya lleva). Y lleva las etiquetas `outcome:<outcome>`, `route:<route>` y `model:<modelo>`, para filtrar en LangSmith (por ejemplo, todas las transferencias). Nunca lleva la clave, la IP ni el contenido de `.env`.
4. **Proyecto propio.** Las trazas van al proyecto `LANGSMITH_PROJECT`; si no está definido, a `support-assistant` (nunca a `default`).
5. **Las trazas nunca rompen una respuesta.** Si LangSmith no responde o la clave es inválida, `POST /ask` responde igual y en el mismo tiempo: los envíos van en segundo plano y sus errores no llegan a la persona ni al evento `error` del log.
6. **Meta de latencia realista.** `SLO_P95_MS` vale `4000` por omisión: con el modelo real, cada pregunta hace dos llamadas al modelo y el p95 de 2 segundos no es alcanzable.
7. **`.env.example` completo.** `product/.env.example` lista **todas** las variables de las tablas «Configuración» de `spec/` (salvo `ENV_FILE`, que se lee antes del archivo), con su valor por omisión y los secretos vacíos. Agrega `LANGSMITH_PROJECT=support-assistant`, `SLO_P95_MS=4000` y, comentada, `LANGSMITH_ENDPOINT` para las cuentas de la región europea.

### Publicación (la hace `deploy`)

8. **Render.** `render.yaml` agrega los valores fijos `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT=support-assistant` y `SLO_P95_MS=4000`. Para encender las trazas en producción, la persona agrega `LANGSMITH_API_KEY` en Render > Environment. `HIDE_INPUTS` y `HIDE_OUTPUTS` siguen en `true`.

## Configuración nueva

| Variable | Por omisión | Para qué |
| --- | --- | --- |
| `LANGSMITH_PROJECT` | `support-assistant` | Proyecto de LangSmith donde caen las trazas |
| `SLO_P95_MS` | `4000` | Meta de latencia p95 en milisegundos (antes `2000`) |

`README.md` explica cómo crear la clave de LangSmith, cómo encender las trazas en el equipo propio (con `HIDE_INPUTS=false` y `HIDE_OUTPUTS=false` para ver el texto, solo en desarrollo) y en Render, y qué se ve en cada traza.

## Reglas

- Las pruebas nunca llaman a LangSmith: usan un `traceable` y un cliente sustitutos.
- No se agregan librerías nuevas.
- Todo lo de las especificaciones anteriores sigue funcionando.

## Cómo se comprueba

- `verification unit`, `contract`, `qa`, `e2e` y `evaluate`, como antes. El contrato no ve LangSmith por dentro: comprueba la meta de latencia, `.env.example`, `render.yaml` y que una respuesta no dependa de LangSmith. Lo demás lo cubren las pruebas unitarias.
- Una persona aprueba la publicación. Después, `scripts/publish.py` hace el push y Render redespliega cuando el CI pasa.
- `uv run python -m verification production <url>`: la prueba de humo contra Render.
