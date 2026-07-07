"""
Modulo comun del harness Clio.
Funciones de path, IO y registro compartidas por todos los scripts.

Linea de comandos: este modulo no se invoca directamente.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

# --------------------------------------------------------------------------- #
# Constantes
# --------------------------------------------------------------------------- #

REPO_RAIZ = Path(__file__).resolve().parents[2]

# Nombres canonicos de archivos y carpetas dentro de una subcarpeta.
SUBCARPETA_PROCESADAS = "i_procesadas"
SUBCARPETA_METRICAS = "metricas"
ARCHIVO_CHECKLIST = "checklist.json"
ARCHIVO_LOG_CLIO = "log_clio.md"
ARCHIVO_INFORME_HTML = "informe_preliminar.html"
ARCHIVO_INFORME_MD = "informe_final.md"

EXTENSIONES_IMAGEN = (".jpg", ".jpeg")
EXTENSIONES_TRANSCRIPCION = (".txt", ".json")
ARCHIVOS_JSON_SISTEMA = {ARCHIVO_CHECKLIST}

# Lista canonica de metricas esperadas en <ruta>/metricas/.
# Single source of truth: estado.py, validar.py y metricas.py importan desde aca.
ARCHIVOS_METRICAS_ESPERADOS = [
    "frecuencia.json",
    "frecuencia_sin_stopwords.json",
    "co_ocurrencia.json",
    "correlacion.json",
    "tfidf.json",
    "resumen_top10.csv",
    "versiones.json",
]

PLACEHOLDERS_INVALIDOS = {
    "",
    "[ilegible]",
    "[zona ilegible]",
    "ilegible",
    "transcripcion vacia",
    "sin texto",
    "none",
    "null",
}

# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #


def resolver_ruta(ruta_arg: str) -> Path:
    """Resuelve una ruta recibida como argumento (relativa al repo o absoluta)."""
    p = Path(ruta_arg).expanduser()
    if not p.is_absolute():
        p = REPO_RAIZ / p
    return p.resolve()


def validar_subcarpeta(ruta: Path) -> None:
    """Verifica que la ruta sea una subcarpeta dentro de Fuentes/."""
    try:
        ruta.relative_to(REPO_RAIZ / "Fuentes")
    except ValueError as exc:
        raise SystemExit(
            f"ERROR: la ruta '{ruta}' no esta dentro de Fuentes/. "
            f"Las subcarpetas a procesar deben colgar de Fuentes/."
        ) from exc
    if not ruta.is_dir():
        raise SystemExit(f"ERROR: la ruta '{ruta}' no es una carpeta existente.")


def carpeta_procesadas(ruta: Path) -> Path:
    return ruta / SUBCARPETA_PROCESADAS


def carpeta_metricas(ruta: Path) -> Path:
    return ruta / SUBCARPETA_METRICAS


def archivo_checklist(ruta: Path) -> Path:
    return ruta / ARCHIVO_CHECKLIST


def archivo_log(ruta: Path) -> Path:
    return ruta / ARCHIVO_LOG_CLIO


# --------------------------------------------------------------------------- #
# Listado de imagenes y transcripciones
# --------------------------------------------------------------------------- #


def listar_imagenes_sueltas(ruta: Path) -> list[Path]:
    """Lista imagenes en la raiz de la subcarpeta, excluyendo i_procesadas/."""
    out = []
    for entrada in sorted(ruta.iterdir()):
        if entrada.is_file() and entrada.suffix.lower() in EXTENSIONES_IMAGEN:
            out.append(entrada)
    return out


def listar_imagenes_procesadas(ruta: Path) -> list[Path]:
    proc = carpeta_procesadas(ruta)
    if not proc.is_dir():
        return []
    return sorted(p for p in proc.iterdir() if p.is_file())


def listar_imagenes_totales(ruta: Path) -> list[Path]:
    """Suelta + procesadas."""
    return listar_imagenes_sueltas(ruta) + listar_imagenes_procesadas(ruta)


def listar_transcripciones(ruta: Path) -> list[Path]:
    """Archivos de transcripcion (.txt preferentemente) en la raiz de la subcarpeta."""
    por_base: dict[str, Path] = {}
    bases_procesadas = {base_sin_extension(p) for p in listar_imagenes_procesadas(ruta)}
    for entrada in sorted(ruta.iterdir()):
        if not entrada.is_file() or entrada.suffix.lower() not in EXTENSIONES_TRANSCRIPCION:
            continue
        if entrada.suffix.lower() == ".json" and not _es_json_transcripcion(
            entrada,
            bases_procesadas,
        ):
            continue
        base = base_sin_extension(entrada)
        existente = por_base.get(base)
        if existente is None or entrada.suffix.lower() == ".txt":
            por_base[base] = entrada
    return sorted(por_base.values())


def base_sin_extension(path: Path) -> str:
    return path.stem


def _es_json_transcripcion(path: Path, bases_procesadas: set[str]) -> bool:
    if path.name in ARCHIVOS_JSON_SISTEMA:
        return False
    if path.stem in bases_procesadas:
        return True
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(data, dict) and isinstance(data.get("transcripcion"), str)


def leer_transcripcion(path: Path) -> str:
    """Lee el contenido textual de un archivo de transcripcion (.txt o .json).

    Para .json devuelve data["transcripcion"] (string, posiblemente vacio).
    Para .txt devuelve el contenido del archivo.
    Cualquier error de IO o parseo devuelve "".
    Single source of truth para validar.py, informe_preliminar.py y metricas.py.
    """
    if path.suffix.lower() == ".json":
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return str(data.get("transcripcion", ""))
        except (json.JSONDecodeError, OSError):
            return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


# --------------------------------------------------------------------------- #
# Checklist
# --------------------------------------------------------------------------- #


def leer_checklist(ruta: Path) -> dict[str, Any]:
    ck = archivo_checklist(ruta)
    if not ck.is_file():
        return {"imagenes": {}}
    try:
        with ck.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if "imagenes" not in data or not isinstance(data["imagenes"], dict):
            return {"imagenes": {}}
        return data
    except (json.JSONDecodeError, OSError):
        return {"imagenes": {}}


def escribir_checklist(ruta: Path, data: dict[str, Any]) -> None:
    ck = archivo_checklist(ruta)
    ck.parent.mkdir(parents=True, exist_ok=True)
    with ck.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# Log de Clio
# --------------------------------------------------------------------------- #


def asegurar_log(ruta: Path) -> Path:
    log = archivo_log(ruta)
    if not log.is_file():
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8") as fh:
            fh.write("# Log de Clio\n\n")
            fh.write(f"Subcarpeta: `{ruta.relative_to(REPO_RAIZ)}`\n\n")
    return log


def escribir_log(ruta: Path, linea: str) -> None:
    log = asegurar_log(ruta)
    marca = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{marca} {linea}\n")


def escribir_log_seccion(ruta: Path, titulo: str, cuerpo: str) -> None:
    log = asegurar_log(ruta)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## {titulo}\n\n{cuerpo}\n")


# --------------------------------------------------------------------------- #
# Salida JSON a stdout (para que los subagentes la parseen)
# --------------------------------------------------------------------------- #


def emitir_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def emitir_ok(mensaje: str, **extra: Any) -> None:
    emitir_json({"ok": True, "mensaje": mensaje, **extra})


def emitir_error(mensaje: str, **extra: Any) -> None:
    emitir_json({"ok": False, "error": mensaje, **extra})
