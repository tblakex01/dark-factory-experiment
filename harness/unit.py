#!/usr/bin/env python3
"""The unit rung, across BOTH halves of DynaChat, with a real count.

Same reason as `static.py`: two stacks, one rung. Commands lifted from
`run-tests-backend-p1` / `run-tests-frontend-p1` in the validate-pr workflow.

    python harness/unit.py

**The count is the point.** `ci.py` refuses a run that reports zero tests, because a
suite that discovered nothing exits 0 and looks perfect. That guard only works if the
number reaching it is real, so this parses BOTH runners and sums them - and it fails if
either half reports nothing, rather than quietly passing on the other half's total.

Measured 2026-08-13: backend 390 passed / 67 skipped, frontend 159 passed.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "app" / "backend"
FRONTEND = ROOT / "app" / "frontend"

# pytest -q tail:      "390 passed, 67 skipped in 85.07s"
# vitest run tail:     "Tests  159 passed (159)"   (ANSI codes stripped first)
BACKEND_PATTERN = re.compile(r"(\d+) passed")
FRONTEND_PATTERN = re.compile(r"Tests\s+(\d+) passed")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def run(label: str, cwd: Path, argv: list[str], pattern: re.Pattern[str]) -> int | None:
    """Returns the test count, or None if the half failed or reported nothing."""
    if not cwd.exists():
        print(f"UNIT_MISSING {label}: {cwd} does not exist", flush=True)
        return None
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900)
    except FileNotFoundError:
        print(f"UNIT_MISSING {label}: {argv[0]} is not on PATH", flush=True)
        return None
    except subprocess.TimeoutExpired:
        print(f"UNIT_TIMEOUT {label} after 900s", flush=True)
        return None

    out = ANSI.sub("", (p.stdout or "") + (p.stderr or ""))
    if p.returncode != 0:
        print(f"--- {label} ---", flush=True)
        print(out.strip()[-3000:], flush=True)
        print(f"UNIT_FAILED half={label}", flush=True)
        return None

    m = pattern.search(out)
    count = int(m.group(1)) if m else 0
    if count == 0:
        # EMPTY IS NOT PASS, applied to the counter itself. A runner whose output format
        # changed reports zero, and zero read as success is how a green gate stops
        # meaning anything.
        print(f"UNIT_ERROR {label}: exited 0 but reported 0 tests. Either the suite ran "
              f"nothing, or the pattern no longer matches this runner's output.",
              flush=True)
        return None

    print(f"  ok  {label} tests={count}", flush=True)
    return count


def main() -> int:
    backend = run("backend", BACKEND,
                  ["uv", "run", "pytest", "tests", "-q"], BACKEND_PATTERN)
    frontend = run("frontend", FRONTEND,
                   ["bun", "run", "test"], FRONTEND_PATTERN)

    # BOTH halves, deliberately. Returning the backend total when the frontend half died
    # would report a healthy-looking number for a run that checked half the product.
    if backend is None or frontend is None:
        return 1

    print(f"UNIT_PASSED tests={backend + frontend} backend={backend} frontend={frontend}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
