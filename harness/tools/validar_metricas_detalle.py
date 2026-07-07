"""Validaciones estructurales detalladas para metricas/ de Clio."""
from __future__ import annotations

import csv
from pathlib import Path


def validar_detalle_metricas(
    datos_json: dict,
    bases_validas: list[str],
    resumen_csv: Path,
) -> list[dict[str, str]]:
    invalidos: list[dict[str, str]] = []
    total_validas = len(bases_validas)
    _validar_json_metricas(datos_json, total_validas, invalidos)
    _validar_csv_resumen(resumen_csv, bases_validas, invalidos)
    return invalidos


def _validar_json_metricas(datos_json: dict, total_validas: int, invalidos: list) -> None:
    for nombre in ("frecuencia.json", "frecuencia_sin_stopwords.json"):
        payload = datos_json.get(nombre)
        if payload is not None and not isinstance(payload, dict):
            invalidos.append({"archivo": nombre, "motivo": "debe ser objeto documento -> ranking"})

    cooc = datos_json.get("co_ocurrencia.json")
    if cooc is not None and not (
        isinstance(cooc, dict)
        and isinstance(cooc.get("ventana"), int)
        and isinstance(cooc.get("por_documento"), dict)
    ):
        invalidos.append({"archivo": "co_ocurrencia.json", "motivo": "estructura minima invalida"})

    correlacion = datos_json.get("correlacion.json")
    if correlacion is not None and (
        not isinstance(correlacion, dict) or not _correlacion_valida(correlacion, total_validas)
    ):
        invalidos.append({"archivo": "correlacion.json", "motivo": "estructura minima invalida"})

    tfidf = datos_json.get("tfidf.json")
    if tfidf is not None and not (
        isinstance(tfidf, dict)
        and isinstance(tfidf.get("n_documentos"), int)
        and isinstance(tfidf.get("por_documento"), dict)
    ):
        invalidos.append({"archivo": "tfidf.json", "motivo": "estructura minima invalida"})

    versiones = datos_json.get("versiones.json")
    if versiones is None:
        return
    resumen = versiones.get("resumen_corpus") if isinstance(versiones, dict) else None
    n_documentos = resumen.get("n_documentos") if isinstance(resumen, dict) else None
    if not isinstance(n_documentos, int):
        invalidos.append({"archivo": "versiones.json", "motivo": "falta resumen_corpus.n_documentos"})
        return
    if n_documentos != total_validas:
        invalidos.append(
            {
                "archivo": "versiones.json",
                "motivo": f"n_documentos={n_documentos} no coincide con transcripciones_validas={total_validas}",
            }
        )


def _correlacion_valida(payload: dict, total_validas: int) -> bool:
    calculable = (
        isinstance(payload.get("n_documentos"), int)
        and isinstance(payload.get("terminos"), list)
        and isinstance(payload.get("pares_por_valor_absoluto"), list)
    )
    if calculable:
        return True
    return (
        total_validas == 1
        and isinstance(payload.get("terminos"), list)
        and isinstance(payload.get("matriz"), list)
        and isinstance(payload.get("nota"), str)
    )


def _validar_csv_resumen(path: Path, bases_validas: list[str], invalidos: list) -> None:
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
    except OSError as exc:
        invalidos.append({"archivo": "resumen_top10.csv", "motivo": f"csv ilegible: {exc}"})
        return
    header = reader.fieldnames or []
    if header[:2] != ["documento", "pal1"]:
        invalidos.append({"archivo": "resumen_top10.csv", "motivo": "cabecera esperada documento,pal1,..."})
    documentos = [row.get("documento", "") for row in rows]
    if "__SUBCORPUS__" not in documentos:
        invalidos.append({"archivo": "resumen_top10.csv", "motivo": "falta fila __SUBCORPUS__"})
    documentos_reales = [doc for doc in documentos if doc and doc != "__SUBCORPUS__"]
    total_validas = len(bases_validas)
    if len(documentos_reales) != total_validas:
        invalidos.append(
            {
                "archivo": "resumen_top10.csv",
                "motivo": f"filas_documento={len(documentos_reales)} no coincide con transcripciones_validas={total_validas}",
            }
        )
    if sorted(documentos_reales) != sorted(bases_validas):
        invalidos.append(
            {
                "archivo": "resumen_top10.csv",
                "motivo": "documentos_csv no coincide exactamente con transcripciones_validas",
            }
        )
