"""
checklist.py - Manejo de checklist.json de una subcarpeta.

Uso:
    python harness/tools/checklist.py <ruta> init
    python harness/tools/checklist.py <ruta> siguiente
    python harness/tools/checklist.py <ruta> marcar <imagen> <procesada|error|pendiente>
    python harness/tools/checklist.py <ruta> mostrar
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from common import (
    base_sin_extension,
    emitir_error,
    emitir_json,
    emitir_ok,
    escribir_checklist,
    leer_checklist,
    listar_imagenes_sueltas,
    resolver_ruta,
    validar_subcarpeta,
)


def _entrada_inicial(nombre_imagen: str) -> dict:
    return {
        "estado": "pendiente",
        "intentos": 0,
        "ultima_actualizacion": None,
        "detalle_error": None,
    }


def cmd_init(ruta: Path) -> int:
    sueltas = listar_imagenes_sueltas(ruta)
    data = leer_checklist(ruta)
    imgs = data.setdefault("imagenes", {})
    nuevas = 0
    for img in sueltas:
        if img.name not in imgs:
            imgs[img.name] = _entrada_inicial(img.name)
            nuevas += 1
        else:
            entrada = imgs[img.name]
            entrada.setdefault("estado", "pendiente")
            entrada.setdefault("intentos", 0)
            entrada.setdefault("ultima_actualizacion", None)
            entrada.setdefault("detalle_error", None)
    data["actualizado"] = datetime.now().isoformat(timespec="seconds")
    escribir_checklist(ruta, data)
    emitir_ok(
        f"Checklist inicializado. {nuevas} entradas nuevas de {len(sueltas)} imagenes sueltas.",
        total_imagenes_sueltas=len(sueltas),
        entradas_nuevas=nuevas,
        estados=_contar_estados(imgs),
    )
    return 0


def cmd_siguiente(ruta: Path) -> int:
    data = leer_checklist(ruta)
    imgs = data.get("imagenes", {})
    for nombre, entrada in imgs.items():
        if entrada.get("estado") == "pendiente":
            emitir_ok("Siguiente imagen pendiente", siguiente=nombre)
            return 0
    emitir_json({"ok": True, "mensaje": "No quedan imagenes pendientes", "siguiente": None})
    return 0


def cmd_marcar(ruta: Path, imagen: str, estado: str, detalle: str | None = None) -> int:
    if estado not in {"pendiente", "procesada", "error"}:
        emitir_error(f"Estado invalido: {estado}. Debe ser pendiente, procesada o error.")
        return 2
    data = leer_checklist(ruta)
    imgs = data.setdefault("imagenes", {})
    if imagen not in imgs:
        emitir_error(
            f"La imagen '{imagen}' no esta en checklist. Ejecuta primero: "
            f"python harness/tools/checklist.py {ruta} init"
        )
        return 2
    entrada = imgs[imagen]
    entrada["estado"] = estado
    entrada["ultima_actualizacion"] = datetime.now().isoformat(timespec="seconds")
    if estado == "procesada":
        entrada["detalle_error"] = None
    if estado == "error":
        entrada["intentos"] = int(entrada.get("intentos", 0)) + 1
        entrada["detalle_error"] = detalle or "(sin detalle)"
    data["actualizado"] = datetime.now().isoformat(timespec="seconds")
    escribir_checklist(ruta, data)
    emitir_ok(f"Imagen {imagen} marcada como {estado}.", imagen=imagen, estado=estado)
    return 0


def cmd_mostrar(ruta: Path) -> int:
    data = leer_checklist(ruta)
    imgs = data.get("imagenes", {})
    emitir_json(
        {
            "ok": True,
            "total": len(imgs),
            "por_estado": _contar_estados(imgs),
            "imagenes": imgs,
        }
    )
    return 0


def _contar_estados(imgs: dict) -> dict:
    out = {"pendiente": 0, "procesada": 0, "error": 0}
    for entrada in imgs.values():
        e = str(entrada.get("estado", "pendiente")).lower()
        out[e] = out.get(e, 0) + 1
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "Uso: python harness/tools/checklist.py <ruta> "
            "<init|siguiente|mostrar|marcar <imagen> <estado> [detalle]>",
            file=sys.stderr,
        )
        return 2

    ruta = resolver_ruta(argv[1])
    validar_subcarpeta(ruta)
    comando = argv[2].lower()

    if comando == "init":
        return cmd_init(ruta)
    if comando == "siguiente":
        return cmd_siguiente(ruta)
    if comando == "mostrar":
        return cmd_mostrar(ruta)
    if comando == "marcar":
        if len(argv) < 5:
            print(
                "Uso: python harness/tools/checklist.py <ruta> marcar <imagen> "
                "<procesada|error|pendiente> [detalle]",
                file=sys.stderr,
            )
            return 2
        imagen = argv[3]
        estado = argv[4].lower()
        detalle = argv[5] if len(argv) > 5 else None
        return cmd_marcar(ruta, imagen, estado, detalle)
    print(f"Comando desconocido: {comando}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
