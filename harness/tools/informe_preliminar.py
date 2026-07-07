"""
informe_preliminar.py - Genera informe_preliminar.html con tres columnas por imagen.

Para cada imagen en i_procesadas/ con transcripcion asociada, produce una
seccion con:
    1. Miniatura de la imagen original.
    2. Texto extraido por OCR.
    3. Top-10 palabras mas frecuentes sin stopwords de ese documento.

Uso:
    python harness/tools/informe_preliminar.py <ruta>
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

from common import (
    ARCHIVO_INFORME_HTML,
    SUBCARPETA_METRICAS,
    SUBCARPETA_PROCESADAS,
    base_sin_extension,
    carpeta_metricas,
    carpeta_procesadas,
    emitir_error,
    emitir_ok,
    leer_transcripcion,
    listar_imagenes_procesadas,
    resolver_ruta,
    validar_subcarpeta,
    escribir_log,
    asegurar_log,
)


def _cargar_top10(ruta: Path) -> dict[str, list[str]]:
    """Lee metricas/resumen_top10.csv y devuelve base -> [palabras]."""
    path = carpeta_metricas(ruta) / "resumen_top10.csv"
    out: dict[str, list[str]] = {}
    if path.is_file():
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for fila in reader:
                doc = fila.get("documento", "")
                if not doc.strip():
                    continue
                palabras = [
                    v for k, v in fila.items() if k and k.startswith("pal") and v.strip()
                ]
                out[doc] = palabras
    for base, palabras in _cargar_top10_json_faltante(ruta, set(out)).items():
        out[base] = palabras
    return out


def _cargar_top10_json_faltante(ruta: Path, bases_csv: set[str]) -> dict[str, list[str]]:
    path = carpeta_metricas(ruta) / "frecuencia_sin_stopwords.json"
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    faltantes: dict[str, list[str]] = {}
    for base, ranking in data.items():
        if base in bases_csv or not isinstance(ranking, list):
            continue
        palabras = []
        for item in ranking[:10]:
            if isinstance(item, list) and item:
                palabras.append(str(item[0]))
        faltantes[str(base)] = palabras
    return faltantes


def _cargar_transcripciones(ruta: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(ruta.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".txt", ".json"):
            continue
        base = base_sin_extension(p)
        # preferir .txt sobre .json si ambos existen
        if base not in out or p.suffix.lower() == ".txt":
            out[base] = leer_transcripcion(p)
    return out


def _css() -> str:
    return """
    body { font-family: Georgia, 'Times New Roman', serif; margin: 24px auto; max-width: 1100px; color: #222; line-height: 1.55; }
    h1 { border-bottom: 2px solid #444; padding-bottom: 8px; }
    h2 { margin-top: 2.5em; border-left: 6px solid #2c5282; padding-left: 10px; }
    .indice { background: #f5f7fa; border: 1px solid #d0d7de; padding: 12px 18px; border-radius: 6px; margin: 16px 0 32px; }
    .indice a { display: block; padding: 2px 0; }
    .seccion { display: grid; grid-template-columns: 1fr 2fr 1fr; gap: 18px; border: 1px solid #e0e0e0; padding: 16px; border-radius: 6px; margin-bottom: 28px; page-break-inside: avoid; }
    .col { min-width: 0; }
    .col h3 { margin-top: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; color: #666; }
    .miniatura img { max-width: 100%; height: auto; border: 1px solid #ccc; }
    .transcripcion { white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 13px; max-height: 520px; overflow: auto; background: #fafafa; padding: 8px; border-radius: 4px; }
    .top10 ol { padding-left: 20px; }
    .top10 li { font-family: Georgia, serif; }
    .vacia { color: #b00; font-style: italic; }
    @media print { .seccion { page-break-inside: avoid; } }
    """


def _anchor_id(base: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9_-]+", "-", base.strip()).strip("-").lower()
    return limpio or "imagen"


def _seccion_imagen(base: str, img_path: Path, transcripcion: str, top: list[str]) -> str:
    anchor = _anchor_id(base)
    miniatura = (
        f'<img src="{html.escape(SUBCARPETA_PROCESADAS + "/" + img_path.name)}" '
        f'alt="{html.escape(img_path.name)}" />'
    )
    if transcripcion.strip():
        trans_html = f'<div class="transcripcion">{html.escape(transcripcion)}</div>'
    else:
        trans_html = '<p class="vacia">(transcripcion vacia o no disponible)</p>'

    if top:
        items = "".join(f"<li>{html.escape(p)}</li>" for p in top)
        top_html = f"<ol>{items}</ol>"
    else:
        top_html = '<p class="vacia">(no calculado)</p>'

    return f"""
    <section class="seccion" id="{html.escape(anchor)}">
      <div class="col miniatura">
        <h3>Imagen original</h3>
        {miniatura}
        <p style="font-size:12px;color:#666;margin-top:6px;">{html.escape(img_path.name)}</p>
      </div>
      <div class="col">
        <h3>Texto extraido por OCR</h3>
        {trans_html}
      </div>
      <div class="col top10">
        <h3>10 palabras más frecuentes<br/>(sin palabras vacías)</h3>
        {top_html}
      </div>
    </section>
    """


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python harness/tools/informe_preliminar.py <ruta>", file=sys.stderr)
        return 2

    ruta = resolver_ruta(argv[1])
    validar_subcarpeta(ruta)

    imagenes = listar_imagenes_procesadas(ruta)
    if not imagenes:
        emitir_error(
            "No hay imagenes procesadas en i_procesadas/. "
            "Ejecuta primero la etapa OCR."
        )
        return 1

    transcripciones = _cargar_transcripciones(ruta)
    top10 = _cargar_top10(ruta)

    partes = [
        "<!DOCTYPE html>",
        '<html lang="es">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Informe preliminar - {html.escape(ruta.name)}</title>",
        f"<style>{_css()}</style>",
        "</head>",
        "<body>",
        f"<h1>Informe preliminar del subcorpus <em>{html.escape(ruta.name)}</em></h1>",
        "<p>Una seccion por imagen con tres columnas: miniatura, texto extraido por OCR y "
        "las diez palabras más frecuentes del documento (excluyendo palabras vacias como "
        "articulos y preposiciones). La transcripcion preserva la ortografia de epoca.</p>",
        '<nav class="indice"><strong>Índice</strong>',
    ]

    for img in imagenes:
        base = base_sin_extension(img)
        partes.append(
            f'<a href="#{html.escape(_anchor_id(base))}">{html.escape(img.name)}</a>'
        )

    partes.append("</nav>")

    for img in imagenes:
        base = base_sin_extension(img)
        trans = transcripciones.get(base, "")
        top = top10.get(base, [])
        partes.append(_seccion_imagen(base, img, trans, top))

    partes.append("</body></html>")

    salida = ruta / ARCHIVO_INFORME_HTML
    salida.write_text("\n".join(partes), encoding="utf-8")

    asegurar_log(ruta)
    escribir_log(ruta, f"INFORME PRELIMINAR - {len(imagenes)} secciones -> {ARCHIVO_INFORME_HTML}")

    emitir_ok(
        f"Informe preliminar generado con {len(imagenes)} secciones.",
        archivo=str(salida),
        n_secciones=len(imagenes),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
