"""
swap_modelo.py - Intercambia modelo principal <-> modelo de respaldo de un agente.

Uso:
    python harness/tools/swap_modelo.py <rol>
    python harness/tools/swap_modelo.py <rol> --restaurar

Roles validos: clio, ocr-historico, analista-cuantitativo, redactor-informes.

Lee harness/modelos.json, identifica el model: del .opencode/agents/<rol>.md y
lo reescribe con el otro modelo (principal <-> respaldo). El cambio exige
reiniciar OpenCode para que el runtime recargue la configuracion.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from common import REPO_RAIZ, emitir_error, emitir_ok

ROLES_VALIDOS = {
    "clio",
    "ocr-historico",
    "analista-cuantitativo",
    "redactor-informes",
}


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


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Uso: python harness/tools/swap_modelo.py <rol> [--restaurar]",
            file=sys.stderr,
        )
        return 2

    rol = argv[1].lower()
    restaurar = "--restaurar" in argv[2:]

    if rol not in ROLES_VALIDOS:
        emitir_error(
            f"Rol invalido: {rol}. Roles validos: {sorted(ROLES_VALIDOS)}"
        )
        return 2

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
        emitir_error(
            f"No se encontro la linea 'model:' en {agent_file}."
        )
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


if __name__ == "__main__":
    sys.exit(main(sys.argv))
