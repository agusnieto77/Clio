"""
correlacion.py - Correlacion de co-presencia binaria entre los top_n terminos.

Construye una matriz documentos x terminos (top_n mas frecuentes del subcorpus),
calcula la correlacion de Pearson entre columnas y reporta los pares mas
fuertes (positivos o negativos) por valor absoluto.

Para subcorpus de un solo documento la correlacion no es calculable: devuelve
un shape documentado con nota, que validar_metricas_detalle acepta explicitamente.
"""
from __future__ import annotations

from collections import Counter


def calcular_correlacion(docs: dict[str, list[str]], top_n: int) -> dict:
    """Correlacion de co-presencia binaria entre los top_n terminos mas frecuentes."""
    import numpy as np
    from scipy.sparse import csr_matrix

    bases = list(docs.keys())
    if not bases:
        return {"top_n": top_n, "matriz": [], "terminos": []}

    # Vocabulario: top_n terminos mas frecuentes en el subcorpus.
    # Usamos dict.fromkeys(tokens) para preservar el orden de primera aparicion
    # dentro de cada doc. Un set NO preserva orden, y al combinarse con
    # most_common(top_n) sobre empates produce salidas no deterministas entre
    # procesos Python (PYTHONHASHSEED varia entre corridas).
    df: Counter = Counter()
    for tokens in docs.values():
        df.update(dict.fromkeys(tokens, 1))
    terminos = [t for t, _ in df.most_common(top_n)]
    if not terminos:
        return {"top_n": top_n, "matriz": [], "terminos": []}

    termino_idx = {t: i for i, t in enumerate(terminos)}
    rows, cols, vals = [], [], []
    for fila, base in enumerate(bases):
        presentes = set(docs[base]) & set(terminos)
        for t in presentes:
            rows.append(fila)
            cols.append(termino_idx[t])
            vals.append(1)
    matriz = csr_matrix(
        (vals, (rows, cols)), shape=(len(bases), len(terminos)), dtype=float
    ).toarray()

    if matriz.shape[0] < 2:
        return {
            "top_n": top_n,
            "terminos": terminos,
            "matriz": [],
            "nota": "Menos de 2 documentos; correlacion no calculable.",
        }

    # Pearson entre columnas
    try:
        correl = np.corrcoef(matriz.T)
    except Exception:
        correl = np.zeros((len(terminos), len(terminos)))

    pares_significativos = []
    for i in range(len(terminos)):
        for j in range(i + 1, len(terminos)):
            r = float(correl[i, j])
            if r != r:  # NaN
                continue
            pares_significativos.append(
                {
                    "par": [terminos[i], terminos[j]],
                    "correlacion_pearson": round(r, 4),
                }
            )
    pares_significativos.sort(key=lambda x: abs(x["correlacion_pearson"]), reverse=True)

    return {
        "top_n": top_n,
        "n_documentos": len(bases),
        "terminos": terminos,
        "pares_por_valor_absoluto": pares_significativos[:100],
    }
