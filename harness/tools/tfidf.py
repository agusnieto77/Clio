"""
tfidf.py - TF-IDF por documento y agregado al subcorpus.

Envuelve sklearn.feature_extraction.text.TfidfVectorizer con token_pattern
preservando acentos y ñ. Reporta los 30 terminos de mayor peso por documento
y el acumulado de pesos a nivel subcorpus.
"""
from __future__ import annotations

from collections import Counter


def calcular_tfidf(docs: dict[str, list[str]], norma: str, sublinear: bool) -> dict:
    """TF-IDF por documento y agregado al subcorpus."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    bases = list(docs.keys())
    documentos_texto = [" ".join(docs[b]) for b in bases]
    if not any(documentos_texto):
        return {
            "norma": norma,
            "sublinear_tf": sublinear,
            "por_documento": {},
            "agregado_subcorpus": [],
        }

    vectorizer = TfidfVectorizer(
        lowercase=True,
        token_pattern=r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]+",
        norm=norma,
        sublinear_tf=sublinear,
    )
    mat = vectorizer.fit_transform(documentos_texto)
    vocab = vectorizer.get_feature_names_out()

    por_doc = {}
    suma_acumulada: Counter = Counter()
    for fila, base in enumerate(bases):
        vec = mat.getrow(fila).toarray().ravel()
        top_idx = vec.argsort()[::-1][:30]
        contrib = []
        for idx in top_idx:
            peso = float(vec[idx])
            if peso <= 0:
                continue
            termino = str(vocab[idx])
            contrib.append({"termino": termino, "peso": round(peso, 4)})
            suma_acumulada[termino] += peso
        por_doc[base] = contrib

    agregado = [
        {"termino": t, "peso_acumulado": round(p, 4)}
        for t, p in suma_acumulada.most_common(100)
    ]
    return {
        "norma": norma,
        "sublinear_tf": sublinear,
        "n_documentos": len(bases),
        "por_documento": por_doc,
        "agregado_subcorpus": agregado,
    }
