from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUENTES = ROOT / "Fuentes"
TOOLS = ROOT / "harness" / "tools"
TMP_ROOT = FUENTES / "_tmp_clio_validation_regression"

sys.path.insert(0, str(TOOLS))

from common import (  # noqa: E402
    ARCHIVOS_METRICAS_ESPERADOS,
    leer_transcripcion,
    listar_transcripciones,
)


def _run_tool(*args: str) -> tuple[int, dict]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(result.stdout or result.stderr) from exc
    return result.returncode, payload


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _reset_case(name: str) -> Path:
    ruta = TMP_ROOT / name
    if ruta.exists():
        shutil.rmtree(ruta)
    ruta.mkdir(parents=True)
    return ruta


def test_common_ignores_checklist_but_accepts_ocr_json() -> None:
    # Given: one processed image, its OCR JSON, and Clio system JSON.
    ruta = _reset_case("common_json_filter")
    (ruta / "i_procesadas").mkdir()
    (ruta / "i_procesadas" / "doc 1.jpg").write_bytes(b"fake")
    _write_json(ruta / "doc 1.json", {"transcripcion": "Texto OCR valido"})
    _write_json(ruta / "checklist.json", {"imagenes": {}})

    # When: transcription discovery runs.
    discovered = [path.name for path in listar_transcripciones(ruta)]

    # Then: only the OCR JSON is treated as a transcription.
    assert discovered == ["doc 1.json"]


def test_transcripciones_fail_when_pending_images_have_zero_processed_docs() -> None:
    # Given: OCR has source work pending but no processed valid transcription.
    ruta = _reset_case("zero_processed")
    (ruta / "pendiente.jpg").write_bytes(b"fake")
    _write_json(
        ruta / "checklist.json",
        {"imagenes": {"pendiente.jpg": {"estado": "pendiente"}}},
    )

    # When: Clio validates transcriptions.
    code, payload = _run_tool("harness/tools/validar.py", "transcripciones", str(ruta))

    # Then: validation blocks analysis instead of accepting an empty OCR stage.
    assert code == 1
    assert payload["ok"] is False
    assert payload["total_transcripciones_validas"] == 0


def test_estado_stops_empty_subfolder_instead_of_analysis() -> None:
    # Given: a Clio subfolder without images or transcriptions.
    ruta = _reset_case("empty_subfolder")

    # When: state is reconstructed.
    code, payload = _run_tool("harness/tools/estado.py", str(ruta), "resumen")

    # Then: the workflow stops as an empty subfolder instead of entering analysis.
    assert code == 0
    assert payload["imagenes_total"] == 0
    assert payload["transcripciones"] == []
    assert payload["punto_reanudacion"] == "detenido"
    assert payload["motivo_reanudacion"] == "SUBCARPETA VACIA"


def test_transcripciones_prefer_valid_txt_over_empty_optional_json() -> None:
    # Given: OCR produced the required txt and an optional empty json for the same image.
    ruta = _reset_case("txt_preferred_over_json")
    (ruta / "i_procesadas").mkdir()
    (ruta / "doc.jpg").write_bytes(b"fake")
    shutil.move(ruta / "doc.jpg", ruta / "i_procesadas" / "doc.jpg")
    (ruta / "doc.txt").write_text("texto valido desde txt", encoding="utf-8")
    _write_json(ruta / "doc.json", {"transcripcion": ""})

    # When: transcription discovery and validation run.
    discovered = [path.name for path in listar_transcripciones(ruta)]
    code, payload = _run_tool("harness/tools/validar.py", "transcripciones", str(ruta))

    # Then: the valid txt wins, the optional json is not double-counted, and validation passes.
    assert discovered == ["doc.txt"]
    assert code == 0
    assert payload["ok"] is True
    assert payload["total_transcripciones"] == 1
    assert payload["total_transcripciones_validas"] == 1


def test_metricas_fail_when_corpus_document_count_is_wrong() -> None:
    # Given: one valid processed transcription but metric metadata claims two docs.
    ruta = _reset_case("metricas_wrong_count")
    (ruta / "i_procesadas").mkdir()
    (ruta / "i_procesadas" / "doc.jpg").write_bytes(b"fake")
    (ruta / "doc.txt").write_text("texto valido", encoding="utf-8")
    metricas = ruta / "metricas"
    metricas.mkdir()
    payload = {"doc": [["texto", 1]]}
    for nombre in [
        "frecuencia.json",
        "frecuencia_sin_stopwords.json",
        "co_ocurrencia.json",
        "correlacion.json",
        "tfidf.json",
    ]:
        _write_json(metricas / nombre, payload)
    (metricas / "resumen_top10.csv").write_text(
        "documento,pal1\ndoc,texto\n__SUBCORPUS__,texto\n",
        encoding="utf-8",
    )
    _write_json(
        metricas / "versiones.json",
        {"resumen_corpus": {"n_documentos": 2, "n_terminos_unicos": 1}},
    )

    # When: metric validation runs.
    code, payload = _run_tool("harness/tools/validar.py", "metricas", str(ruta))

    # Then: the inconsistent corpus count is rejected.
    assert code == 1
    assert payload["ok"] is False
    assert any(item["archivo"] == "versiones.json" for item in payload["invalidos"])


def test_metricas_one_document_generated_metrics_validate() -> None:
    # Given: one valid processed transcription, the smallest legitimate corpus.
    ruta = _reset_case("metricas_one_document")
    (ruta / "i_procesadas").mkdir()
    (ruta / "doc.jpg").write_bytes(b"fake")
    shutil.move(ruta / "doc.jpg", ruta / "i_procesadas" / "doc.jpg")
    (ruta / "doc.txt").write_text(
        "puerto pesca trabajo sindicato convenio salario marineros",
        encoding="utf-8",
    )

    # When: deterministic metrics are generated and validated.
    metric_code, metric_payload = _run_tool("harness/tools/metricas.py", str(ruta))
    code, payload = _run_tool("harness/tools/validar.py", "metricas", str(ruta))

    # Then: single-document correlation shape with nota is accepted.
    assert metric_code == 0
    assert metric_payload["ok"] is True
    assert code == 0
    assert payload["ok"] is True
    assert payload["invalidos"] == []


def test_metricas_fail_when_top10_csv_document_key_is_wrong() -> None:
    # Given: the valid transcription key preserves a trailing space, but CSV trims it.
    ruta = _reset_case("metricas_wrong_csv_key")
    (ruta / "i_procesadas").mkdir()
    imagen = "doc 1 .jpg"
    (ruta / "i_procesadas" / imagen).write_bytes(b"fake")
    (ruta / "doc 1 .txt").write_text("texto valido", encoding="utf-8")
    metricas = ruta / "metricas"
    metricas.mkdir()
    _write_json(metricas / "frecuencia.json", {"doc 1 ": [["texto", 1]]})
    _write_json(metricas / "frecuencia_sin_stopwords.json", {"doc 1 ": [["texto", 1]]})
    _write_json(metricas / "co_ocurrencia.json", {"ventana": 5, "por_documento": {"doc 1 ": []}})
    _write_json(
        metricas / "correlacion.json",
        {
            "top_n": 20,
            "terminos": ["texto"],
            "matriz": [],
            "nota": "Menos de 2 documentos; correlacion no calculable.",
        },
    )
    _write_json(
        metricas / "tfidf.json",
        {"n_documentos": 1, "por_documento": {"doc 1 ": []}},
    )
    (metricas / "resumen_top10.csv").write_text(
        "documento,pal1\ndoc 1,texto\n__SUBCORPUS__,texto\n",
        encoding="utf-8",
    )
    _write_json(
        metricas / "versiones.json",
        {"resumen_corpus": {"n_documentos": 1, "n_terminos_unicos": 1}},
    )

    # When: metric validation runs.
    code, payload = _run_tool("harness/tools/validar.py", "metricas", str(ruta))

    # Then: row count alone is not enough; exact document keys must match.
    assert code == 1
    assert payload["ok"] is False
    assert any(item["archivo"] == "resumen_top10.csv" for item in payload["invalidos"])


def test_informes_fail_when_reports_are_skeletal() -> None:
    # Given: files exist but contain no real preliminary/final report structure.
    ruta = _reset_case("skeletal_reports")
    (ruta / "i_procesadas").mkdir()
    (ruta / "i_procesadas" / "doc.jpg").write_bytes(b"fake")
    (ruta / "doc.txt").write_text("texto valido", encoding="utf-8")
    (ruta / "informe_preliminar.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
    (ruta / "informe_final.md").write_text("# Informe final\n", encoding="utf-8")

    # When: report validation runs.
    code, payload = _run_tool("harness/tools/validar.py", "informes", str(ruta))

    # Then: non-empty placeholder reports are not accepted.
    assert code == 1
    assert payload["ok"] is False


def test_estado_does_not_retry_errored_images_as_plain_pending() -> None:
    # Given: an image remains in the source folder but checklist marks it as OCR error.
    ruta = _reset_case("errored_source_image")
    (ruta / "fallida.jpg").write_bytes(b"fake")
    _write_json(
        ruta / "checklist.json",
        {"imagenes": {"fallida.jpg": {"estado": "error", "intentos": 3}}},
    )

    # When: state is reconstructed.
    code, payload = _run_tool("harness/tools/estado.py", str(ruta), "resumen")

    # Then: Clio reports intervention instead of ordinary OCR retry.
    assert code == 0
    assert payload["imagenes_pendientes_ocr"] == []
    assert payload["imagenes_en_error"] == ["fallida.jpg"]
    assert payload["punto_reanudacion"] == "detenido"


def test_informe_preliminar_keeps_trailing_space_key_and_safe_anchor() -> None:
    # Given: a processed example-style filename whose document key ends in space.
    ruta = _reset_case("informe_anchor")
    (ruta / "i_procesadas").mkdir()
    imagen = "doc especial 1 .jpg"
    (ruta / "i_procesadas" / imagen).write_bytes(b"fake")
    (ruta / "doc especial 1 .txt").write_text("texto visible", encoding="utf-8")
    metricas = ruta / "metricas"
    metricas.mkdir()
    (metricas / "resumen_top10.csv").write_text(
        "documento,pal1\ndoc especial 1 ,visible\n__SUBCORPUS__,visible\n",
        encoding="utf-8",
    )

    # When: the preliminary report is generated.
    code, payload = _run_tool("harness/tools/informe_preliminar.py", str(ruta))
    contenido = (ruta / "informe_preliminar.html").read_text(encoding="utf-8")

    # Then: top-10 lookup still uses the trailing-space key, but HTML ids are safe.
    assert code == 0
    assert payload["ok"] is True
    assert "<li>visible</li>" in contenido
    assert 'id="doc-especial-1"' in contenido
    assert 'href="#doc-especial-1"' in contenido


def test_informe_preliminar_falls_back_to_json_top10_when_csv_misses_document() -> None:
    # Given: CSV has only the aggregate row, but JSON has document-level top terms.
    ruta = _reset_case("informe_top10_fallback")
    (ruta / "i_procesadas").mkdir()
    (ruta / "doc.jpg").write_bytes(b"fake")
    shutil.move(ruta / "doc.jpg", ruta / "i_procesadas" / "doc.jpg")
    (ruta / "doc.txt").write_text("texto visible", encoding="utf-8")
    metricas = ruta / "metricas"
    metricas.mkdir()
    (metricas / "resumen_top10.csv").write_text(
        "documento,pal1\n__SUBCORPUS__,agregado\n",
        encoding="utf-8",
    )
    _write_json(
        metricas / "frecuencia_sin_stopwords.json",
        {"doc": [["fallback", 3], ["termino", 2]]},
    )

    # When: the preliminary report is generated.
    code, payload = _run_tool("harness/tools/informe_preliminar.py", str(ruta))
    contenido = (ruta / "informe_preliminar.html").read_text(encoding="utf-8")

    # Then: document top terms are recovered from JSON instead of rendering no calculado.
    assert code == 0
    assert payload["ok"] is True
    assert "<li>fallback</li>" in contenido
    assert "<li>termino</li>" in contenido
    assert "(no calculado)" not in contenido


def test_archivos_metricas_esperados_single_source_of_truth() -> None:
    # Given: los tres modulos que antes duplicaban la constante.
    import importlib

    estado = importlib.import_module("estado")
    validar = importlib.import_module("validar")
    metricas = importlib.import_module("metricas")

    # When: se compara cada modulo contra common.
    # Then: nadie redefine la lista localmente; todos apuntan al mismo objeto.
    assert estado.ARCHIVOS_METRICAS_ESPERADOS is ARCHIVOS_METRICAS_ESPERADOS
    assert validar.ARCHIVOS_METRICAS_ESPERADOS is ARCHIVOS_METRICAS_ESPERADOS
    assert metricas.ARCHIVOS_METRICAS_ESPERADOS is ARCHIVOS_METRICAS_ESPERADOS
    assert ARCHIVOS_METRICAS_ESPERADOS == [
        "frecuencia.json",
        "frecuencia_sin_stopwords.json",
        "co_ocurrencia.json",
        "correlacion.json",
        "tfidf.json",
        "resumen_top10.csv",
        "versiones.json",
    ]


def test_leer_transcripcion_unifica_lectura_txt_y_json() -> None:
    # Given: un .txt y un .json de transcripcion con el mismo contenido esperado.
    ruta = _reset_case("leer_transcripcion_unified")
    txt_path = ruta / "doc.txt"
    json_path = ruta / "doc.json"
    txt_path.write_text("texto plano", encoding="utf-8")
    _write_json(json_path, {"transcripcion": "texto estructurado"})

    # When: se lee por la funcion unificada.
    # Then: cada formato devuelve su contenido sin duplicar logica.
    assert leer_transcripcion(txt_path) == "texto plano"
    assert leer_transcripcion(json_path) == "texto estructurado"
    # .json sin campo transcripcion -> ""
    vacio = ruta / "vacio.json"
    _write_json(vacio, {"otro_campo": 1})
    assert leer_transcripcion(vacio) == ""
    # .json invalido -> ""
    roto = ruta / "roto.json"
    roto.write_text("{no es json", encoding="utf-8")
    assert leer_transcripcion(roto) == ""


def test_modulos_no_redefinen_logica_de_lectura_de_transcripcion() -> None:
    # Given: los modulos que antes tenian helpers locales duplicados.
    import importlib

    validar = importlib.import_module("validar")
    informe = importlib.import_module("informe_preliminar")
    metricas = importlib.import_module("metricas")

    # Then: ya no existen los helpers privados duplicados.
    assert not hasattr(validar, "_contenido_transcripcion")
    assert not hasattr(metricas, "_texto_transcripcion")
    # informe_preliminar ya no reimplementa la lectura en _cargar_transcripciones:
    # su cuerpo debe delegar en leer_transcripcion.
    import inspect

    fuente = inspect.getsource(informe._cargar_transcripciones)
    assert "leer_transcripcion(" in fuente
    assert "json.load" not in fuente


def test_correlacion_es_determinista_entre_corridas() -> None:
    # Given: el bug clasico de Counter.update(set(tokens)): set() pierde el
    # orden de insercion y, al combinarse con most_common(top_n) sobre empates,
    # produce salidas distintas entre procesos Python (PYTHONHASHSEED varia).
    # Para forzar el fallo sin depender del hash seed del proceso, verificamos
    # el contrato: la implementacion NO debe usar set(tokens) sobre los docs.
    import importlib
    import inspect

    correlacion = importlib.import_module("correlacion")
    fuente = inspect.getsource(correlacion.calcular_correlacion)
    assert "set(tokens)" not in fuente, (
        "correlacion.calcular_correlacion usa set(tokens), que pierde el orden "
        "de insercion y rompe el determinismo de most_common(top_n) cuando hay "
        "empates de frecuencia. Usar dict.fromkeys(tokens) para preservar el "
        "orden de primera aparicion y lograr reproducibilidad entre corridas."
    )


if __name__ == "__main__":
    try:
        test_common_ignores_checklist_but_accepts_ocr_json()
        test_transcripciones_fail_when_pending_images_have_zero_processed_docs()
        test_estado_stops_empty_subfolder_instead_of_analysis()
        test_transcripciones_prefer_valid_txt_over_empty_optional_json()
        test_metricas_fail_when_corpus_document_count_is_wrong()
        test_metricas_one_document_generated_metrics_validate()
        test_metricas_fail_when_top10_csv_document_key_is_wrong()
        test_informes_fail_when_reports_are_skeletal()
        test_estado_does_not_retry_errored_images_as_plain_pending()
        test_informe_preliminar_keeps_trailing_space_key_and_safe_anchor()
        test_informe_preliminar_falls_back_to_json_top10_when_csv_misses_document()
        test_archivos_metricas_esperados_single_source_of_truth()
        test_leer_transcripcion_unifica_lectura_txt_y_json()
        test_modulos_no_redefinen_logica_de_lectura_de_transcripcion()
        test_correlacion_es_determinista_entre_corridas()
    finally:
        if TMP_ROOT.exists():
            shutil.rmtree(TMP_ROOT)

