# Página: una mesa de ayuda moderna

Parte del producto de `spec/01-architecture.md` a `spec/06-traces.md`. Rediseña la página web para que se vea moderna y cuidada, cambia su texto de bienvenida y cierra tres pendientes menores. La API y su comportamiento no cambian.

## Lo que debe hacer

### Página (la hace `developer`)

1. **Texto de bienvenida.** El texto que hoy explica la página («Cuéntanos qué te pasa con tus palabras…») se reemplaza por este, exacto:
   > Bienvenido al sitio de soporte con IA. Describe tu problema y buscaremos una solución, si no la encontramos, te transferimos con el equipo que puede ayudarte.
2. **Diseño de conversación.** La página se ve como un chat de soporte:
   - Un encabezado con el nombre «Support Assistant», un ícono sencillo (SVG en línea) y el texto de bienvenida.
   - Cada mensaje en una burbuja: los de la persona a la derecha y los del asistente a la izquierda, con colores distintos.
   - La respuesta con solución destaca el id del artículo (por ejemplo `KB-0003`) como una etiqueta.
   - El aviso de transferencia (`data-testid="escalation"`) es una tarjeta distinta, con el equipo y el folio bien visibles.
   - El folio (`request_id`) de cada respuesta se ve pequeño y discreto debajo de ella.
   - El campo de pregunta y el botón Enviar quedan fijos abajo, como en una aplicación de mensajería.
3. **Ejemplos para empezar.** Mientras no hay conversación, se muestran tres ejemplos que se pueden pulsar: «No me puedo conectar a la VPN desde mi casa», «Olvidé mi contraseña» y «Mi teclado tiene teclas que no funcionan». Al pulsar uno, su texto se escribe en el campo de pregunta (`data-testid="example"` en cada uno).
4. **Mientras espera.** Al enviar, el botón se desactiva y aparece un indicador «Buscando una solución…» en lugar de la respuesta; al llegar la respuesta o un error, desaparece. **Enter** envía y **Shift+Enter** hace un salto de línea.
5. **Moderna y accesible.**
   - Colores, tipografía, espaciado, bordes redondeados y sombras definidos como variables CSS (`--color-...`), con una paleta sobria (no más de un color de acento).
   - **Modo oscuro** automático con `prefers-color-scheme: dark`.
   - Se ve bien en un celular de 360 px de ancho y en una pantalla grande (el chat no pasa de unos 760 px de ancho, centrado).
   - Contraste de texto de al menos 4.5:1 (WCAG AA), foco visible al navegar con teclado, y los controles con `aria-label` cuando no tienen texto.
   - Respeta `prefers-reduced-motion`: sin animaciones si la persona lo pide.
6. **Sin dependencias externas.** Todo vive en `app/static/index.html`, con su CSS y su JavaScript en el mismo archivo: sin frameworks, sin fuentes ni scripts de otros sitios y sin paso de compilación. La tipografía es la del sistema (`system-ui`). Así la página carga rápido, funciona sin internet y no avisa a terceros de quién la visita.
7. **Lo que no cambia.**
   - Los `data-testid` existentes: `question`, `send`, `answer` y `escalation`.
   - Los mensajes de error de `spec/05-demo.md` (401, 429 y 503) y el de una pregunta vacía, ahora con el estilo nuevo.
   - La página nunca manda `X-API-Key` ni guarda nada en el navegador.

### Pendientes menores (los hace `developer`)

8. **Código muerto.** Se elimina:
   - `build_model()` de `app/llm.py`: nadie la usa desde que `build_models()` de `app/gateway.py` crea los modelos (`spec/03-costs.md`).
   - `build_tracer()` de `app/tracing.py`: el producto usa `build_tracing()` desde `spec/06-traces.md`, y solo la llamaban las pruebas. Las pruebas que la usan (`tests/test_observability_config.py` y `tests/test_production.py`) pasan a usar `build_tracing()` y su campo `tracer`, sin perder lo que comprueban.
9. **`README.md` empieza con una sección «Requisitos y primeros pasos»** para alguien que descarga el repositorio y tiene sus propias cuentas y claves:
   - **Requisitos:** Git y **Python 3.12** (o Docker, en lugar de Python).
   - **Cuentas**, en una tabla con si es obligatoria y qué se necesita de cada una: Cloudflare solo para el modelo real (Account ID, un AI Gateway creado cuyo nombre va en `CF_GATEWAY_ID`, y un token con los permisos **Workers AI: Read** y **AI Gateway: Run**); LangSmith opcional (una API key, para trazas); Render opcional (solo para publicar).
   - **Pasos** en orden, con los comandos para Windows (PowerShell) y para macOS/Linux: clonar, crear y activar un entorno virtual, `pip install -r requirements.txt`, copiar `.env.example` a `.env`, completar los valores, `uvicorn app.main:app --port 8000` y abrir `http://127.0.0.1:8000`.
   - **El `.env` mínimo** para el modelo real con la página de demo (`MODEL_PROVIDER`, las tres `CF_*`, `API_KEYS` y `PUBLIC_PAGE=true`), con valores de ejemplo como `<tu-account-id>`, nunca reales.
   - **Probarlo sin ninguna cuenta:** solo `PUBLIC_PAGE=true`; responde el modelo simulado.
   - **Con Docker:** `docker build -t support-assistant .` y `docker run -p 8000:8000 --env-file .env support-assistant` (el `.env` nunca entra en la imagen).
   - **Para correr las pruebas:** `pip install pytest-playwright pylint` y `python -m playwright install chromium`, que no van en `requirements.txt` porque la imagen de Docker no las necesita; luego `pytest tests` y, con el producto corriendo con `PUBLIC_PAGE=true`, `pytest e2e --base-url http://127.0.0.1:8000`.

   El resto del README se conserva; si algo de él repite esta sección, se deja una sola versión.

## Pruebas de punta a punta (las actualiza `qa-e2e`)

- Las pruebas existentes siguen pasando con el diseño nuevo (buscan por `data-testid`, no por estilos).
- Se agregan: el texto de bienvenida se ve al abrir la página, y pulsar un ejemplo escribe su texto en el campo de pregunta.
- Máximo 7 pruebas en total.

## Reglas

- No cambia la API, ni el agente, ni la configuración.
- No se agregan librerías nuevas.
- Todo lo de las especificaciones anteriores sigue funcionando.

## Cómo se comprueba

- `verification unit`, `contract`, `qa`, `e2e` y `evaluate`, como antes.
- Una persona revisa la página en su navegador antes de aprobar la publicación.
- Una persona aprueba la publicación. Después, `scripts/publish.py` hace el push y Render redespliega cuando el CI pasa.
- `uv run python -m verification production <url>`: la prueba de humo contra Render.
