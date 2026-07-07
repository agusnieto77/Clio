# Instalación

## Requisitos mínimos

- Python 3.10 o superior
- `pip`
- (Opcional) OpenCode u otro runtime que entienda `.opencode/`

## Dependencias

```bash
pip install -r harness/tools/requirements.txt
```

Las librerías necesarias para análisis incluyen NLTK, numpy, scipy, scikit-learn, pandas y networkx.

## Stopwords NLTK

La primera corrida puede descargar el corpus `stopwords` de NLTK on-demand. Si trabajás sin internet, preinstalalo una vez.

## Verificación rápida

```bash
python tests/clio_validation_regression.py
```

Si termina sin excepciones, la suite de regresión pasó completa.
