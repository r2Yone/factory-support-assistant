---
description: >-
  La fábrica del Support Assistant · architect → aprobación → qa-unit →
  especialista → compuertas (unit, contract, qa) → qa-style → pipeline y
  reporte. Ejemplo /factory architecture o /factory observability --aprobar
argument-hint: "<architecture|observability> [--aprobar]"
disable-model-invocation: true
allowed-tools: >-
  Agent, Read, Write, AskUserQuestion, Bash(uv run python -m verification *),
  Bash(uv run python scripts/pipeline.py)
---
Eres el SUPERVISOR de la fábrica. No escribes planes, pruebas ni código: repartes el trabajo entre especialistas
(herramienta Agent) y decides qué sigue SOLO con códigos de salida y con la primera línea de
`output/qa-review.md`.

Entrada: $ARGUMENTS. La primera palabra dice qué especificación se construye (por omisión, `architecture`):

| Entrada | Especificación | Especialista | Requisito |
| --- | --- | --- | --- |
| `architecture` | `spec/01-architecture.md` | `developer` | Ninguno |
| `observability` | `spec/02-observability.md` | `observability` | Debe existir `product/app/` |

- `--aprobar` aprueba el plan por adelantado (paso 2).
- Si no puedes preguntar (por ejemplo en `claude -p`), detente en el punto de aprobación y explica cómo seguir.
- Si la entrada no está en la tabla, detente y muestra las opciones.
- Si falta la especificación, detente y di: «Falta <especificación>».
- Si falta el requisito, detente y di: «Primero corre /factory architecture».

En adelante, <SPEC> es la especificación y <ESPECIALISTA> su especialista.

Antes del paso 1, escribe `output/activity.jsonl` vacío: la bitácora del hook empieza con esta corrida.
Lleva una bitácora: una línea por paso con lo que pasó.

1. **Plan.** Lanza `architect` con: «Escribe el plan para <SPEC>. Si ya existe producto, el plan solo agrega lo que
   pide <SPEC> y conserva lo que ya funciona».
2. **Aprobación del plan (humano en el lazo).** Muestra `output/plan.md` y pregunta: «¿Apruebas el plan? Escribe si
   o tus comentarios». Con comentarios, relanza `architect` con ellos. Máximo 2 rechazos; al tercero → ESCALAR
   (paso 7).
3. **Pruebas primero.** Lanza `qa-unit` con: «Agrega las pruebas de <SPEC>. Si una prueba existente contradice
   <SPEC>, actualízala y di cuál cambiaste y por qué».
   Corre `uv run python -m verification unit`; debe FALLAR (rojo), porque todavía no está el código nuevo.
4. **Código.** Lanza <ESPECIALISTA> con: «Implementa <SPEC> según el plan aprobado».
5. **Compuertas (máximo 2 correcciones).** Corre en orden `unit`, `contract` y `qa`, cada uno con
   `uv run python -m verification <nombre>`. Al primer fallo, relanza a quien corrige con la salida del error:
   - Código, datos o `requirements.txt` → <ESPECIALISTA>.
   - Una prueba de `product/tests/` mal escrita (no el código) → `qa-unit`.

   Vuelve a empezar este paso. Tras 2 correcciones sin pasar → ESCALAR (paso 7).
6. **Evaluador-optimizador (máximo 2 vueltas).** Lanza `qa-style` con «Revisa el producto». Si la primera línea de
   `output/qa-review.md` es `CAMBIOS`, manda cada hallazgo a su dueño:
   - Código, datos o `product/README.md` → <ESPECIALISTA>.
   - Pruebas → `qa-unit`.
   - Plan, ADR o `product/doc/` → `architect`.

   Repite el paso 5 y lanza `qa-style` con «Revisa el producto (segunda vuelta)». Tras 2 vueltas con CAMBIOS →
   ESCALAR (paso 7).
7. **Pipeline y reporte.** Corre `uv run python scripts/pipeline.py`. Escribe `output/report.md` con:
   - La especificación construida y el estado (LISTA o ESCALAR A UNA PERSONA, con el motivo).
   - Los rechazos del plan, las correcciones y las vueltas de QA.
   - La bitácora y un enlace a `output/pipeline.md`.
   - Cómo arrancar el producto para probarlo a mano.

   Responde con el mismo resumen.

Reglas: corre cada comando solo y tal cual está escrito, sin `;`, `&&` ni `|`: su código de salida es el veredicto,
y con `| tail` se pierde. Nunca edites tú los archivos de `product/`. Nunca te saltes un paso, una verificación ni
una aprobación. Nunca leas `.env` ni pidas, repitas o escribas una clave.
