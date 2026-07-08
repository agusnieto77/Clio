"""
validar.py - Validaciones entre etapas del harness Clio.

Uso:
    python harness/tools/validar.py transcripciones <ruta>
    python harness/tools/validar.py metricas <ruta>
    python harness/tools/validar.py informes <ruta>

Cada subcomando verifica las precondiciones de la etapa siguiente y emite
JSON con ok=true/false y detalle. Clio usa este reporte para decidir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from common import (
    ARCHIVO_ANEXO_NUBE_HTML,
    ARCHIVO_ANEXO_NUBE_PNG,
    ARCHIVO_INFORME_HTML,
    ARCHIVO_INFORME_MD,
    ARCHIVOS_METRICAS_ESPERADOS,
    EXTENSIONES_TRANSCRIPCION,
    PLACEHOLDERS_INVALIDOS,
    base_sin_extension,
    carpeta_metricas,
    carpeta_procesadas,
    emitir_json,
    emitir_ok,
    leer_checklist,
    leer_transcripcion,
    listar_imagenes_procesadas,
    listar_imagenes_sueltas,
    listar_transcripciones,
    resolver_ruta,
    validar_subcarpeta,
)
from validar_metricas_detalle import validar_detalle_metricas


# --------------------------------------------------------------------------- #
# Validacion de transcripciones
# --------------------------------------------------------------------------- #


def _es_contenido_valido(contenido: str) -> bool:
    texto = contenido.strip()
    if texto.lower() in PLACEHOLDERS_INVALIDOS:
        return False
    if not texto:
        return False
    ilegible = texto.lower().count("[ilegible]") * len("[ilegible]")
    return ilegible <= len(texto) * 0.8


def _total_transcripciones_validas(ruta: Path) -> int:
    return len(_bases_transcripciones_validas(ruta))


def _bases_transcripciones_validas(ruta: Path) -> list[str]:
    return [
        base_sin_extension(path)
        for path in listar_transcripciones(ruta)
        if _es_contenido_valido(leer_transcripcion(path))
    ]


def _pendientes_checklist(ruta: Path) -> list[str]:
    imagenes = leer_checklist(ruta).get("imagenes", {})
    if not isinstance(imagenes, dict):
        return []
    return [
        nombre
        for nombre, entrada in imagenes.items()
        if isinstance(entrada, dict) and entrada.get("estado") == "pendiente"
    ]


def validar_transcripciones(ruta: Path) -> int:
    procesadas = listar_imagenes_procesadas(ruta)
    sueltas = listar_imagenes_sueltas(ruta)
    pendientes_checklist = _pendientes_checklist(ruta)
    transcripciones = listar_transcripciones(ruta)
    bases_transcripciones = {base_sin_extension(p) for p in transcripciones}

    sin_transcripcion = []
    vacias = []
    placeholders = []

    for img in procesadas:
        base = base_sin_extension(img)
        if base not in bases_transcripciones:
            sin_transcripcion.append(img.name)
            continue
        # tomar el .txt preferentemente, si no .json
        cand = next(
            (p for p in transcripciones if base_sin_extension(p) == base),
            None,
        )
        if cand is None:
            sin_transcripcion.append(img.name)
            continue
        contenido = leer_transcripcion(cand)
        if not contenido.strip() or contenido.lower() in PLACEHOLDERS_INVALIDOS:
            vacias.append({"imagen": img.name, "archivo": cand.name})
            continue
        # detectar placeholder dominante (mas del 80% del contenido)
        if not _es_contenido_valido(contenido):
            placeholders.append({"imagen": img.name, "archivo": cand.name})

    total_validas = _total_transcripciones_validas(ruta)
    cero_ocr_util = total_validas == 0 and (sueltas or pendientes_checklist)
    ok = not (sin_transcripcion or vacias or placeholders or cero_ocr_util)
    emitir_json(
        {
            "ok": ok,
            "total_imagenes_procesadas": len(procesadas),
            "total_transcripciones": len(transcripciones),
            "total_transcripciones_validas": total_validas,
            "imagenes_fuente_pendientes": [p.name for p in sueltas],
            "checklist_pendientes": pendientes_checklist,
            "sin_transcripcion": sin_transcripcion,
            "transcripciones_vacias_o_placeholder": vacias,
            "transcripciones_dominadas_por_ilegible": placeholders,
            "error": "No hay transcripciones validas para imagenes pendientes o fuente."
            if cero_ocr_util
            else None,
        }
    )
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# Validacion de metricas
# --------------------------------------------------------------------------- #


def validar_metricas(ruta: Path) -> int:
    met = carpeta_metricas(ruta)
    if not met.is_dir():
        emitir_json(
            {
                "ok": False,
                "error": "La subcarpeta metricas/ no existe.",
                "faltantes": list(ARCHIVOS_METRICAS_ESPERADOS),
            }
        )
        return 1

    faltantes = []
    invalidos = []
    datos_json = {}
    for nombre in ARCHIVOS_METRICAS_ESPERADOS:
        p = met / nombre
        if not p.is_file():
            faltantes.append(nombre)
            continue
        if p.stat().st_size == 0:
            invalidos.append({"archivo": nombre, "motivo": "vacio"})
            continue
        if nombre.endswith(".json"):
            try:
                with p.open("r", encoding="utf-8") as fh:
                    datos_json[nombre] = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                invalidos.append({"archivo": nombre, "motivo": f"json invalido: {exc}"})

    bases_validas = _bases_transcripciones_validas(ruta)
    invalidos.extend(validar_detalle_metricas(datos_json, bases_validas, met / "resumen_top10.csv"))

    ok = not (faltantes or invalidos)
    emitir_json(
        {
            "ok": ok,
            "metricas_esperadas": list(ARCHIVOS_METRICAS_ESPERADOS),
            "total_transcripciones_validas": len(bases_validas),
            "faltantes": faltantes,
            "invalidos": invalidos,
        }
    )
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# Validacion de informes
# --------------------------------------------------------------------------- #


def validar_informes(ruta: Path) -> int:
    html = ruta / ARCHIVO_INFORME_HTML
    md = ruta / ARCHIVO_INFORME_MD
    anexo_html = ruta / ARCHIVO_ANEXO_NUBE_HTML
    anexo_png = ruta / ARCHIVO_ANEXO_NUBE_PNG
    estado = {}
    ok = True
    imagenes_procesadas = listar_imagenes_procesadas(ruta)
    if not html.is_file() or html.stat().st_size == 0:
        estado["informe_preliminar.html"] = "falta_o_vacio"
        ok = False
    else:
        contenido_html = html.read_text(encoding="utf-8", errors="ignore")
        secciones = contenido_html.count('class="seccion"')
        if "<nav" not in contenido_html or secciones < len(imagenes_procesadas):
            estado["informe_preliminar.html"] = "estructura_incompleta"
            ok = False
        else:
            estado["informe_preliminar.html"] = "ok"
    if not md.is_file() or md.stat().st_size == 0:
        estado["informe_final.md"] = "falta_o_vacio"
        ok = False
    else:
        contenido_md = md.read_text(encoding="utf-8", errors="ignore")
        requeridas = [
            "## Nota de metodo",
            "## 1. Descripcion general",
            "## 2. Patrones lexicos",
            "## 3. Asociaciones",
            "## 5. Hallazgos",
            "## Anexo de visualización",
        ]
        faltan = [titulo for titulo in requeridas if titulo not in contenido_md]
        referencias_anexo = [ARCHIVO_ANEXO_NUBE_HTML, ARCHIVO_ANEXO_NUBE_PNG]
        faltan_refs = [ref for ref in referencias_anexo if ref not in contenido_md]
        if len(contenido_md.strip()) < 500 or faltan or faltan_refs:
            estado["informe_final.md"] = {"estado": "estructura_incompleta", "faltan": faltan, "faltan_referencias": faltan_refs}
            ok = False
        else:
            estado["informe_final.md"] = "ok"
    if not anexo_html.is_file() or anexo_html.stat().st_size == 0:
        estado[ARCHIVO_ANEXO_NUBE_HTML] = "falta_o_vacio"
        ok = False
    else:
        contenido_anexo_html = anexo_html.read_text(encoding="utf-8", errors="ignore")
        if "Plotly.newPlot" not in contenido_anexo_html and "plotly" not in contenido_anexo_html.lower():
            estado[ARCHIVO_ANEXO_NUBE_HTML] = "estructura_incompleta"
            ok = False
        else:
            estado[ARCHIVO_ANEXO_NUBE_HTML] = "ok"
    if not anexo_png.is_file() or anexo_png.stat().st_size == 0:
        estado[ARCHIVO_ANEXO_NUBE_PNG] = "falta_o_vacio"
        ok = False
    else:
        estado[ARCHIVO_ANEXO_NUBE_PNG] = "ok"
    emitir_json({"ok": ok, **estado})
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "Uso: python harness/tools/validar.py "
            "<transcripciones|metricas|informes> <ruta>",
            file=sys.stderr,
        )
        return 2

    que = argv[1].lower()
    ruta = resolver_ruta(argv[2])
    validar_subcarpeta(ruta)

    if que == "transcripciones":
        return validar_transcripciones(ruta)
    if que == "metricas":
        return validar_metricas(ruta)
    if que == "informes":
        return validar_informes(ruta)

    print(f"Subcomando desconocido: {que}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
