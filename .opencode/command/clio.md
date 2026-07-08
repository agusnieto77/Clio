---
description: "Invoca a Clio para procesar una subcarpeta de Fuentes/. Clio coordina las etapas OCR, analisis cuantitativo y redaccion, manteniendo log persistente y reanudable. Uso: /clio <subcarpeta>."
agent: clio
---

Procesa la subcarpeta indicada siguiendo el protocolo de Clio en `.opencode/skill/clio/SKILL.md`.

Subcarpeta: `$ARGUMENTS`

Pasos a ejecutar (Clio):
1. Validar que `$ARGUMENTS` es una subcarpeta de `Fuentes/`.
2. Inicializar el log con `python harness/tools/estado.py "$ARGUMENTS" init`.
3. Reportar los modelos principal y de respaldo de cada subagente leyendo `harness/modelos.json`.
4. Decidir punto de reanudacion segun el estado del filesystem.
5. Delegar en orden a `ocr-historico`, `analista-cuantitativo`, `redactor-informes`, validando entre etapas con `python harness/tools/validar.py`.
6. Detener el flujo y registrar si una validacion falla.
7. Cerrar el log con el resumen final.

No ejecutes tareas tecnicas vos misma: coordinas y registras.
