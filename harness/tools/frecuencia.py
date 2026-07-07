"""
frecuencia.py - Calculo de frecuencia de tokens por documento.

Funcion pura: recibe docs ya tokenizados y devuelve el ranking
[documento -> [(termino, conteo), ...]] ordenado de mayor a menor.
"""
from __future__ import annotations

from collections import Counter


def calcular_frecuencia(docs: dict[str, list[str]]) -> dict[str, list[tuple[str, int]]]:
    """Ranking de tokens por documento, ordenado por frecuencia descendente."""
    return {
        base: Counter(tokens).most_common()
        for base, tokens in docs.items()
    }
