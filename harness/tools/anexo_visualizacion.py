"""
anexo_visualizacion.py - Genera una nube de palabras del corpus completo.

Produce dos artefactos en la subcarpeta:
    - anexo_visualizacion_nube.html  (interactivo, Plotly)
    - anexo_visualizacion_nube.png   (vista estática)

Además inserta o actualiza un bloque canónico en `informe_final.md` para que el
anexo quede enlazado y visible desde el informe final.

Uso:
    python harness/tools/anexo_visualizacion.py <ruta>
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import plotly.colors as pc
import plotly.graph_objects as go
from PIL import ImageFont
from wordcloud import WordCloud

from common import (
    ARCHIVO_ANEXO_NUBE_HTML,
    ARCHIVO_ANEXO_NUBE_PNG,
    ARCHIVO_INFORME_MD,
    asegurar_log,
    carpeta_metricas,
    emitir_error,
    emitir_ok,
    escribir_log,
    leer_transcripcion,
    listar_transcripciones,
    resolver_ruta,
    validar_subcarpeta,
)
from tokenizacion import stopwords_espanol, tokenizar

ANEXO_START = "<!-- ANEXO_VISUALIZACION:START -->"
ANEXO_END = "<!-- ANEXO_VISUALIZACION:END -->"


def _cargar_frecuencias_metricas(ruta: Path) -> Counter[str]:
    path = carpeta_metricas(ruta) / "frecuencia_sin_stopwords.json"
    if not path.is_file():
        return Counter()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return Counter()
    if not isinstance(data, dict):
        return Counter()

    total: Counter[str] = Counter()
    for ranking in data.values():
        if not isinstance(ranking, list):
            continue
        for item in ranking:
            if not isinstance(item, list) or len(item) < 2:
                continue
            termino = str(item[0])
            try:
                frecuencia = int(item[1])
            except (TypeError, ValueError):
                continue
            total[termino] += frecuencia
    return total


def _cargar_frecuencias_transcripciones(ruta: Path) -> Counter[str]:
    sw = stopwords_espanol()
    total: Counter[str] = Counter()
    for path in listar_transcripciones(ruta):
        texto = leer_transcripcion(path)
        if not texto.strip():
            continue
        total.update(t for t in tokenizar(texto, 2) if t not in sw)
    return total


def _cargar_frecuencias_corpus(ruta: Path) -> Counter[str]:
    frecuencias = _cargar_frecuencias_metricas(ruta)
    if frecuencias:
        return frecuencias
    return _cargar_frecuencias_transcripciones(ruta)


def _color_func_builder(frecuencias: dict[str, int]):
    max_freq = max(frecuencias.values()) if frecuencias else 1
    min_freq = min(frecuencias.values()) if frecuencias else 0

    def _color(word: str, **_) -> str:
        freq = frecuencias.get(word, min_freq)
        escala = 0.5 if max_freq == min_freq else (freq - min_freq) / (max_freq - min_freq)
        return pc.sample_colorscale("Viridis", [escala])[0]

    return _color


def _crear_wordcloud(frecuencias: Counter[str]) -> WordCloud:
    wc = WordCloud(
        width=1600,
        height=900,
        background_color="white",
        collocations=False,
        prefer_horizontal=0.92,
        random_state=42,
        margin=8,
    )
    wc.generate_from_frequencies(dict(frecuencias))
    wc.recolor(color_func=_color_func_builder(dict(frecuencias)), random_state=42)
    return wc


def _layout_to_plotly(wc: WordCloud, frecuencias: dict[str, int]) -> go.Figure:
    fig = go.Figure()
    min_freq = min(frecuencias.values()) if frecuencias else 0
    max_freq = max(frecuencias.values()) if frecuencias else 1

    fig.add_trace(
        go.Scatter(
            x=[0, 0],
            y=[0, 0],
            mode="markers",
            marker=dict(
                size=0.1,
                color=[min_freq, max_freq],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Frecuencia"),
            ),
            opacity=0,
            hoverinfo="skip",
            showlegend=False,
        )
    )

    for item in wc.layout_:
        (word, _weight), font_size, position, orientation, color = item
        font = ImageFont.truetype(wc.font_path, font_size)
        bbox = font.getbbox(word)
        ancho = max(1, bbox[2] - bbox[0])
        alto = max(1, bbox[3] - bbox[1])
        if orientation is not None:
            ancho, alto = alto, ancho
        x = position[1] + (ancho / 2)
        y = wc.height - (position[0] + (alto / 2))
        angulo = 90 if orientation is not None else 0
        frecuencia = int(frecuencias.get(word, 0))

        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="text",
                text=[word],
                textfont=dict(size=font_size, color=color, family="DejaVu Sans"),
                textangle=angulo,
                hovertemplate=f"{word}<br>Frecuencia: {frecuencia}<extra></extra>",
                showlegend=False,
            )
        )

    fig.update_xaxes(visible=False, range=[0, wc.width])
    fig.update_yaxes(visible=False, range=[0, wc.height], scaleanchor="x", scaleratio=1)
    fig.update_layout(
        title=f"Nube de palabras del corpus completo: {len(wc.words_)} términos visibles",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def _render_html(fig: go.Figure, ruta: Path, total_documentos: int, total_terminos: int) -> str:
    plot = fig.to_html(include_plotlyjs="inline", full_html=False, config={"responsive": True})
    return f"""<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Anexo de visualización - {ruta.name}</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; margin: 24px auto; max-width: 1280px; color: #1f2933; }}
    h1 {{ border-bottom: 2px solid #334e68; padding-bottom: 8px; }}
    .nota {{ background: #f7fafc; border: 1px solid #d9e2ec; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; }}
  </style>
</head>
<body>
  <h1>Anexo de visualización del subcorpus <em>{ruta.name}</em></h1>
  <div class=\"nota\">
    <p>Esta nube de palabras resume el corpus completo del subcorpus, agregando todas las transcripciones válidas. El tamaño y el color de cada término representan su frecuencia relativa dentro del conjunto total de documentos. La paleta usada es Viridis.</p>
    <p><strong>Documentos considerados:</strong> {total_documentos}. <strong>Términos distintos:</strong> {total_terminos}.</p>
  </div>
  {plot}
</body>
</html>
"""


def _bloque_anexo() -> str:
    return f"""{ANEXO_START}
## Anexo de visualización

### Nube de palabras del corpus completo

Este anexo resume el conjunto completo del subcorpus en una nube de palabras donde el tamaño y la escala de color de cada término representan su frecuencia agregada en todas las transcripciones válidas. La paleta usada es Viridis.

- Vista interactiva: `{ARCHIVO_ANEXO_NUBE_HTML}`
- Vista estática: `{ARCHIVO_ANEXO_NUBE_PNG}`

[Abrir nube interactiva]({ARCHIVO_ANEXO_NUBE_HTML})

![Nube de palabras del corpus completo]({ARCHIVO_ANEXO_NUBE_PNG})
{ANEXO_END}
"""


def _actualizar_informe_final(ruta: Path) -> Path:
    path = ruta / ARCHIVO_INFORME_MD
    bloque = _bloque_anexo().strip()
    contenido = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else f"# Informe final del subcorpus `{ruta.name}`\n\n"

    if ANEXO_START in contenido and ANEXO_END in contenido:
        inicio = contenido.index(ANEXO_START)
        fin = contenido.index(ANEXO_END) + len(ANEXO_END)
        nuevo = contenido[:inicio].rstrip() + "\n\n" + bloque + "\n" + contenido[fin:].lstrip()
    elif "## Anexo: sobre la transcripcion" in contenido:
        idx = contenido.index("## Anexo: sobre la transcripcion")
        nuevo = contenido[:idx].rstrip() + "\n\n" + bloque + "\n\n" + contenido[idx:].lstrip()
    else:
        nuevo = contenido.rstrip() + "\n\n" + bloque + "\n"

    path.write_text(nuevo, encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python harness/tools/anexo_visualizacion.py <ruta>", file=sys.stderr)
        return 2

    ruta = resolver_ruta(argv[1])
    validar_subcarpeta(ruta)

    frecuencias = _cargar_frecuencias_corpus(ruta)
    if not frecuencias:
        emitir_error("No hay frecuencias suficientes para construir la nube del corpus completo.")
        return 1

    total_documentos = len([p for p in listar_transcripciones(ruta) if leer_transcripcion(p).strip()])
    wc = _crear_wordcloud(frecuencias)
    png_path = ruta / ARCHIVO_ANEXO_NUBE_PNG
    html_path = ruta / ARCHIVO_ANEXO_NUBE_HTML
    wc.to_file(str(png_path))
    fig = _layout_to_plotly(wc, dict(frecuencias))
    html_path.write_text(_render_html(fig, ruta, total_documentos, len(frecuencias)), encoding="utf-8")
    md_path = _actualizar_informe_final(ruta)

    asegurar_log(ruta)
    escribir_log(
        ruta,
        f"ANEXO VISUALIZACION - documentos={total_documentos} - terminos={len(frecuencias)} - html={ARCHIVO_ANEXO_NUBE_HTML} - png={ARCHIVO_ANEXO_NUBE_PNG}",
    )

    emitir_ok(
        "Anexo de visualización generado e insertado en el informe final.",
        archivo_html=str(html_path),
        archivo_png=str(png_path),
        archivo_md=str(md_path),
        n_documentos=total_documentos,
        n_terminos=len(frecuencias),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
