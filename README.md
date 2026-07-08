# Clio

![Release](https://img.shields.io/github/v/release/agusnieto77/Clio?label=release)
![License](https://img.shields.io/github/license/agusnieto77/Clio)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Regression tests](https://img.shields.io/badge/regression-15%20tests-green)

Harness agéntico nativo de [OpenCode](https://opencode.ai) y determinista para procesar corpus documentales fotografiados: OCR histórico, métricas de minería de texto y reportes exploratorios por subcarpeta.

Clio corre como agente nativo de OpenCode: el orquestador, las skills de los cuatro roles y el comando `/clio` viven dentro de `.opencode/`. Los scripts en `harness/tools/` son las primitivas deterministas que esos agentes invocan; sin OpenCode podés ejecutar el pipeline como scripts sueltos en modo manual, pero perdés la orquestación unificada, las validaciones entre etapas y el comando `/clio`.

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

- **[OpenCode](https://opencode.ai)** (runtime nativo del harness).
- Python 3.10+
- Dependencias Python:

```bash
pip install -r harness/tools/requirements.txt
```

## Configuración inicial de modelos

Si no querés tocar JSON a mano, usá el asistente guiado:

```bash
python harness/tools/configurar_modelos.py
```

El script ofrece tres caminos:

1. **Configuración por defecto**
2. **Configuración recomendada** (la que viene testeada en este repo)
3. **Configuración guiada paso a paso**

También podés aplicar un preset directo:

```bash
python harness/tools/configurar_modelos.py --preset default
python harness/tools/configurar_modelos.py --preset recommended
```

Clio ya trae un `harness/modelos.json` listo para usar. El asistente reescribe ese archivo y además sincroniza el campo `model:` de `.opencode/agent/*.md`. Después del cambio, **reiniciá OpenCode**.

> Aclaración: `harness/modelos.json` está **trackeado en el repo** intencionalmente, de modo que el repositorio publicado refleje siempre una configuración funcional. Los presets `modelos.default.json` y `modelos.recommended.json` son plantillas que el asistente guiado puede copiar a `modelos.json`; **no se cargan en runtime**. Los agentes en runtime leen su propio frontmatter `model:`.

## Uso rápido

### Camino canónico — flujo completo con OpenCode

Desde una sesión OpenCode abierta en este repo:

```text
/clio Fuentes/MiSubcorpus
```

OpenCode carga el agente `clio` definido en `opencode.json`, las cuatro skills de `.opencode/skill/` y el comando `/clio`. El flujo valida el estado en cada etapa y registra avance en el filesystem, así que es seguro interrumpirlo y reanudar.

### Fallback — pipeline manual con scripts sueltos

Útil solo para debug o cuando no podés abrir OpenCode. **Perdés la orquestación, las validaciones entre etapas y el comando `/clio`**: tenés que invocar los scripts uno a uno en el orden correcto.

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
- `CONTRIBUTING.md`

## Cómo citar Clio

GitHub ya puede leer la metadata de citación desde `CITATION.cff`.

### Cita sugerida (texto)

> **Nieto, Agustín** (INHUS-CONICET/UNMDP).  
> *Clio: Harness agéntico y determinista para OCR histórico, métricas de minería de texto y reportes exploratorios por subcarpeta.*  
> Version 0.1.0. GitHub.  
> <https://github.com/agusnieto77/Clio>

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
