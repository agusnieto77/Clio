"""
auditoria_modelos.py - Resume eventos AUDITORIA_MODELO desde log_clio.md.

Uso:
    python harness/tools/auditoria_modelos.py <ruta>
    python harness/tools/auditoria_modelos.py <ruta> --markdown

La ruta puede ser una subcarpeta dentro de Fuentes/ o la carpeta Fuentes/
completa. El script recorre recursivamente los `log_clio.md`, extrae las lineas
`AUDITORIA_MODELO <json>` y devuelve un resumen agregado por subcarpeta y por
rol.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from common import REPO_RAIZ, emitir_ok, resolver_ruta

PREFIJO_AUDITORIA = "AUDITORIA_MODELO "


def _validar_ruta_auditoria(ruta: Path) -> None:
    fuentes = REPO_RAIZ / "Fuentes"
    try:
        ruta.relative_to(fuentes)
        return
    except ValueError:
        pass
    if ruta != fuentes:
        raise SystemExit(
            f"ERROR: la ruta '{ruta}' debe ser `Fuentes/` o una carpeta dentro de Fuentes/."
        )


def _logs_objetivo(ruta: Path) -> list[Path]:
    if not ruta.is_dir():
        raise SystemExit(f"ERROR: la ruta '{ruta}' no es una carpeta existente.")
    return sorted(p for p in ruta.rglob("log_clio.md") if p.is_file())


def _leer_eventos(path: Path) -> list[dict]:
    eventos = []
    for linea in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if PREFIJO_AUDITORIA not in linea:
            continue
        payload = linea.split(PREFIJO_AUDITORIA, 1)[1].strip()
        try:
            eventos.append(json.loads(payload))
        except json.JSONDecodeError:
            eventos.append({
                "evento": "auditoria_invalida",
                "raw": payload,
            })
    return eventos


def _incrementar_conteos(destino: dict, evento: str) -> None:
    eventos = destino.setdefault("eventos", {})
    eventos[evento] = int(eventos.get(evento, 0)) + 1


def _resumir(ruta: Path) -> dict:
    logs = _logs_objetivo(ruta)
    por_subcarpeta: dict[str, dict] = {}
    por_rol: dict[str, dict] = {}
    total_eventos = 0
    total_swaps = 0

    for log in logs:
        subcarpeta = str(log.parent.relative_to(REPO_RAIZ)).replace("\\", "/")
        eventos = _leer_eventos(log)
        if not eventos:
            continue
        sub = por_subcarpeta.setdefault(
            subcarpeta,
            {
                "eventos": {},
                "total_eventos": 0,
                "total_swaps": 0,
                "roles": {},
                "ultimo_evento": None,
            },
        )
        for evento in eventos:
            nombre_evento = str(evento.get("evento", "desconocido"))
            rol = str(evento.get("rol", "(sin rol)"))
            total_eventos += 1
            sub["total_eventos"] += 1
            _incrementar_conteos(sub, nombre_evento)
            sub_roles = sub.setdefault("roles", {})
            _incrementar_conteos(
                sub_roles.setdefault(rol, {"eventos": {}, "total_eventos": 0, "total_swaps": 0}),
                nombre_evento,
            )
            sub_roles[rol]["total_eventos"] += 1

            rol_entry = por_rol.setdefault(
                rol,
                {"eventos": {}, "total_eventos": 0, "total_swaps": 0, "subcarpetas": set()},
            )
            _incrementar_conteos(rol_entry, nombre_evento)
            rol_entry["total_eventos"] += 1
            rol_entry["subcarpetas"].add(subcarpeta)

            if nombre_evento == "swap_automatico":
                total_swaps += 1
                sub["total_swaps"] += 1
                sub_roles[rol]["total_swaps"] += 1
                rol_entry["total_swaps"] += 1

            sub["ultimo_evento"] = evento

    for rol, entry in por_rol.items():
        entry["subcarpetas"] = sorted(entry["subcarpetas"])

    return {
        "ruta_consultada": str(ruta),
        "ruta_relativa": str(ruta.relative_to(REPO_RAIZ)).replace("\\", "/") if ruta != REPO_RAIZ else ".",
        "logs_revisados": len(logs),
        "subcarpetas_con_auditoria": len(por_subcarpeta),
        "total_eventos": total_eventos,
        "total_swaps": total_swaps,
        "por_subcarpeta": por_subcarpeta,
        "por_rol": por_rol,
    }


def _render_markdown(resumen: dict) -> str:
    lineas = [
        "# Auditoría de Modelos",
        "",
        f"- Ruta: `{resumen['ruta_relativa']}`",
        f"- Logs revisados: {resumen['logs_revisados']}",
        f"- Subcarpetas con auditoría: {resumen['subcarpetas_con_auditoria']}",
        f"- Eventos totales: {resumen['total_eventos']}",
        f"- Swaps automáticos: {resumen['total_swaps']}",
        "",
        "## Por Rol",
        "",
    ]

    if resumen["por_rol"]:
        for rol, datos in sorted(resumen["por_rol"].items()):
            subcarpetas = ", ".join(f"`{item}`" for item in datos["subcarpetas"])
            lineas.extend(
                [
                    f"### {rol}",
                    "",
                    f"- Eventos: {datos['total_eventos']}",
                    f"- Swaps: {datos['total_swaps']}",
                    f"- Subcarpetas: {subcarpetas or '(ninguna)' }",
                    f"- Detalle de eventos: {json.dumps(datos['eventos'], ensure_ascii=False, sort_keys=True)}",
                    "",
                ]
            )
    else:
        lineas.extend(["Sin eventos.", ""])

    lineas.append("## Por Subcarpeta")
    lineas.append("")
    if resumen["por_subcarpeta"]:
        for subcarpeta, datos in sorted(resumen["por_subcarpeta"].items()):
            ultimo = datos["ultimo_evento"]
            ultimo_desc = json.dumps(ultimo, ensure_ascii=False, sort_keys=True) if ultimo else "null"
            lineas.extend(
                [
                    f"### `{subcarpeta}`",
                    "",
                    f"- Eventos: {datos['total_eventos']}",
                    f"- Swaps: {datos['total_swaps']}",
                    f"- Roles: {', '.join(sorted(datos['roles'].keys()))}",
                    f"- Detalle de eventos: {json.dumps(datos['eventos'], ensure_ascii=False, sort_keys=True)}",
                    f"- Último evento: `{ultimo_desc}`",
                    "",
                ]
            )
    else:
        lineas.extend(["Sin eventos.", ""])

    return "\n".join(lineas).rstrip() + "\n"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Uso: python harness/tools/auditoria_modelos.py <ruta> [--markdown]", file=sys.stderr)
        return 2

    markdown = "--markdown" in argv[2:]
    ruta = resolver_ruta(argv[1])
    try:
        _validar_ruta_auditoria(ruta)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        resumen = _resumir(ruta)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if markdown:
        sys.stdout.write(_render_markdown(resumen))
        return 0

    emitir_ok("Resumen de auditoria de modelos", **resumen)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
