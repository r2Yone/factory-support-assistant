# Fábrica del Support Assistant (Reto)

Los agentes construyen el producto en `product/` a partir de la especificación de `spec/`. Las personas dirigen, aprueban y comprueban: no programan.

- `/factory architecture` construye `spec/01-architecture.md` (architect, qa-unit, developer y qa-style).
- `/factory observability` agrega `spec/02-observability.md` (architect, qa-unit, observability y qa-style).
- `/factory costs` agrega `spec/03-costs.md` (architect, qa-unit, costs y qa-e2e en paralelo, y qa-style).
- `/factory production [repositorio]` agrega `spec/04-production.md` (architect, qa-unit, security, deploy y qa-e2e en paralelo, qa-style), pide aprobación para publicar, publica en GitHub para que Render lo despliegue y corre la prueba de humo (triage si falla).
- `/factory demo [repositorio]` agrega `spec/05-demo.md` (la página sin clave, con límite por IP y tope de gasto diario), con el mismo flujo de publicación que `production`.
- `/factory traces [repositorio]` agrega `spec/06-traces.md` (observability y deploy en paralelo): tokens, costo y etiquetas en LangSmith, y la meta de latencia de 4 segundos. Se publica igual que `production`.
- `/factory page [repositorio]` agrega `spec/07-page.md` (developer y qa-e2e en paralelo): la página rediseñada y el texto de bienvenida nuevo. Se publica igual que `production`, y la persona revisa la página antes de aprobar.
- `scripts/publish.py` borra `output/approved.txt` al publicar: cada publicación necesita su propia aprobación.
- `hooks/permissions.py`: cada agente escribe solo en sus carpetas; nadie lee `.env` y nadie publica sin `output/approved.txt`.
- `hooks/activity_log.py`: bitácora de cada herramienta; `scripts/pipeline.py` dibuja el pipeline.
- `verification/`: el código decide si un paso terminó bien, no el agente.

## Reglas

- El orquestador delega: nunca escribe en `product/` (corrige al agente, no su resultado).
- Todo bucle tiene tope: 2 rechazos del plan, 2 correcciones y 2 vueltas de qa-style; después se escala a una persona.
- Una persona aprueba el plan antes de que se escriba código, y aprueba antes de publicar.
- Nunca leas `.env`.
- Código en inglés; comentarios, docstrings, documentos y mensajes a las personas en español. 
