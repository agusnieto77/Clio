"""
coocurrencia.py - Co-ocurrencia de pares no ordenados dentro de ventana deslizante.

Para cada documento cuenta cuantas veces aparece cada par (a, b) de tokens
distintos dentro de una ventana de tamano fijo. Tambien agrega a nivel subcorpus.
"""
from __future__ import annotations

from collections import Counter


def calcular_co_ocurrencia(docs: dict[str, list[str]], ventana: int) -> dict:
    """Co-ocurrencia de pares no ordenados dentro de ventana deslizante."""
    por_doc = {}
    acumulado: Counter = Counter()
    for base, tokens in docs.items():
        c: Counter = Counter()
        n = len(tokens)
        for i in range(n):
            for j in range(i + 1, min(i + ventana, n)):
                a, b = sorted((tokens[i], tokens[j]))
                if a == b:
                    continue
                c[(a, b)] += 1
                acumulado[(a, b)] += 1
        por_doc[base] = [{"par": list(k), "conteo": v} for k, v in c.most_common(100)]
    return {
        "ventana": ventana,
        "por_documento": por_doc,
        "agregado_subcorpus": [
            {"par": list(k), "conteo": v} for k, v in acumulado.most_common(200)
        ],
    }
