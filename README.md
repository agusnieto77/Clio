# Clio

![Release](https://img.shields.io/github/v/release/agusnieto77/Clio?label=release)
![License](https://img.shields.io/github/license/agusnieto77/Clio)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Regression tests](https://img.shields.io/badge/regression-15%20tests-green)

Harness agéntico y determinista para procesar corpus documentales fotografiados: OCR histórico, métricas de minería de texto y reportes exploratorios por subcarpeta.

## Qué hace

Clio trata cada subcarpeta de `Fuentes/` como un subcorpus independiente y ejecuta un flujo de cuatro roles:

1. **Clio** (orquestadora) — valida, decide punto de reanudación y registra.
2. **OCR histórico** — transcribe una imagen a la vez preservando layout y ortografía de época.
3. **Analista cuantitativo** — calcula frecuencia, co-ocurrencia, correlación y TF-IDF.
4. **Redactor de informes** — produce un HTML preliminar por imagen y un informe final Markdown.

El principio rector es **determinismo**: estado en el filesystem, validaciones entre etapas y cero invenciones para tapar faltantes.

## Estado del repo público

Este repo incluye **un solo subcorpus de ejemplo** ya procesado:

- `Fuentes/Actas/` — 10 fojas de una reunión del CORS (22/08/1943), con:
  - `i_procesadas/`
  - transcripciones `.txt` y `.json`
  - `metricas/`
  - `informe_preliminar.html`
  - `informe_final.md`
  - `log_clio.md`

Sirve como corpus de referencia para ver la estructura completa de entrada/salida.

## Requisitos

- Python 3.10+
- Dependencias Python:

```bash
pip install -r harness/tools/requirements.txt
```

- **Opcional pero recomendado:** OpenCode / runtime compatible con `.opencode/` para correr el comando `/clio` como flujo completo.

## Uso rápido

### Opción A — flujo completo con agentes

Desde una sesión OpenCode abierta en este repo:

```text
/clio Fuentes/MiSubcorpus
```

### Opción B — herramientas deterministas manuales

```bash
python harness/tools/estado.py Fuentes/MiSubcorpus init
python harness/tools/validar.py transcripciones Fuentes/MiSubcorpus
python harness/tools/metricas.py Fuentes/MiSubcorpus
python harness/tools/validar.py metricas Fuentes/MiSubcorpus
python harness/tools/informe_preliminar.py Fuentes/MiSubcorpus
python harness/tools/validar.py informes Fuentes/MiSubcorpus
python harness/tools/estado.py Fuentes/MiSubcorpus resumen
```

## Estructura del repo

```text
Clio/
├── opencode.json
├── .opencode/
│   ├── agent/
│   ├── command/
│   └── skill/
├── harness/
│   ├── modelos.json
│   └── tools/
├── tests/
│   └── clio_validation_regression.py
├── docs/
│   ├── instalacion.md
│   ├── uso.md
│   └── formato-del-corpus.md
└── Fuentes/
    └── Actas/
```

## Garantías actuales

- Validación de transcripciones, métricas e informes.
- Reanudación desde filesystem (`checklist.json`, `i_procesadas/`, `metricas/`, informes).
- `correlacion.json` determinista entre procesos Python con distinto `PYTHONHASHSEED`.
- Suite de regresión incluida en `tests/clio_validation_regression.py`.

## Documentación

- `docs/instalacion.md`
- `docs/uso.md`
- `docs/formato-del-corpus.md`

## Cómo citar Clio

GitHub ya puede leer la metadata de citación desde `CITATION.cff`.

### Cita sugerida (texto)

`Nieto, Agustín (INHUS-CONICET/UNMDP). Clio: Harness agéntico y determinista para OCR histórico, métricas de minería de texto y reportes exploratorios por subcarpeta. Version 0.1.0. GitHub. https://github.com/agusnieto77/Clio`

### BibTeX

```bibtex
@software{clio_2026,
  author  = {Nieto, Agustín},
  title   = {Clio: Harness ag\'entico y determinista para OCR hist\'orico, m\'etricas de miner\'ia de texto y reportes exploratorios por subcarpeta},
  year    = {2026},
  version = {v0.1.0},
  note    = {INHUS-CONICET/UNMDP},
  url     = {https://github.com/agusnieto77/Clio}
}
```

## Licencia

MIT. Ver `LICENSE`.
