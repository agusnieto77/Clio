"""
mover_imagen.py - Mueve una imagen procesada a i_procesadas/.

Uso:
    python harness/tools/mover_imagen.py <ruta> <imagen>

La subcarpeta i_procesadas/ se crea si no existe. La imagen se mueve
(atomicamente en el mismo volumen) y se reporta la nueva ubicacion.
Si la imagen no existe o ya esta en i_procesadas/, se reporta error.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from common import (
    carpeta_procesadas,
    emitir_error,
    emitir_ok,
    resolver_ruta,
    validar_subcarpeta,
)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Uso: python harness/tools/mover_imagen.py <ruta> <imagen>", file=sys.stderr)
        return 2

    ruta = resolver_ruta(argv[1])
    validar_subcarpeta(ruta)
    nombre_imagen = Path(argv[2]).name  # evitar paths cruzados

    origen = ruta / nombre_imagen
    if not origen.is_file():
        emitir_error(
            f"La imagen '{nombre_imagen}' no existe en {ruta}.",
            imagen=nombre_imagen,
        )
        return 1

    destino_dir = carpeta_procesadas(ruta)
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / nombre_imagen

    if destino.is_file():
        emitir_error(
            f"Ya existe '{nombre_imagen}' en i_procesadas/. No se sobrescribe.",
            imagen=nombre_imagen,
            destino=str(destino),
        )
        return 1

    try:
        shutil.move(str(origen), str(destino))
    except OSError as exc:
        emitir_error(
            f"No se pudo mover '{nombre_imagen}': {exc}",
            imagen=nombre_imagen,
        )
        return 1

    emitir_ok(
        f"Imagen movida a i_procesadas/.",
        imagen=nombre_imagen,
        origen=str(origen),
        destino=str(destino),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
