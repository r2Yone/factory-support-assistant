# Arquitectura simple y lista para crecer

Producto: **Support Assistant**, el primer nivel de la mesa de ayuda de la empresa. Lo usan los empleados desde una página web.

Funciona como una mesa de ayuda real: la persona **describe su problema con sus palabras** (no conoce los artículos), el asistente lo clasifica, busca una solución en la base de conocimiento y, si no la encuentra, **la transfiere con el equipo humano** que atiende esa categoría.

## Lo que debe hacer

1. Una API web (FastAPI) **sin estado**: no guarda nada entre peticiones. Escalar es correr más copias.
2. Un **solo agente** con dos herramientas sobre `data/knowledge_base.json`:
   - `search_knowledge_base(problem)`: clasifica el problema en una categoría y busca artículos que lo resuelvan.
   - `escalate_to_human(category)`: indica qué equipo humano atiende esa categoría. En esta versión no crea tickets ni guarda nada: solo dice a quién se transfiere.
3. El flujo esperado:
   - Si hay un artículo vigente que resuelve el problema, el asistente da su solución y dice de qué artículo viene (id y título).
   - Si el problema se pudo clasificar pero no hay un artículo vigente que lo resuelva, el asistente transfiere con el equipo de esa categoría.
   - Si la persona pide hablar con una persona, el asistente la transfiere con la mesa general sin buscar.
   - Si el mensaje no describe un problema reconocible, el asistente pide más detalle y recuerda que puede pedir hablar con una persona.
4. **Un artículo `obsoleto` nunca se ofrece como solución**: es como si no existiera para la búsqueda.
5. El agente trabaja en un **bucle con tope**: en cada vuelta el modelo pide una herramienta o responde. Si llega al tope sin responder, contesta exactamente: `No pude completar la respuesta. Intenta con una pregunta más concreta.`
6. El modelo se usa a través de una **interfaz** (`complete(messages)`), para poder cambiarlo sin tocar el agente. Por ahora solo existe el **modelo simulado**.
7. Una **página web** para los empleados.

## Base de conocimiento (`data/knowledge_base.json`)

Un objeto con tres partes:

- `general_team`: el equipo que atiende lo que no tiene categoría (por ejemplo, cuando la persona pide hablar con alguien).
- `categories`: cada una con `name`, `team` (el equipo humano que la atiende) y `keywords` (palabras que la identifican).
- `articles`: cada uno con `id`, `title`, `category`, `keywords`, `solution`, `status` (`vigente` u `obsoleto`) y `updated`.

## Búsqueda (`search_knowledge_base`)

Determinista y sin red:

1. **Normalizar**: el problema y las palabras clave se comparan en minúsculas y sin acentos (`Conexión` = `conexion`). Las palabras del problema son las secuencias de letras y dígitos (`Wi-Fi` da `wi` y `fi`).
2. **Clasificar**: la categoría es la que tiene más palabras clave presentes en el problema. En empate gana la primera del archivo. Si ninguna coincide, la categoría es la del mejor artículo encontrado; si tampoco hay artículos, es `null`.
3. **Buscar**: el puntaje de un artículo es cuántas de sus palabras clave aparecen en el problema. Se devuelven los artículos **vigentes** con puntaje de al menos `KB_MIN_SCORE`, de mayor a menor puntaje (en empate, en el orden del archivo), y como máximo `KB_MAX_RESULTS`.
4. **Resultado**: un objeto JSON en texto, `{"category": "<nombre>" o null, "articles": [{"id", "title", "category", "solution", "updated"}]}`.

`escalate_to_human(category)` devuelve en texto `{"category": "<nombre>", "team": "<equipo>"}`. Una categoría que no existe, o `General`, se atiende con `general_team`.

## Protocolo entre el agente y el modelo

El modelo responde siempre un único objeto JSON:

- `{"tool": "<nombre>", "args": {...}}` para pedir una herramienta.
- `{"answer": "<respuesta en español>"}` para responder.

El agente agrega el resultado de la herramienta a la conversación como un mensaje `user` que empieza con `Resultado de la herramienta: ` y vuelve a preguntar al modelo.

El agente valida los argumentos antes de ejecutar una herramienta: `problem` es texto no vacío de hasta `MAX_QUESTION_CHARS` caracteres; `category` es texto de 1 a 64 letras, espacios o guiones. Si el modelo responde algo que no es JSON válido, pide una herramienta que no existe o manda argumentos inválidos, el agente no truena: agrega el error a la conversación como resultado de la herramienta y sigue el bucle.

## Modelo simulado (`MODEL_PROVIDER=fake`)

Determinista, sin red ni costo. Decide con reglas sobre el último mensaje, en este orden:

1. Si empieza con `Resultado de la herramienta: `, lee el JSON que sigue:
   - Trae `team` (fue una transferencia) → `{"answer": "Te comunico con <team>."}`
   - Trae `articles` con al menos uno → `{"answer": "Encontré una solución en la base de conocimiento (<id>, <title>): <solution> Si no se resuelve, pide hablar con una persona."}` con el primer artículo.
   - Trae `articles` vacío y `category` con valor → pide `escalate_to_human` con esa categoría.
   - Trae `articles` vacío y `category` en `null` → responde la guía (regla 3).
   - No es JSON (por ejemplo, un error de la herramienta) → pide `escalate_to_human` con la categoría `General`.
2. Si la persona pide hablar con alguien (contiene la palabra `persona`, `humano`, `humana` o `agente`) → pide `escalate_to_human` con la categoría `General`.
3. Si tiene menos de 3 palabras → `{"answer": "Describe tu problema (por ejemplo: «no me puedo conectar a la VPN») y busco una solución. Si prefieres, pide hablar con una persona."}`.
4. Si no → pide `search_knowledge_base` con el mensaje completo como `problem`.

Cuenta tokens de forma aproximada: tokens de entrada = palabras de todos los mensajes; de salida = palabras de su respuesta.

## API

| Método y ruta | Qué hace |
| --- | --- |
| `GET /` | La página web |
| `GET /health` | `{"status": "ok", "pid": <id del proceso>}` |
| `POST /ask` | Cuerpo `{"question": "...", "history": [{"role": "user" o "assistant", "content": "..."}]}`. `history` es opcional |

Respuesta de `POST /ask`: `{"answer", "steps", "tools_used", "escalated", "team", "input_tokens", "output_tokens"}`.

- `escalated` es `true` si el agente ejecutó `escalate_to_human`, y `team` es el equipo al que se transfirió (`null` si no hubo transferencia).
- `question` vacía, solo con espacios o con más de `MAX_QUESTION_CHARS` caracteres → `422`.
- El historial lo manda el cliente. La API no lo guarda.

## Configuración (variables de entorno, con valores por omisión)

| Variable | Por omisión | Para qué |
| --- | --- | --- |
| `MODEL_PROVIDER` | `fake` | Qué modelo usar. Por ahora solo `fake` |
| `AGENT_MAX_STEPS` | `4` | Tope de vueltas del bucle (buscar, transferir y responder caben en 3) |
| `MAX_QUESTION_CHARS` | `2000` | Largo máximo de la pregunta |
| `KB_PATH` | `data/knowledge_base.json` | La base de conocimiento |
| `KB_MIN_SCORE` | `2` | Palabras clave que deben coincidir para ofrecer un artículo |
| `KB_MAX_RESULTS` | `2` | Artículos que devuelve la búsqueda como máximo |

Un valor inválido (por ejemplo `AGENT_MAX_STEPS=0`, `KB_MIN_SCORE=0` o un `KB_PATH` que no existe o no tiene la forma descrita) impide arrancar, con un mensaje claro.

## Página web (`app/static/index.html`)

- Un solo archivo HTML con CSS y JavaScript adentro, sin librerías ni compilación. Se sirve en `GET /`.
- Campo de pregunta `data-testid="question"`, botón `data-testid="send"` y la conversación `data-testid="answer"`.
- El texto de ayuda del campo invita a describir el problema (por ejemplo, «Describe tu problema»).
- Cada respuesta muestra el texto y las herramientas usadas. Si hubo transferencia, muestra un aviso visible `data-testid="escalation"` con el equipo: «Te transferimos con <team>».
- El navegador guarda el historial de la conversación y lo manda en `history`.
- El texto de las respuestas se pinta con `textContent`, **nunca** con `innerHTML`: así una respuesta no puede inyectar código.
- Si la API responde un error, se muestra un mensaje en español.

## Estructura del producto

```
product/
  app/       main.py (expone `app` y `create_app()`), agent.py, llm.py, knowledge_base.py, config.py,
             static/index.html
  data/      knowledge_base.json (copia de spec/knowledge_base.json)
  tests/     pruebas unitarias y escenarios Gherkin (los escribe qa-unit)
  doc/       architecture.md y adr/ (los escribe architect)
  README.md  qué es, cómo correrlo y sus variables
  requirements.txt
```

- `create_app()` recibe sus dependencias (configuración, modelo, base de conocimiento) para que las pruebas inyecten las suyas.
- Solo se usan las librerías de `requirements.txt` de la fábrica: fastapi, uvicorn, pydantic, httpx, pytest, pytest-bdd y pytest-cov.
- No lleva `pyproject.toml`.

## Reglas de QA.md que aplican desde ya

- Nombres de código, pruebas y mensajes de la API en inglés. Comentarios y docstrings en español, con docstrings estilo Sphinx (`:param:`, `:return:`) en clases y funciones públicas.
- Líneas de máximo 88 caracteres. Sin emojis.
- Sin `datetime.now()` directo: si hace falta la hora, se inyecta.
- Pruebas: escenarios Gherkin (pytest-bdd) para el comportamiento y pruebas unitarias para la lógica.
- Cobertura de 80 % o más.
- Decisiones de arquitectura en ADR (`doc/adr/NNNN-titulo.md`).

## Cómo se comprueba

- `uv run python -m verification unit`: las pruebas del producto pasan con cobertura de 80 % o más.
- `uv run python -m verification contract`: las pruebas de contrato de la fábrica pasan contra el producto corriendo.
- `uv run python -m verification qa`: el estilo de QA.md (pylint, 88 columnas, sin emojis, documentos en su lugar).
- `qa-style` revisa lo que un script no ve y escribe `output/qa-review.md`, que empieza con `APROBADO` o `CAMBIOS`.
