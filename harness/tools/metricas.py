"""
metricas.py - Calculo determinista de metricas de mineria de texto sobre las
transcripciones de una subcarpeta.

Orquestador: lee args, carga parametros, tokeniza una sola vez y delega cada
tecnica a su modulo. La logica de cada tecnica vive en:
    frecuencia.py      coocurrencia.py   correlacion.py
    tfidf.py           versiones.py
La tokenizacion y las stopwords viven en tokenizacion.py.

Produce en <ruta>/metricas/:
    frecuencia.json
    frecuencia_sin_stopwords.json
    co_ocurrencia.json
    correlacion.json
    tfidf.json
    resumen_top10.csv
    versiones.json

Uso:
    python harness/tools/metricas.py <ruta>
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

from coocurrencia import calcular_co_ocurrencia
from common import (
    ARCHIVOS_METRICAS_ESPERADOS,
    asegurar_log,
    base_sin_extension,
    carpeta_metricas,
    emitir_error,
    emitir_ok,
    escribir_log,
    leer_transcripcion,
    listar_transcripciones,
    resolver_ruta,
    validar_subcarpeta,
    REPO_RAIZ,
)
from correlacion import calcular_correlacion
from frecuencia import calcular_frecuencia
from tfidf import calcular_tfidf
from tokenizacion import stopwords_espanol, tokenizar
from versiones import calcular_versiones

# --------------------------------------------------------------------------- #
# Parametros
# --------------------------------------------------------------------------- #


def _cargar_parametros() -> dict:
    path = REPO_RAIZ / "harness" / "modelos.json"
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("parametros_analisis", {})


PARAMS_DEFAULT = {
    "ventana_cocurrencia": 5,
    "stopwords_idioma": "español",
    "min_longitud_token": 2,
    "top_n_frecuencia": 10,
    "tfidf_norma": "l2",
    "tfidf_sublinear_tf": True,
}


# --------------------------------------------------------------------------- #
# Orquestacion
# --------------------------------------------------------------------------- #


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python harness/tools/metricas.py <ruta>", file=sys.stderr)
        return 2

    ruta = resolver_ruta(argv[1])
    validar_subcarpeta(ruta)

    params = {**PARAMS_DEFAULT, **_cargar_parametros()}

    archivos = listar_transcripciones(ruta)
    if not archivos:
        emitir_error(
            "No hay archivos de transcripcion (.txt o .json) en la subcarpeta."
        )
        return 1

    sw = stopwords_espanol()
    docs_tokens: dict[str, list[str]] = {}
    excluidos = []
    for p in archivos:
        texto = leer_transcripcion(p)
        if texto.strip() == "":
            excluidos.append({"archivo": p.name, "motivo": "transcripcion vacia"})
            continue
        base = base_sin_extension(p)
        docs_tokens[base] = tokenizar(texto, params["min_longitud_token"])

    if not docs_tokens:
        emitir_error(
            "Todas las transcripciones estan vacias. No se puede calcular metricas.",
            excluidos=excluidos,
        )
        return 1

    docs_sin_sw = {
        base: [t for t in tokens if t not in sw]
        for base, tokens in docs_tokens.items()
    }

    n_docs = len(docs_tokens)
    n_unicos = len({t for tokens in docs_tokens.values() for t in tokens})

    frec_total = calcular_frecuencia(docs_tokens)
    frec_sin_sw = calcular_frecuencia(docs_sin_sw)
    cooc = calcular_co_ocurrencia(docs_tokens, params["ventana_cocurrencia"])
    correl = calcular_correlacion(docs_sin_sw, params["top_n_frecuencia"] * 2)
    tfidf = calcular_tfidf(docs_tokens, params["tfidf_norma"], params["tfidf_sublinear_tf"])
    versiones = calcular_versiones(params, n_docs, n_unicos)

    # Resumen top10 en CSV
    met = carpeta_metricas(ruta)
    met.mkdir(parents=True, exist_ok=True)

    filas_csv = []
    top_n = params["top_n_frecuencia"]
    for base, ranking in frec_sin_sw.items():
        top_terms = [t for t, _ in ranking[:top_n]]
        filas_csv.append(
            {
                "documento": base,
                **{
                    f"pal{i+1}": (top_terms[i] if i < len(top_terms) else "")
                    for i in range(top_n)
                },
            }
        )
    # Fila agregada subcorpus
    acumulado: Counter = Counter()
    for tokens in docs_sin_sw.values():
        acumulado.update(tokens)
    top_agregado = [t for t, _ in acumulado.most_common(top_n)]
    filas_csv.append(
        {
            "documento": "__SUBCORPUS__",
            **{
                f"pal{i+1}": (top_agregado[i] if i < len(top_agregado) else "")
                for i in range(top_n)
            },
        }
    )

    def _dump(nombre: str, payload):
        with (met / nombre).open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)

    _dump("frecuencia.json", frec_total)
    _dump("frecuencia_sin_stopwords.json", frec_sin_sw)
    _dump("co_ocurrencia.json", cooc)
    _dump("correlacion.json", correl)
    _dump("tfidf.json", tfidf)
    _dump("versiones.json", versiones)

    with (met / "resumen_top10.csv").open("w", encoding="utf-8", newline="") as fh:
        campos = ["documento"] + [f"pal{i+1}" for i in range(top_n)]
        writer = csv.DictWriter(fh, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas_csv)

    asegurar_log(ruta)
    escribir_log(
        ruta,
        f"METRICAS - documentos={n_docs} - terminos_unicos={n_unicos} - "
        f"excluidos={len(excluidos)} - archivos={len(ARCHIVOS_METRICAS_ESPERADOS)}",
    )

    emitir_ok(
        f"Metricas calculadas: {n_docs} documentos, {n_unicos} terminos unicos.",
        n_documentos=n_docs,
        n_terminos_unicos=n_unicos,
        excluidos=excluidos,
        metricas_producidas=list(ARCHIVOS_METRICAS_ESPERADOS),
        parametros=params,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
