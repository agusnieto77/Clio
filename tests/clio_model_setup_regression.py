from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "harness" / "tools"
TMP_ROOT = ROOT / "tests" / "_tmp_model_setup"

sys.path.insert(0, str(TOOLS))

import common  # noqa: E402
import auditoria_modelos as am  # noqa: E402
import configurar_modelos as cm  # noqa: E402
import swap_modelo as sm  # noqa: E402


def _reset_repo(name: str) -> Path:
    repo = TMP_ROOT / name
    if repo.exists():
        shutil.rmtree(repo)
    (repo / "harness").mkdir(parents=True)
    (repo / ".opencode" / "agents").mkdir(parents=True)
    return repo


def _copy_presets(repo: Path) -> None:
    shutil.copy2(ROOT / "harness" / "modelos.default.json", repo / "harness" / "modelos.default.json")
    shutil.copy2(
        ROOT / "harness" / "modelos.recommended.json",
        repo / "harness" / "modelos.recommended.json",
    )


def _write_agent(repo: Path, rol: str, model: str = "dummy/old-model") -> None:
    contenido = (
        "---\n"
        f"description: {rol}\n"
        "mode: subagent\n"
        f"model: {model}\n"
        'color: "primary"\n'
        "---\n"
    )
    (repo / ".opencode" / "agents" / f"{rol}.md").write_text(
        contenido,
        encoding="utf-8",
    )


def _write_modelos(
    repo: Path,
    principal: str = "proveedor/principal",
    respaldo: str = "proveedor/respaldo",
) -> None:
    payload = {
        "agentes": {
            rol: {
                "principal": {"id_opencode": principal},
                "respaldo": {"id_opencode": respaldo},
            }
            for rol in sm.ROLES_VALIDOS
        },
        "parametros_analisis": {
            "ventana_cocurrencia": 5,
            "stopwords_idioma": "español",
            "normalizacion_ortografica": "no_aplicar_en_transcripcion_primaria",
            "stopwords_fuente": "local",
            "tfidf_norma": "l2",
            "tfidf_sublinear_tf": True,
            "min_longitud_token": 2,
            "top_n_frecuencia": 10,
        },
    }
    (repo / "harness" / "modelos.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _reset_fuentes_case(repo: Path, name: str) -> Path:
    ruta = repo / "Fuentes" / "_tmp_model_setup" / name
    if ruta.exists():
        shutil.rmtree(ruta)
    ruta.mkdir(parents=True)
    return ruta


def _patch_repo_root(repo: Path) -> tuple[Path, Path]:
    original_common = common.REPO_RAIZ
    original_swap = sm.REPO_RAIZ
    common.REPO_RAIZ = repo
    sm.REPO_RAIZ = repo
    return original_common, original_swap


def _restore_repo_root(original_common: Path, original_swap: Path) -> None:
    common.REPO_RAIZ = original_common
    sm.REPO_RAIZ = original_swap


def _leer_auditorias_modelo(ruta: Path) -> list[dict]:
    log = (ruta / "log_clio.md").read_text(encoding="utf-8")
    auditorias = []
    for linea in log.splitlines():
        marcador = "AUDITORIA_MODELO "
        if marcador not in linea:
            continue
        auditorias.append(json.loads(linea.split(marcador, 1)[1]))
    return auditorias


def _assert_auto_swap_third_failure(repo: Path, rol: str) -> None:
    ruta = _reset_fuentes_case(repo, f"auto_swap_{rol}")
    (ruta / "checklist.json").write_text('{"imagenes": {}}\n', encoding="utf-8")
    _write_modelos(repo)
    _write_agent(repo, rol, "proveedor/principal")
    original_common, original_swap = _patch_repo_root(repo)
    try:
        for esperado in (1, 2):
            code = sm.main([
                "swap_modelo.py",
                rol,
                "--auto",
                str(ruta),
                f"fallo de modelo {rol}",
            ])
            assert code == 0
            data = json.loads((ruta / "checklist.json").read_text(encoding="utf-8"))
            assert data["agentes"][rol]["fallos_modelo_consecutivos"] == esperado
            agent_text = (repo / ".opencode" / "agents" / f"{rol}.md").read_text(encoding="utf-8")
            assert "model: proveedor/principal" in agent_text

        code = sm.main([
            "swap_modelo.py",
            rol,
            "--auto",
            str(ruta),
            f"fallo de modelo {rol}",
        ])
        assert code == 0
        data = json.loads((ruta / "checklist.json").read_text(encoding="utf-8"))
        assert data["agentes"][rol]["fallos_modelo_consecutivos"] == 0
        assert data["agentes"][rol]["ultimo_modelo_registrado"] == "proveedor/respaldo"
        agent_text = (repo / ".opencode" / "agents" / f"{rol}.md").read_text(encoding="utf-8")
        assert "model: proveedor/respaldo" in agent_text
    finally:
        _restore_repo_root(original_common, original_swap)
        if ruta.exists():
            shutil.rmtree(ruta)


def test_presets_cargan_y_validan() -> None:
    for preset in ("default", "recommended"):
        config = cm._cargar_preset(ROOT, preset)
        assert config["preset"] == preset
        cm._validar_modelos(config)


def test_aplicar_preset_escribe_modelos_y_sincroniza_agents() -> None:
    repo = _reset_repo("aplicar_preset")
    _copy_presets(repo)
    for rol in cm.ROLES:
        _write_agent(repo, rol)
    (repo / "harness" / "modelos.json").write_text("{}\n", encoding="utf-8")

    config = cm._cargar_preset(repo, "default")
    backup, modelos = cm._aplicar_config(repo, config)

    assert backup is not None
    assert backup.is_file()
    assert modelos.is_file()

    saved = json.loads(modelos.read_text(encoding="utf-8"))
    assert saved["preset"] == "default"
    for rol in cm.ROLES:
        principal = config["agentes"][rol]["principal"]["id_opencode"]
        agent_text = (repo / ".opencode" / "agents" / f"{rol}.md").read_text(
            encoding="utf-8"
        )
        assert f"model: {principal}" in agent_text


def test_sincronizar_agents_tolera_modelo_ya_actualizado() -> None:
    repo = _reset_repo("sync_idempotente")
    _copy_presets(repo)
    config = cm._cargar_preset(repo, "recommended")
    for rol in cm.ROLES:
        principal = config["agentes"][rol]["principal"]["id_opencode"]
        _write_agent(repo, rol, principal)

    cm._sincronizar_agents(repo, config)

    for rol in cm.ROLES:
        principal = config["agentes"][rol]["principal"]["id_opencode"]
        agent_text = (repo / ".opencode" / "agents" / f"{rol}.md").read_text(
            encoding="utf-8"
        )
        assert f"model: {principal}" in agent_text


def test_validacion_falla_si_falta_un_rol() -> None:
    config = cm._cargar_preset(ROOT, "recommended")
    del config["agentes"]["clio"]
    try:
        cm._validar_modelos(config)
    except cm.ModelosConfigError as exc:
        assert "clio" in str(exc)
    else:
        raise AssertionError("La validación debía fallar si falta un rol.")


def test_auto_swap_cambia_a_respaldo_en_tercer_fallo() -> None:
    repo = _reset_repo("auto_swap_tercer_fallo")
    _assert_auto_swap_third_failure(repo, "ocr-historico")


def test_auto_swap_cambia_a_respaldo_en_tercer_fallo_analista() -> None:
    repo = _reset_repo("auto_swap_tercer_fallo_analista")
    _assert_auto_swap_third_failure(repo, "analista-cuantitativo")


def test_auto_swap_cambia_a_respaldo_en_tercer_fallo_redactor() -> None:
    repo = _reset_repo("auto_swap_tercer_fallo_redactor")
    _assert_auto_swap_third_failure(repo, "redactor-informes")


def test_auto_swap_reinicia_contador_en_exito() -> None:
    repo = _reset_repo("auto_swap_reset_exito")
    ruta = _reset_fuentes_case(repo, "auto_swap_reset_exito")
    (ruta / "checklist.json").write_text('{"imagenes": {}}\n', encoding="utf-8")
    _write_modelos(repo)
    _write_agent(repo, "ocr-historico", "proveedor/principal")
    original_common, original_swap = _patch_repo_root(repo)
    try:
        code = sm.main([
            "swap_modelo.py",
            "ocr-historico",
            "--auto",
            str(ruta),
            "fallo 1",
        ])
        assert code == 0
        code = sm.main([
            "swap_modelo.py",
            "ocr-historico",
            "--exito",
            str(ruta),
        ])
        assert code == 0
        data = json.loads((ruta / "checklist.json").read_text(encoding="utf-8"))
        assert data["agentes"]["ocr-historico"]["fallos_modelo_consecutivos"] == 0

        code = sm.main([
            "swap_modelo.py",
            "ocr-historico",
            "--auto",
            str(ruta),
            "fallo 2",
        ])
        assert code == 0
        data = json.loads((ruta / "checklist.json").read_text(encoding="utf-8"))
        assert data["agentes"]["ocr-historico"]["fallos_modelo_consecutivos"] == 1
    finally:
        _restore_repo_root(original_common, original_swap)
        if ruta.exists():
            shutil.rmtree(ruta)


def test_auto_swap_escribe_auditoria_estructurada_en_log() -> None:
    repo = _reset_repo("auto_swap_log_auditoria")
    ruta = _reset_fuentes_case(repo, "auto_swap_log_auditoria")
    (ruta / "checklist.json").write_text('{"imagenes": {}}\n', encoding="utf-8")
    _write_modelos(repo)
    _write_agent(repo, "ocr-historico", "proveedor/principal")
    original_common, original_swap = _patch_repo_root(repo)
    try:
        sm.main([
            "swap_modelo.py",
            "ocr-historico",
            "--auto",
            str(ruta),
            "modelo no disponible",
        ])
        sm.main([
            "swap_modelo.py",
            "ocr-historico",
            "--auto",
            str(ruta),
            "modelo no disponible",
        ])
        sm.main([
            "swap_modelo.py",
            "ocr-historico",
            "--auto",
            str(ruta),
            "modelo no disponible",
        ])
        sm.main([
            "swap_modelo.py",
            "ocr-historico",
            "--exito",
            str(ruta),
        ])

        auditorias = _leer_auditorias_modelo(ruta)
        assert [item["evento"] for item in auditorias] == [
            "fallo_registrado",
            "fallo_registrado",
            "swap_automatico",
            "exito_modelo",
        ]
        assert auditorias[0]["rol"] == "ocr-historico"
        assert auditorias[0]["detalle"] == "modelo no disponible"
        assert auditorias[2]["swap_ejecutado"] is True
        assert auditorias[2]["modelo_anterior"] == "proveedor/principal"
        assert auditorias[2]["modelo_nuevo"] == "proveedor/respaldo"
        assert auditorias[3]["fallos_consecutivos"] == 0
    finally:
        _restore_repo_root(original_common, original_swap)
        if ruta.exists():
            shutil.rmtree(ruta)


def test_auditoria_modelos_resume_por_subcarpeta_y_rol() -> None:
    repo = _reset_repo("auditoria_modelos_resumen")
    ruta_a = _reset_fuentes_case(repo, "auditoria_a")
    ruta_b = _reset_fuentes_case(repo, "auditoria_b")
    for ruta, rol in ((ruta_a, "ocr-historico"), (ruta_b, "analista-cuantitativo")):
        (ruta / "checklist.json").write_text('{"imagenes": {}}\n', encoding="utf-8")
        _write_modelos(repo)
        _write_agent(repo, rol, "proveedor/principal")
        original_common, original_swap = _patch_repo_root(repo)
        try:
            sm.main(["swap_modelo.py", rol, "--auto", str(ruta), "fallo 1"])
            sm.main(["swap_modelo.py", rol, "--auto", str(ruta), "fallo 2"])
            sm.main(["swap_modelo.py", rol, "--auto", str(ruta), "fallo 3"])
        finally:
            _restore_repo_root(original_common, original_swap)

    original_common = common.REPO_RAIZ
    original_swap = sm.REPO_RAIZ
    original_auditoria = am.REPO_RAIZ
    common.REPO_RAIZ = repo
    sm.REPO_RAIZ = repo
    am.REPO_RAIZ = repo
    try:
        resumen = am._resumir(repo / "Fuentes")
    finally:
        common.REPO_RAIZ = original_common
        sm.REPO_RAIZ = original_swap
        am.REPO_RAIZ = original_auditoria

    assert resumen["logs_revisados"] == 2
    assert resumen["subcarpetas_con_auditoria"] == 2
    assert resumen["total_swaps"] == 2
    assert resumen["por_rol"]["ocr-historico"]["total_swaps"] == 1
    assert resumen["por_rol"]["analista-cuantitativo"]["total_swaps"] == 1
    assert any("auditoria_a" in key for key in resumen["por_subcarpeta"])
    assert any("auditoria_b" in key for key in resumen["por_subcarpeta"])


def test_auditoria_modelos_render_markdown() -> None:
    resumen = {
        "ruta_relativa": "Fuentes",
        "logs_revisados": 2,
        "subcarpetas_con_auditoria": 1,
        "total_eventos": 4,
        "total_swaps": 1,
        "por_rol": {
            "ocr-historico": {
                "eventos": {"fallo_registrado": 2, "swap_automatico": 1},
                "total_eventos": 3,
                "total_swaps": 1,
                "subcarpetas": ["Fuentes/demo"],
            }
        },
        "por_subcarpeta": {
            "Fuentes/demo": {
                "eventos": {"fallo_registrado": 2, "swap_automatico": 1},
                "total_eventos": 3,
                "total_swaps": 1,
                "roles": {"ocr-historico": {"eventos": {}, "total_eventos": 3, "total_swaps": 1}},
                "ultimo_evento": {"evento": "swap_automatico", "rol": "ocr-historico"},
            }
        },
    }

    markdown = am._render_markdown(resumen)

    assert "# Auditoría de Modelos" in markdown
    assert "## Por Rol" in markdown
    assert "### ocr-historico" in markdown
    assert "Swaps automáticos: 1" in markdown
    assert "### `Fuentes/demo`" in markdown
    assert '"swap_automatico": 1' in markdown


def test_auto_swap_no_cambia_si_ya_esta_en_respaldo() -> None:
    repo = _reset_repo("auto_swap_respaldado")
    ruta = _reset_fuentes_case(repo, "auto_swap_respaldado")
    (ruta / "checklist.json").write_text('{"imagenes": {}}\n', encoding="utf-8")
    _write_modelos(repo)
    _write_agent(repo, "ocr-historico", "proveedor/respaldo")
    original_common, original_swap = _patch_repo_root(repo)
    try:
        code = sm.main([
            "swap_modelo.py",
            "ocr-historico",
            "--auto",
            str(ruta),
            "falla tambien el respaldo",
        ])
        assert code == 0
        data = json.loads((ruta / "checklist.json").read_text(encoding="utf-8"))
        assert data["agentes"]["ocr-historico"]["fallos_modelo_consecutivos"] == 1
        agent_text = (repo / ".opencode" / "agents" / "ocr-historico.md").read_text(encoding="utf-8")
        assert "model: proveedor/respaldo" in agent_text
    finally:
        _restore_repo_root(original_common, original_swap)
        if ruta.exists():
            shutil.rmtree(ruta)


if __name__ == "__main__":
    try:
        test_presets_cargan_y_validan()
        test_aplicar_preset_escribe_modelos_y_sincroniza_agents()
        test_sincronizar_agents_tolera_modelo_ya_actualizado()
        test_validacion_falla_si_falta_un_rol()
        test_auto_swap_cambia_a_respaldo_en_tercer_fallo()
        test_auto_swap_cambia_a_respaldo_en_tercer_fallo_analista()
        test_auto_swap_cambia_a_respaldo_en_tercer_fallo_redactor()
        test_auto_swap_reinicia_contador_en_exito()
        test_auto_swap_escribe_auditoria_estructurada_en_log()
        test_auditoria_modelos_resume_por_subcarpeta_y_rol()
        test_auditoria_modelos_render_markdown()
        test_auto_swap_no_cambia_si_ya_esta_en_respaldo()
    finally:
        if TMP_ROOT.exists():
            shutil.rmtree(TMP_ROOT)
