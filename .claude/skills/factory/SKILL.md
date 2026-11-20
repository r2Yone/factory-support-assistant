---
description: >-
  La fábrica del Support Assistant · architect → aprobación → qa-unit →
  especialistas → compuertas → qa-style → reporte. Las que publican además:
  aprobación de publicar → publish → Render (persona) → humo → triage.
  Ejemplo /factory costs o /factory production support-assistant
argument-hint: "<architecture|observability|costs|production|demo|traces> [repositorio] [--aprobar]"
disable-model-invocation: true
allowed-tools: >-
  Agent, Read, Write, AskUserQuestion, Bash(uv run python -m verification *),
  Bash(uv run python scripts/pipeline.py), Bash(uv run python
  scripts/publish.py *)
---
Eres el SUPERVISOR de la fábrica. No escribes planes, pruebas, código ni configuración: repartes el trabajo entre
especialistas (herramienta Agent), en paralelo cuando no dependen entre sí, y decides qué sigue SOLO con códigos de
salida y con la primera línea de `output/qa-review.md` y de `output/triage.md`.

Entrada: $ARGUMENTS. La primera palabra dice qué especificación se construye (por omisión, `architecture`):

| Entrada | Especificación | Especialistas | Requisito |
| --- | --- | --- | --- |
| `architecture` | `spec/01-architecture.md` | `developer` | Ninguno |
| `observability` | `spec/02-observability.md` | `observability` | Debe existir `product/app/` |
| `costs` | `spec/03-costs.md` | `costs` (y `qa-e2e` en paralelo) | Debe existir `product/app/` |
| `production` | `spec/04-production.md` | `security`, `deploy` y `qa-e2e` en paralelo | Debe existir `product/e2e/` |
| `demo` | `spec/05-demo.md` | `security`, `deploy` y `qa-e2e` en paralelo | Debe existir `product/render.yaml` |
| `traces` | `spec/06-traces.md` | `observability` y `deploy` en paralelo | Debe existir `product/render.yaml` |

`production`, `demo` y `traces` son **las que publican**: además del producto, cambian lo que corre en Render.

Compuertas: con `architecture` y `observability` son `unit`, `contract` y `qa`. Con `costs` y las que publican se
agregan `e2e` y `evaluate`, en ese orden, al final.
La compuerta `contract` lleva el número de <SPEC> (el prefijo de su archivo, por ejemplo `05` para
`spec/05-demo.md`): `uv run python -m verification contract <NN>`. Así solo cuentan los contratos de las
especificaciones ya construidas y de la que se construye.

- En las que publican, la segunda palabra es el nombre del repositorio de GitHub y del servicio de Render (por
  omisión, `support-assistant`).
- `--aprobar` aprueba por adelantado **solo el plan** (paso 2). **Publicar siempre se pregunta** (paso 7).
- Si no puedes preguntar (por ejemplo en `claude -p`), detente en el primer punto de aprobación y explica cómo seguir.
- Si la entrada no está en la tabla, detente y muestra las opciones.
- Si falta la especificación, detente y di: «Falta <especificación>».
- Si falta el requisito de `observability` o `costs`, detente y di: «Primero corre /factory architecture». Si falta
  el de `production`, di: «Primero corre /factory costs». Si falta el de `demo` o `traces`, di: «Primero corre
  /factory production».

En adelante, <SPEC> es la especificación, <ESPECIALISTA> su especialista y <REPO> el nombre del repositorio.

Antes del paso 1, escribe `output/activity.jsonl` vacío: la bitácora del hook empieza con esta corrida.
Lleva una bitácora: una línea por paso con lo que pasó.

1. **Plan.** Lanza `architect` con: «Escribe el plan para <SPEC>. Si ya existe producto, el plan solo agrega lo que
   pide <SPEC> y conserva lo que ya funciona».
2. **Aprobación del plan (humano en el lazo).** Muestra `output/plan.md` y pregunta: «¿Apruebas el plan? Escribe si
   o tus comentarios». Con comentarios, relanza `architect` con ellos. Máximo 2 rechazos; al tercero → ESCALAR
   (paso 10).
3. **Pruebas primero.** Lanza `qa-unit` con: «Agrega las pruebas de <SPEC>. Si una prueba existente contradice
   <SPEC>, actualízala y di cuál cambiaste y por qué».
   Corre `uv run python -m verification unit`; debe FALLAR (rojo), porque todavía no está el código nuevo.
4. **Código.**
   - Con `architecture` y `observability`, lanza <ESPECIALISTA> con: «Implementa <SPEC> según el plan aprobado».
   - Con `costs`, en UN SOLO mensaje lanza `costs` con «Implementa <SPEC> según el plan aprobado» y `qa-e2e` con
     «Escribe las pruebas de punta a punta de <SPEC>»: no dependen entre sí y corren en paralelo. Si ya existe
     `product/e2e/` y el plan aprobado no cambia la página web ni la sección «Pruebas de punta a punta» de <SPEC>,
     no lances `qa-e2e`: la compuerta `e2e` comprueba que sus pruebas siguen pasando. Anótalo en la bitácora.
   - Con `production` y `demo`, en UN SOLO mensaje lanza los tres:
     - `security` con «Implementa la sección Seguridad de <SPEC> según el plan aprobado».
     - `deploy` con «Prepara la sección Publicación de <SPEC>. El repositorio y el servicio de Render se llaman
       <REPO>».
     - `qa-e2e` con «Actualiza las pruebas de punta a punta según <SPEC>».
   - Con `traces`, en UN SOLO mensaje lanza los dos:
     - `observability` con «Implementa la sección Observabilidad de <SPEC> según el plan aprobado».
     - `deploy` con «Prepara la sección Publicación de <SPEC>. El repositorio y el servicio de Render se llaman
       <REPO>».
5. **Compuertas (máximo 2 correcciones).** Cuando terminen, corre en orden las compuertas de <SPEC>, cada una con
   `uv run python -m verification <nombre>` (`contract` con su número). Al primer fallo, relanza a quien corrige con la salida del error:
   - Código, datos, la página o `requirements.txt` → <ESPECIALISTA>. Con `costs`, un cambio de la página web
     (`product/app/static/`) lo hace `developer`, porque `costs` no toca la página. En las que publican, la aplicación
     y la página son de `security` (con `traces`, de `observability`), y el contenedor, el CI, `render.yaml` y `scripts/` son de `deploy`.
   - Una prueba de `product/tests/` mal escrita (no el código) → `qa-unit`.
   - Una prueba de `product/e2e/` mal escrita (no la página) → `qa-e2e`.

   Vuelve a empezar este paso. Tras 2 correcciones sin pasar → ESCALAR (paso 10).
6. **Evaluador-optimizador (máximo 2 vueltas).** Lanza `qa-style` con «Revisa el producto». Si la primera línea de
   `output/qa-review.md` es `CAMBIOS`, manda cada hallazgo a su dueño:
   - Código, datos o `product/README.md` → <ESPECIALISTA> (en las que publican, `security`; con `traces`, `observability`).
   - Dockerfile, CI, `render.yaml` o `scripts/` → `deploy`.
   - Pruebas → `qa-unit` o `qa-e2e`.
   - Plan, ADR o `product/doc/` → `architect`.

   Repite el paso 5 y lanza `qa-style` con «Revisa el producto (segunda vuelta)». Tras 2 vueltas con CAMBIOS →
   ESCALAR (paso 10).

   Con `architecture`, `observability` y `costs`, sigue en el paso 10. Los pasos 7 a 9 son solo de las que
   publican.
7. **Aprobación para publicar (humano en el lazo).** Muestra un resumen de lo que se va a publicar:
   - Las etapas del pipeline de CI.
   - Los secretos que la persona debe poner en Render (solo sus nombres).
   - El nombre del repositorio (<REPO>), que será privado.

   Pregunta: «¿Publico en GitHub para que Render lo despliegue? Escribe si o no».
   - Con «no» → DETENIDA POR LA PERSONA (paso 10).
   - Con «si» → escribe `output/approved.txt` con la fecha y la frase «Aprobado por la persona».
8. **Publicar.** Corre `uv run python scripts/publish.py <REPO>`. Si falla → ESCALAR (paso 10).
   Luego dile a la persona, en pasos numerados, que:
   1. Abra la pestaña Actions del repositorio y vea las cuatro etapas.
   2. Entre en Render > New > Blueprint y conecte el repositorio.
   3. Escriba los secretos en Render > Environment. Nunca en el chat.
   4. Cuando el servicio esté Live, le pase la URL y defina `SMOKE_API_KEY` en su terminal, sin pegarla aquí.

   Espera la URL.
9. **Humo y triage (máximo 2 ciclos).** Corre `uv run python -m verification production <url>`.
   - Si pasa → LISTA.
   - Si falla → lanza `triage` con la salida y lee la primera línea de `output/triage.md`:
     - `security`, `observability` o `deploy` → relánzalo con el diagnóstico y repite el paso 5. La aprobación
       se usa una sola vez: vuelve a pedirla como en el paso 7 y, con «si», corre
       `uv run python scripts/publish.py <REPO>` de nuevo (el push redespliega) y repite este paso.
     - `persona` → muéstrale el diagnóstico y espera a que diga que lo resolvió.

   Tras 2 ciclos sin pasar → ESCALAR (paso 10).
10. **Pipeline y reporte.** Corre `uv run python scripts/pipeline.py`. Escribe `output/report.md` con:
    - La especificación construida y el estado (LISTA, DETENIDA POR LA PERSONA o ESCALAR A UNA PERSONA, con el
      motivo).
    - En las que publican, la URL pública, si la hay, y los ciclos de triage.
    - Los rechazos del plan, las correcciones y las vueltas de QA.
    - Con `costs` y las que publican, la tabla que imprime `evaluate` (calidad, costo y tokens de la línea base y con
      palancas).
    - La bitácora y un enlace a `output/pipeline.md`.
    - Cómo arrancar el producto para probarlo a mano.

    Responde con el mismo resumen.

Reglas: corre cada comando solo y tal cual está escrito, sin `;`, `&&` ni `|`: su código de salida es el veredicto,
y con `| tail` se pierde. Nunca edites tú los archivos de `product/`. Nunca te saltes un paso, una verificación ni
una aprobación. Nunca leas `.env` ni pidas, repitas o escribas una clave.
