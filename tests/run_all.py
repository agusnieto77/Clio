from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str) -> None:
    result = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detalle = result.stdout or result.stderr
        raise SystemExit(f"Falló {script}:\n{detalle}")


def main() -> int:
    _run("tests/clio_validation_regression.py")
    _run("tests/clio_model_setup_regression.py")
    print("OK: todas las suites de regresión pasaron.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
