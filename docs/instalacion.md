# Instalación

## Requisitos mínimos

- **[OpenCode](https://opencode.ai)** (runtime nativo del harness; provee el comando `/clio`, el agente `clio` y carga las skills de `.opencode/skill/`).
- Python 3.10 o superior
- `pip`

## Dependencias

```bash
pip install -r harness/tools/requirements.txt
```

Las librerías necesarias para análisis incluyen NLTK, numpy, scipy, scikit-learn, pandas y networkx.

## Configuración de modelos

La forma más simple de arrancar es usar el asistente guiado:

```bash
python harness/tools/configurar_modelos.py
```

Ese asistente puede:

- dejar la **configuración por defecto**
- dejar la **configuración recomendada**
- hacer una **configuración guiada paso a paso**

Si querés aplicar un preset directo:

```bash
python harness/tools/configurar_modelos.py --preset default
python harness/tools/configurar_modelos.py --preset recommended
```

El repo ya trae un `harness/modelos.json` funcional. El asistente reescribe ese archivo y sincroniza los `model:` de `.opencode/agent/*.md`. Reiniciá OpenCode después de cambiar modelos.

## Stopwords NLTK

La primera corrida puede descargar el corpus `stopwords` de NLTK on-demand. Si trabajás sin internet, preinstalalo una vez.

## Verificación rápida

```bash
python tests/run_all.py
```

Si termina sin excepciones, todas las suites de regresión pasaron completas.
