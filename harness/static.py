#!/usr/bin/env python3
"""The static rung, across BOTH halves of DynaChat.

`ci.py` runs one command per rung, and this repo has two stacks. Rather than teach the
ladder about that - the ladder is the same in every factory and should stay that way -
the split lives here, behind one command that `harness.config.json` can name.

The commands are lifted verbatim from `.archon/workflows/dark-factory-validate-pr.yaml`
(`static-checks-backend-p1` / `static-checks-frontend-p1`) so there is ONE definition of
what "static passes" means for this repo. If you change one, change the other, or the
gate and the workflow start disagreeing about a green build.

    python harness/static.py

Exits non-zero if any check fails. Prints which one, because "static failed" across two
languages and five tools is not a diagnosis.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "app" / "backend"
FRONTEND = ROOT / "app" / "frontend"

# (label, cwd, argv). Kept as argv rather than shell strings: `ci.py` resolves argv[0]
# through shutil.which for the Windows .cmd-shim problem, and a shell string would
# reintroduce the quoting bugs that ate 2026-04-14.
CHECKS = [
    ("ruff-lint",   BACKEND,  ["uv", "run", "ruff", "check", "."]),
    ("ruff-format", BACKEND,  ["uv", "run", "ruff", "format", "--check", "."]),
    ("mypy",        BACKEND,  ["uv", "run", "mypy", "."]),
    ("tsc",         FRONTEND, ["bun", "run", "tsc", "--noEmit"]),
    ("biome",       FRONTEND, ["bun", "x", "biome", "check", "src"]),
]


def main() -> int:
    failed: list[str] = []
    ran = 0

    for label, cwd, argv in CHECKS:
        if not cwd.exists():
            # LOUD. A missing half is not a passing half - that is the whole argument of
            # this harness, applied to itself.
            print(f"STATIC_MISSING {label}: {cwd} does not exist", flush=True)
            failed.append(label)
            continue
        try:
            p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600)
        except FileNotFoundError:
            print(f"STATIC_MISSING {label}: {argv[0]} is not on PATH", flush=True)
            failed.append(label)
            continue
        except subprocess.TimeoutExpired:
            print(f"STATIC_TIMEOUT {label} after 600s", flush=True)
            failed.append(label)
            continue

        ran += 1
        if p.returncode != 0:
            print(f"--- {label} ---", flush=True)
            print(((p.stdout or "") + (p.stderr or "")).strip()[-2000:], flush=True)
            failed.append(label)
        else:
            print(f"  ok  {label}", flush=True)

    if failed:
        print(f"STATIC_FAILED checks={','.join(failed)}", flush=True)
        return 1

    # A COUNT, not just a name. Five tools silently becoming three is the shape of every
    # bug this repo has filed against its own gate.
    print(f"STATIC_OK checks={ran}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
