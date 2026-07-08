from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "harness" / "tools"
TMP_ROOT = ROOT / "tests" / "_tmp_model_setup"

sys.path.insert(0, str(TOOLS))

import configurar_modelos as cm  # noqa: E402


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


if __name__ == "__main__":
    try:
        test_presets_cargan_y_validan()
        test_aplicar_preset_escribe_modelos_y_sincroniza_agents()
        test_sincronizar_agents_tolera_modelo_ya_actualizado()
        test_validacion_falla_si_falta_un_rol()
    finally:
        if TMP_ROOT.exists():
            shutil.rmtree(TMP_ROOT)
