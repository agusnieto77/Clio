"""
versiones.py - Declaracion de versiones de librerias y parametros para reproducibilidad.

Genera el bloque metricas/versiones.json que permite reproducir una corrida:
version de Python, version de cada libreria cientifica y los parametros usados.
"""
from __future__ import annotations

import sys
from importlib.metadata import version as pkg_version


def calcular_versiones(params: dict, n_docs: int, n_tokens_unicos: int) -> dict:
    libs: dict[str, str] = {}
    for nombre in (
        "nltk",
        "scikit-learn",
        "pandas",
        "networkx",
        "scipy",
        "numpy",
    ):
        try:
            libs[nombre] = pkg_version(nombre)
        except Exception:
            libs[nombre] = "no_instalada"
    return {
        "python": sys.version.split()[0],
        "librerias": libs,
        "parametros": {
            "ventana_cocurrencia": params["ventana_cocurrencia"],
            "stopwords_idioma": params["stopwords_idioma"],
            "stopwords_fuente": (
                "nltk.corpus.stopwords.words('spanish') + "
                "harness/tools/stopwords_epoca.txt"
            ),
            "min_longitud_token": params["min_longitud_token"],
            "top_n_frecuencia": params["top_n_frecuencia"],
            "tfidf_norma": params["tfidf_norma"],
            "tfidf_sublinear_tf": params["tfidf_sublinear_tf"],
            "normalizacion_aplicada": (
                "minusculas; sin stemming ni lematizacion; "
                "ortografia de epoca preservada"
            ),
            "tokenizador_regex": r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]+",
        },
        "resumen_corpus": {
            "n_documentos": n_docs,
            "n_terminos_unicos": n_tokens_unicos,
        },
    }
