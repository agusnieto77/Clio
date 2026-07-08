"""
swap_modelo.py - Intercambia modelo principal <-> modelo de respaldo de un agente.

Uso:
    python harness/tools/swap_modelo.py <rol>
    python harness/tools/swap_modelo.py <rol> --restaurar
    python harness/tools/swap_modelo.py <rol> --auto <ruta-subcarpeta> [detalle]
    python harness/tools/swap_modelo.py <rol> --exito <ruta-subcarpeta>

Roles validos: clio, ocr-historico, analista-cuantitativo, redactor-informes.

Lee harness/modelos.json, identifica el model: del .opencode/agents/<rol>.md y
lo reescribe con el otro modelo (principal <-> respaldo). El cambio exige
reiniciar OpenCode para que el runtime recargue la configuracion.

En modo --auto registra fallos consecutivos del modelo vigente en el
checklist.json de la subcarpeta. Al tercer fallo consecutivo del principal,
hace el swap al respaldo y deja asentado que se requiere reinicio antes de
reanudar el flujo.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from common import (
    REPO_RAIZ,
    emitir_error,
    emitir_ok,
    escribir_checklist,
    escribir_log,
    leer_checklist,
    resolver_ruta,
    validar_subcarpeta,
)

ROLES_VALIDOS = {
    "clio",
    "ocr-historico",
    "analista-cuantitativo",
    "redactor-informes",
}

UMBRAL_FALLOS_CONSECUTIVOS = 3


def _leer_modelos() -> dict:
    path = REPO_RAIZ / "harness" / "modelos.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _agent_path(rol: str) -> Path:
    return REPO_RAIZ / ".opencode" / "agents" / f"{rol}.md"


def _modelo_actual(path: Path) -> str | None:
    """Lee el frontmatter del .md y extrae el valor de model:."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^model:\s*(\S+)\s*$", text, re.MULTILINE)
    return m.group(1) if m else None


def _swap_modelo_en_file(path: Path, nuevo_modelo: str) -> None:
    text = path.read_text(encoding="utf-8")
    nuevo = re.sub(
        r"^(model:\s*)\S+(\s*)$",
        rf"\g<1>{nuevo_modelo}\g<2>",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(nuevo, encoding="utf-8")


def _escribir_auditoria_log(ruta: Path, evento: str, payload: dict) -> None:
    auditoria = {"evento": evento, **payload}
    escribir_log(
        ruta,
        f"AUDITORIA_MODELO {json.dumps(auditoria, ensure_ascii=False, sort_keys=True)}",
    )


def _agentes_state(data: dict) -> dict:
    agentes = data.setdefault("agentes", {})
    if not isinstance(agentes, dict):
        agentes = {}
        data["agentes"] = agentes
    return agentes


def _estado_agente(data: dict, rol: str) -> dict:
    estado = _agentes_state(data).setdefault(rol, {})
    if not isinstance(estado, dict):
        estado = {}
        _agentes_state(data)[rol] = estado
    estado.setdefault("fallos_modelo_consecutivos", 0)
    estado.setdefault("ultimo_error_modelo", None)
    estado.setdefault("ultimo_modelo_registrado", None)
    estado.setdefault("ultima_actualizacion_modelo", None)
    estado.setdefault("ultimo_swap_modelo", None)
    return estado


def _registrar_exito_en_checklist(ruta: Path, rol: str, actual: str) -> dict:
    data = leer_checklist(ruta)
    estado = _estado_agente(data, rol)
    ahora = datetime.now().isoformat(timespec="seconds")
    estado["fallos_modelo_consecutivos"] = 0
    estado["ultimo_error_modelo"] = None
    estado["ultimo_modelo_registrado"] = actual
    estado["ultima_actualizacion_modelo"] = ahora
    data["actualizado"] = ahora
    escribir_checklist(ruta, data)
    return estado


def _registrar_fallo_en_checklist(
    ruta: Path,
    rol: str,
    actual: str,
    detalle: str | None,
) -> tuple[dict, dict]:
    data = leer_checklist(ruta)
    estado = _estado_agente(data, rol)
    ahora = datetime.now().isoformat(timespec="seconds")
    mismo_modelo = estado.get("ultimo_modelo_registrado") == actual
    previos = int(estado.get("fallos_modelo_consecutivos", 0))
    estado["fallos_modelo_consecutivos"] = previos + 1 if mismo_modelo else 1
    estado["ultimo_error_modelo"] = detalle or "(sin detalle)"
    estado["ultimo_modelo_registrado"] = actual
    estado["ultima_actualizacion_modelo"] = ahora
    data["actualizado"] = ahora
    escribir_checklist(ruta, data)
    return data, estado


def _cmd_swap_manual(rol: str, restaurar: bool) -> int:
    modelos = _leer_modelos()
    cfg = modelos.get("agentes", {}).get(rol)
    if not cfg:
        emitir_error(f"No hay configuracion para el rol '{rol}' en modelos.json")
        return 1

    principal = cfg["principal"]["id_opencode"]
    respaldo = cfg["respaldo"]["id_opencode"]
    agent_file = _agent_path(rol)
    if not agent_file.is_file():
        emitir_error(f"No existe {agent_file}")
        return 1

    actual = _modelo_actual(agent_file)
    if actual is None:
        emitir_error(f"No se encontro la linea 'model:' en {agent_file}.")
        return 1

    if restaurar:
        objetivo = principal
        razon = "restauracion al modelo principal"
    elif actual == principal:
        objetivo = respaldo
        razon = "paso a modelo de respaldo"
    elif actual == respaldo:
        objetivo = principal
        razon = "vuelta al modelo principal"
    else:
        objetivo = respaldo
        razon = (
            f"el modelo actual '{actual}' no coincide con principal ni respaldo; "
            "se pasa al respaldo declarado"
        )

    _swap_modelo_en_file(agent_file, objetivo)
    emitir_ok(
        f"Modelo del agente '{rol}' cambiado: '{actual}' -> '{objetivo}'. "
        f"Motivo: {razon}. REINICIAR OpenCode para que el cambio tenga efecto.",
        rol=rol,
        modelo_anterior=actual,
        modelo_nuevo=objetivo,
        razon=razon,
        requiere_reinicio=True,
    )
    return 0


def _cmd_auto(rol: str, ruta_arg: str, detalle: str | None) -> int:
    ruta = resolver_ruta(ruta_arg)
    validar_subcarpeta(ruta)

    modelos = _leer_modelos()
    cfg = modelos.get("agentes", {}).get(rol)
    if not cfg:
        emitir_error(f"No hay configuracion para el rol '{rol}' en modelos.json")
        return 1

    principal = cfg["principal"]["id_opencode"]
    respaldo = cfg["respaldo"]["id_opencode"]
    agent_file = _agent_path(rol)
    if not agent_file.is_file():
        emitir_error(f"No existe {agent_file}")
        return 1

    actual = _modelo_actual(agent_file)
    if actual is None:
        emitir_error(f"No se encontro la linea 'model:' en {agent_file}.")
        return 1

    data, estado = _registrar_fallo_en_checklist(ruta, rol, actual, detalle)
    fallos = int(estado["fallos_modelo_consecutivos"])

    if actual == respaldo:
        escribir_log(
            ruta,
            f"MODELO DE RESPALDO FALLA - agente={rol} - modelo={actual} - "
            f"fallos_consecutivos={fallos} - requiere_intervencion=si",
        )
        _escribir_auditoria_log(
            ruta,
            "fallo_respaldo",
            {
                "rol": rol,
                "ruta": str(ruta),
                "modelo_vigente": actual,
                "fallos_consecutivos": fallos,
                "swap_ejecutado": False,
                "requiere_intervencion": True,
                "requiere_reinicio": False,
                "detalle": detalle or "(sin detalle)",
            },
        )
        emitir_ok(
            f"Fallo registrado para '{rol}' usando el respaldo '{actual}'. "
            "No hay otro modelo declarado para swap automatico.",
            rol=rol,
            ruta=str(ruta),
            modelo_vigente=actual,
            fallos_consecutivos=fallos,
            swap_ejecutado=False,
            requiere_intervencion=True,
            requiere_reinicio=False,
        )
        return 0

    if fallos < UMBRAL_FALLOS_CONSECUTIVOS:
        escribir_log(
            ruta,
            f"FALLO DE MODELO REGISTRADO - agente={rol} - modelo={actual} - "
            f"fallos_consecutivos={fallos}/{UMBRAL_FALLOS_CONSECUTIVOS}",
        )
        _escribir_auditoria_log(
            ruta,
            "fallo_registrado",
            {
                "rol": rol,
                "ruta": str(ruta),
                "modelo_vigente": actual,
                "fallos_consecutivos": fallos,
                "umbral_swap": UMBRAL_FALLOS_CONSECUTIVOS,
                "swap_ejecutado": False,
                "requiere_intervencion": False,
                "requiere_reinicio": False,
                "detalle": detalle or "(sin detalle)",
            },
        )
        emitir_ok(
            f"Fallo registrado para '{rol}'. Todavia no se alcanza el umbral de swap.",
            rol=rol,
            ruta=str(ruta),
            modelo_vigente=actual,
            fallos_consecutivos=fallos,
            swap_ejecutado=False,
            requiere_intervencion=False,
            requiere_reinicio=False,
        )
        return 0

    _swap_modelo_en_file(agent_file, respaldo)
    ahora = datetime.now().isoformat(timespec="seconds")
    estado["fallos_modelo_consecutivos"] = 0
    estado["ultimo_modelo_registrado"] = respaldo
    estado["ultima_actualizacion_modelo"] = ahora
    estado["ultimo_swap_modelo"] = {
        "de": actual,
        "a": respaldo,
        "motivo": f"{UMBRAL_FALLOS_CONSECUTIVOS} fallos consecutivos del modelo principal",
        "timestamp": ahora,
    }
    data["agentes"][rol] = estado
    data["actualizado"] = ahora
    escribir_checklist(ruta, data)
    escribir_log(
        ruta,
        f"SWAP AUTOMATICO DE MODELO - agente={rol} - modelo_anterior={actual} - "
        f"modelo_nuevo={respaldo} - motivo={UMBRAL_FALLOS_CONSECUTIVOS} fallos consecutivos - requiere_reinicio=si",
    )
    _escribir_auditoria_log(
        ruta,
        "swap_automatico",
        {
            "rol": rol,
            "ruta": str(ruta),
            "modelo_anterior": actual,
            "modelo_nuevo": respaldo,
            "fallos_consecutivos": UMBRAL_FALLOS_CONSECUTIVOS,
            "umbral_swap": UMBRAL_FALLOS_CONSECUTIVOS,
            "swap_ejecutado": True,
            "requiere_intervencion": True,
            "requiere_reinicio": True,
            "detalle": detalle or "(sin detalle)",
        },
    )
    emitir_ok(
        f"Swap automatico ejecutado para '{rol}': '{actual}' -> '{respaldo}'. "
        "REINICIAR OpenCode antes de reanudar la subcarpeta.",
        rol=rol,
        ruta=str(ruta),
        modelo_anterior=actual,
        modelo_nuevo=respaldo,
        fallos_consecutivos=UMBRAL_FALLOS_CONSECUTIVOS,
        swap_ejecutado=True,
        requiere_intervencion=True,
        requiere_reinicio=True,
    )
    return 0


def _cmd_exito(rol: str, ruta_arg: str) -> int:
    ruta = resolver_ruta(ruta_arg)
    validar_subcarpeta(ruta)
    agent_file = _agent_path(rol)
    if not agent_file.is_file():
        emitir_error(f"No existe {agent_file}")
        return 1
    actual = _modelo_actual(agent_file)
    if actual is None:
        emitir_error(f"No se encontro la linea 'model:' en {agent_file}.")
        return 1

    estado = _registrar_exito_en_checklist(ruta, rol, actual)
    escribir_log(
        ruta,
        f"EXITO DE MODELO REGISTRADO - agente={rol} - modelo={actual} - contador_reiniciado=si",
    )
    _escribir_auditoria_log(
        ruta,
        "exito_modelo",
        {
            "rol": rol,
            "ruta": str(ruta),
            "modelo_vigente": actual,
            "fallos_consecutivos": int(estado["fallos_modelo_consecutivos"]),
            "swap_ejecutado": False,
            "requiere_reinicio": False,
        },
    )
    emitir_ok(
        f"Contador de fallos consecutivos reiniciado para '{rol}'.",
        rol=rol,
        ruta=str(ruta),
        modelo_vigente=actual,
        fallos_consecutivos=int(estado["fallos_modelo_consecutivos"]),
        swap_ejecutado=False,
        requiere_reinicio=False,
    )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Uso: python harness/tools/swap_modelo.py <rol> [--restaurar|--auto <ruta> [detalle]|--exito <ruta>]",
            file=sys.stderr,
        )
        return 2

    rol = argv[1].lower()

    if rol not in ROLES_VALIDOS:
        emitir_error(
            f"Rol invalido: {rol}. Roles validos: {sorted(ROLES_VALIDOS)}"
        )
        return 2

    if "--auto" in argv[2:]:
        idx = argv.index("--auto")
        if len(argv) <= idx + 1:
            print(
                "Uso: python harness/tools/swap_modelo.py <rol> --auto <ruta-subcarpeta> [detalle]",
                file=sys.stderr,
            )
            return 2
        ruta_arg = argv[idx + 1]
        detalle = " ".join(argv[idx + 2 :]) or None
        return _cmd_auto(rol, ruta_arg, detalle)

    if "--exito" in argv[2:]:
        idx = argv.index("--exito")
        if len(argv) <= idx + 1:
            print(
                "Uso: python harness/tools/swap_modelo.py <rol> --exito <ruta-subcarpeta>",
                file=sys.stderr,
            )
            return 2
        return _cmd_exito(rol, argv[idx + 1])

    restaurar = "--restaurar" in argv[2:]
    return _cmd_swap_manual(rol, restaurar)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
