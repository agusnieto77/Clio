"""
configurar_modelos.py - Asistente guiado para configurar modelos de Clio.

Uso:
    python harness/tools/configurar_modelos.py
    python harness/tools/configurar_modelos.py --preset default
    python harness/tools/configurar_modelos.py --preset recommended
    python harness/tools/configurar_modelos.py --show-presets

El script escribe `harness/modelos.json` y sincroniza el campo `model:` de los
archivos `.opencode/agents/*.md` con el modelo principal de cada rol.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from common import REPO_RAIZ

ROLES = ("clio", "ocr-historico", "analista-cuantitativo", "redactor-informes")
PRESETS = ("default", "recommended")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class ModelosConfigError(Exception):
    """Error de configuración de modelos."""


def _preset_path(repo_root: Path, preset: str) -> Path:
    return repo_root / "harness" / f"modelos.{preset}.json"


def _modelos_path(repo_root: Path) -> Path:
    return repo_root / "harness" / "modelos.json"


def _agent_path(repo_root: Path, rol: str) -> Path:
    return repo_root / ".opencode" / "agents" / f"{rol}.md"


def _leer_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ModelosConfigError(f"{path} no contiene un objeto JSON válido.")
    return data


def _validar_modelos(config: dict) -> None:
    agentes = config.get("agentes")
    if not isinstance(agentes, dict):
        raise ModelosConfigError("Falta el bloque 'agentes' en la configuración.")

    for rol in ROLES:
        entrada = agentes.get(rol)
        if not isinstance(entrada, dict):
            raise ModelosConfigError(f"Falta la configuración del rol '{rol}'.")
        for clave in ("principal", "respaldo"):
            modelo = entrada.get(clave)
            if not isinstance(modelo, dict):
                raise ModelosConfigError(
                    f"El rol '{rol}' no tiene bloque '{clave}' válido."
                )
            identificador = modelo.get("id_opencode")
            if not isinstance(identificador, str) or "/" not in identificador:
                raise ModelosConfigError(
                    f"El rol '{rol}' tiene un id_opencode inválido en '{clave}'."
                )
        necesita_vision = entrada.get("necesita_vision")
        if necesita_vision is True:
            principal = entrada["principal"]["id_opencode"]
            respaldo = entrada["respaldo"]["id_opencode"]
            if not isinstance(principal, str) or not isinstance(respaldo, str):
                raise ModelosConfigError(
                    f"El rol '{rol}' necesita visión y sus modelos deben ser strings válidos."
                )

    parametros = config.get("parametros_analisis")
    if not isinstance(parametros, dict):
        raise ModelosConfigError("Falta el bloque 'parametros_analisis'.")
    requeridos = (
        "ventana_cocurrencia",
        "stopwords_idioma",
        "normalizacion_ortografica",
        "stopwords_fuente",
        "tfidf_norma",
        "tfidf_sublinear_tf",
        "min_longitud_token",
        "top_n_frecuencia",
    )
    faltantes = [clave for clave in requeridos if clave not in parametros]
    if faltantes:
        raise ModelosConfigError(
            f"Faltan parámetros de análisis: {', '.join(faltantes)}."
        )


def _cargar_preset(repo_root: Path, preset: str) -> dict:
    if preset not in PRESETS:
        raise ModelosConfigError(
            f"Preset inválido: {preset}. Elegí uno de: {', '.join(PRESETS)}."
        )
    path = _preset_path(repo_root, preset)
    if not path.is_file():
        raise ModelosConfigError(f"No existe el preset {path}.")
    config = _leer_json(path)
    _validar_modelos(config)
    return config


def _backup_si_existe(repo_root: Path) -> Path | None:
    modelos = _modelos_path(repo_root)
    if not modelos.is_file():
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = modelos.with_name(f"modelos.backup.{timestamp}.json")
    shutil.copy2(modelos, backup)
    return backup


def _escribir_modelos(repo_root: Path, config: dict) -> Path:
    path = _modelos_path(repo_root)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def _sincronizar_agents(repo_root: Path, config: dict) -> None:
    agentes = config["agentes"]
    for rol in ROLES:
        path = _agent_path(repo_root, rol)
        if not path.is_file():
            raise ModelosConfigError(f"No existe el archivo de agente {path}.")
        principal = agentes[rol]["principal"]["id_opencode"]
        text = path.read_text(encoding="utf-8")
        if not re.search(r"^model:\s*\S+\s*$", text, re.MULTILINE):
            raise ModelosConfigError(
                f"No encontré la línea 'model:' en {path.name}."
            )
        nuevo = re.sub(
            r"^(model:\s*)\S+(\s*)$",
            rf"\g<1>{principal}\g<2>",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        path.write_text(nuevo, encoding="utf-8")


def _mostrar_presets(repo_root: Path) -> None:
    print("Presets disponibles:\n")
    print("1. default     — starter, más liviano para roles de texto")
    print("2. recommended — configuración testeada de punta a punta en este repo")
    print("\nArchivos fuente:")
    for preset in PRESETS:
        print(f"- {preset}: {_preset_path(repo_root, preset)}")


def _preguntar(prompt: str, default: str | None = None) -> str:
    sufijo = ""
    if default:
        sufijo = f" [{default}]"
    valor = input(f"{prompt}{sufijo}: ").strip()
    if valor:
        return valor
    if default is not None:
        return default
    return ""


def _menu_inicial() -> str:
    print("\nConfiguración inicial de modelos de Clio\n")
    print("1) Usar la configuración por defecto")
    print("2) Usar la configuración recomendada")
    print("3) Configurar manualmente paso a paso")
    print("4) Ver explicación corta de los presets")
    while True:
        opcion = _preguntar("Elegí una opción", "2")
        match opcion:
            case "1":
                return "default"
            case "2":
                return "recommended"
            case "3":
                return "manual"
            case "4":
                print(
                    "\n- Por defecto: punto de partida simple, más liviano en roles de texto.\n"
                    "- Recomendada: configuración testeada de punta a punta en este repo.\n"
                )
            case _:
                print("Opción inválida. Elegí 1, 2, 3 o 4.")


def _config_manual(repo_root: Path) -> dict:
    base = _cargar_preset(repo_root, "recommended")
    print(
        "\nConfiguración guiada. Si no sabés qué poner, presioná Enter y se usa el valor sugerido.\n"
    )
    agentes = base["agentes"]
    for rol in ROLES:
        print(f"\nRol: {rol}")
        print(f"Descripción: {agentes[rol]['rol']}")
        principal_actual = agentes[rol]["principal"]["id_opencode"]
        respaldo_actual = agentes[rol]["respaldo"]["id_opencode"]
        agentes[rol]["principal"]["id_opencode"] = _preguntar(
            "Modelo principal", principal_actual
        )
        agentes[rol]["respaldo"]["id_opencode"] = _preguntar(
            "Modelo de respaldo", respaldo_actual
        )
    base["preset"] = "manual"
    _validar_modelos(base)
    return base


def _aplicar_config(repo_root: Path, config: dict) -> tuple[Path | None, Path]:
    backup = _backup_si_existe(repo_root)
    modelos = _escribir_modelos(repo_root, config)
    _sincronizar_agents(repo_root, config)
    return backup, modelos


def _resumen(config: dict, backup: Path | None, modelos: Path) -> None:
    print("\nConfiguración guardada correctamente.\n")
    print(f"Archivo principal: {modelos}")
    if backup is not None:
        print(f"Backup anterior:   {backup}")
    print("\nModelos principales activos:")
    for rol in ROLES:
        principal = config["agentes"][rol]["principal"]["id_opencode"]
        print(f"- {rol}: {principal}")
    print("\nIMPORTANTE: reiniciá OpenCode para que los agentes recarguen el cambio.")


def main(argv: list[str]) -> int:
    repo_root = REPO_RAIZ
    try:
        if "--show-presets" in argv[1:]:
            _mostrar_presets(repo_root)
            return 0

        if len(argv) == 3 and argv[1] == "--preset":
            config = _cargar_preset(repo_root, argv[2])
            backup, modelos = _aplicar_config(repo_root, config)
            _resumen(config, backup, modelos)
            return 0

        if len(argv) > 1:
            print(
                "Uso: python harness/tools/configurar_modelos.py [--preset default|recommended|--show-presets]",
                file=sys.stderr,
            )
            return 2

        opcion = _menu_inicial()
        match opcion:
            case "default" | "recommended":
                config = _cargar_preset(repo_root, opcion)
            case "manual":
                config = _config_manual(repo_root)
            case _:
                raise ModelosConfigError("Opción de configuración no reconocida.")

        backup, modelos = _aplicar_config(repo_root, config)
        _resumen(config, backup, modelos)
        return 0
    except ModelosConfigError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 1
    except EOFError:
        print("Configuración cancelada por fin de entrada.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nConfiguración cancelada por el usuario.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
