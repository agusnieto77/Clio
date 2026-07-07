"""
tokenizacion.py - Tokenizacion y stopwords compartidas por las metricas.

Single source of truth para partir texto en tokens y para definir que cuenta
como palabra vacia. Todas las tecnicas (frecuencia, co-ocurrencia, correlacion,
tfidf) reciben los docs ya tokenizados desde metricas.py, que es el unico que
llama a tokenizar() y a stopwords_espanol().
"""
from __future__ import annotations

import re
from pathlib import Path

from common import REPO_RAIZ

TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]+")


def tokenizar(texto: str, min_long: int) -> list[str]:
    """Tokeniza preservando la ortografia de epoca, solo minusculiza."""
    return [t.lower() for t in TOKEN_RE.findall(texto) if len(t) >= min_long]


def stopwords_espanol() -> set[str]:
    """Carga stopwords de NLTK + lista local de epoca."""
    try:
        import nltk
        from nltk.corpus import stopwords
    except ImportError as exc:
        raise SystemExit(
            "Falta NLTK. Instalar con: pip install -r harness/tools/requirements.txt"
        ) from exc

    try:
        sw_nltk = set(stopwords.words("spanish"))
    except LookupError:
        # Descargar el corpus on demand es aceptable: la primera corrida lo pide.
        nltk.download("stopwords", quiet=True)
        sw_nltk = set(stopwords.words("spanish"))

    sw_local: set[str] = set()
    path_local = REPO_RAIZ / "harness" / "tools" / "stopwords_epoca.txt"
    if path_local.is_file():
        for linea in path_local.read_text(encoding="utf-8").splitlines():
            linea = linea.strip().lower()
            if linea and not linea.startswith("#"):
                sw_local.add(linea)

    return sw_nltk | sw_local
