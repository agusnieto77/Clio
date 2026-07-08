# Formato del corpus

## Entrada esperada

Cada subcarpeta dentro de `Fuentes/` representa un subcorpus independiente.

- Imágenes sueltas `.jpg` / `.jpeg` en la raíz de la subcarpeta
- Sin necesidad de estructura adicional

## Salida generada por Clio

- `i_procesadas/` — imágenes ya transcritas
- `*.txt` — transcripción plana por imagen
- `*.json` — transcripción estructurada por imagen
- `checklist.json` — estado por imagen (`pendiente`, `procesada`, `error`)
- `metricas/` — resultados cuantitativos
- `informe_preliminar.html` — una sección por imagen, 3 columnas
- `informe_final.md` — informe exploratorio del subcorpus
- `log_clio.md` — bitácora de la corrida

## Convenciones importantes

- La transcripción primaria preserva la ortografía de época.
- Si hay `.txt` y `.json` para una misma imagen, el `.txt` manda.
- `ARCHIVOS_METRICAS_ESPERADOS` vive en `harness/tools/common.py` y es la fuente única.
- `leer_transcripcion()` vive en `harness/tools/common.py` y es el helper único.

## Ejemplos incluidos

Este repo trae:

- `Fuentes/Actas/` ya procesado como referencia para investigadores que quieran entender la estructura completa del workflow.
- `Fuentes/Panfletos/` con imágenes sueltas pendientes para probar una corrida nueva.
