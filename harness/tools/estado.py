"""
estado.py - Reconstruccion y reporte de estado de una subcarpeta.

Uso:
    python harness/tools/estado.py <ruta> init
    python harness/tools/estado.py <ruta> resumen

Comandos:
    init     - Asegura el log de Clio y emite JSON con el estado reconstruido
               desde el filesystem (imagenes pendientes, procesadas, metricas,
               informes).
    resumen  - Emite JSON con el estado final de la subcarpeta.
"""
from __future__ import annotations

import sys
from pathlib import Path

from common import (
    REPO_RAIZ,
    base_sin_extension,
    archivo_checklist,
    archivo_log,
    asegurar_log,
    carpeta_metricas,
    carpeta_procesadas,
    emitir_json,
    emitir_ok,
    leer_checklist,
    listar_imagenes_procesadas,
    listar_imagenes_sueltas,
    listar_transcripciones,
    resolver_ruta,
    validar_subcarpeta,
    escribir_log,
    ARCHIVO_INFORME_HTML,
    ARCHIVO_INFORME_MD,
    ARCHIVOS_METRICAS_ESPERADOS,
)


def _estado_completo(ruta: Path) -> dict:
    sueltas = listar_imagenes_sueltas(ruta)
    procesadas = listar_imagenes_procesadas(ruta)
    checklist = leer_checklist(ruta)
    imagenes_check = checklist.get("imagenes", {})

    pendientes_segun_fs = [p.name for p in sueltas]
    procesadas_segun_fs = [p.name for p in procesadas]
    procesadas_bases = {base_sin_extension(p) for p in procesadas}

    # Conteos por estado segun checklist
    por_estado = {"pendiente": 0, "procesada": 0, "error": 0}
    estados_check = {}
    for nombre, estado in imagenes_check.items():
        e = str(estado.get("estado", "pendiente")).lower()
        estados_check[nombre] = e
        por_estado[e] = por_estado.get(e, 0) + 1

    imagenes_en_error = sorted(
        nombre for nombre, estado in estados_check.items() if estado == "error"
    )
    imagenes_pendientes_ocr = [
        img.name for img in sueltas if estados_check.get(img.name, "pendiente") != "error"
    ]

    # Metricas
    met = carpeta_metricas(ruta)
    metricas_existentes = []
    metricas_faltantes = []
    if met.is_dir():
        for nombre in ARCHIVOS_METRICAS_ESPERADOS:
            if (met / nombre).is_file():
                metricas_existentes.append(nombre)
            else:
                metricas_faltantes.append(nombre)
    else:
        metricas_faltantes = list(ARCHIVOS_METRICAS_ESPERADOS)

    metricas_completas = len(metricas_faltantes) == 0

    # Informes
    informe_html = (ruta / ARCHIVO_INFORME_HTML).is_file()
    informe_md = (ruta / ARCHIVO_INFORME_MD).is_file()

    transcripciones = listar_transcripciones(ruta)
    transcripciones_bases = {base_sin_extension(p) for p in transcripciones}
    inconsistencias = _detectar_inconsistencias(
        estados_check,
        pendientes_segun_fs,
        procesadas_segun_fs,
        procesadas_bases,
        transcripciones_bases,
    )

    carpeta_vacia = not sueltas and not procesadas and not transcripciones

    # Decision de reanudacion
    if carpeta_vacia:
        punto = "detenido"
        motivo = "SUBCARPETA VACIA"
    elif imagenes_pendientes_ocr:
        punto = "ocr"
        motivo = f"hay {len(imagenes_pendientes_ocr)} imagenes pendientes de OCR"
    elif imagenes_en_error and not metricas_completas:
        punto = "detenido"
        motivo = f"hay {len(imagenes_en_error)} imagenes en error; requiere decision del investigador"
    elif not metricas_completas:
        punto = "analisis"
        motivo = f"metricas incompletas: faltan {metricas_faltantes}"
    elif not (informe_html and informe_md):
        punto = "redaccion"
        faltan = []
        if not informe_html:
            faltan.append(ARCHIVO_INFORME_HTML)
        if not informe_md:
            faltan.append(ARCHIVO_INFORME_MD)
        motivo = f"faltan informes: {faltan}"
    else:
        punto = "completo"
        motivo = "todas las etapas finalizadas"

    return {
        "ruta": str(ruta),
        "ruta_relativa": str(ruta.relative_to(REPO_RAIZ)).replace("\\", "/"),
        "imagenes_total": len(sueltas) + len(procesadas),
        "imagenes_sueltas": pendientes_segun_fs,
        "imagenes_pendientes_ocr": imagenes_pendientes_ocr,
        "imagenes_en_error": imagenes_en_error,
        "imagenes_procesadas": procesadas_segun_fs,
        "checklist_existe": archivo_checklist(ruta).is_file(),
        "checklist_por_estado": por_estado,
        "transcripciones": [p.name for p in transcripciones],
        "inconsistencias": inconsistencias,
        "metricas_existentes": metricas_existentes,
        "metricas_faltantes": metricas_faltantes,
        "metricas_completas": metricas_completas,
        "informe_html_existe": informe_html,
        "informe_md_existe": informe_md,
        "punto_reanudacion": punto,
        "motivo_reanudacion": motivo,
    }


def _detectar_inconsistencias(
    estados_check: dict,
    pendientes_fs: list[str],
    procesadas_fs: list[str],
    procesadas_bases: set[str],
    transcripciones_bases: set[str],
) -> list[dict[str, str]]:
    inconsistencias = []
    pendientes_set = set(pendientes_fs)
    procesadas_set = set(procesadas_fs)
    for nombre, estado in estados_check.items():
        if estado == "procesada" and nombre not in procesadas_set:
            inconsistencias.append(
                {"tipo": "checklist_procesada_sin_archivo", "imagen": nombre}
            )
        if estado == "pendiente" and nombre in procesadas_set:
            inconsistencias.append(
                {"tipo": "archivo_procesado_checklist_pendiente", "imagen": nombre}
            )
        if estado == "error" and nombre not in pendientes_set and nombre not in procesadas_set:
            inconsistencias.append({"tipo": "checklist_error_sin_archivo", "imagen": nombre})
    for nombre in procesadas_fs:
        if estados_check.get(nombre) not in {"procesada", None}:
            inconsistencias.append({"tipo": "procesada_estado_no_procesado", "imagen": nombre})
    for base in sorted(transcripciones_bases - procesadas_bases):
        inconsistencias.append({"tipo": "transcripcion_sin_imagen_procesada", "documento": base})
    return inconsistencias


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "Uso: python harness/tools/estado.py <ruta> <init|resumen>",
            file=sys.stderr,
        )
        return 2

    ruta_arg = argv[1]
    comando = argv[2].lower()

    ruta = resolver_ruta(ruta_arg)
    validar_subcarpeta(ruta)

    estado = _estado_completo(ruta)

    if comando == "init":
        primera_inicializacion = not archivo_log(ruta).is_file()
        asegurar_log(ruta)
        if primera_inicializacion:
            escribir_log(
                ruta,
                f"INIT - subcarpeta={ruta.name} - "
                f"imagenes_pendientes={len(estado['imagenes_pendientes_ocr'])} - "
                f"imagenes_procesadas={len(estado['imagenes_procesadas'])} - "
                f"punto_reanudacion={estado['punto_reanudacion']}",
            )
        emitir_ok("Estado inicial reconstruido", **estado)
        return 0

    if comando == "resumen":
        emitir_ok("Resumen de estado", **estado)
        return 0

    print(f"Comando desconocido: {comando}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
