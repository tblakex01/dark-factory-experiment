#!/usr/bin/env python3
"""Start the backend for a validation run, or fail with a diagnosable reason.

    python harness/serve.py --port 8123

**This exists because of 3fc03a0 (2026-04-18).** The backend hard-requires DATABASE_URL
and friends at import time. The validate-pr workflow's start-app node once launched
uvicorn without loading any of them, so the process crashed at import with
`RuntimeError: DATABASE_URL is not set`, the health poll failed, and the synthesizer
scored that as `e2e_status: "not_e2e_testable"`. PR #80 auto-merged having never been
driven through a browser.

So this refuses to start rather than starting into a crash, and it says which variable
is missing. **A step that cannot run must be loud, not absent** - the whole argument of
this harness, applied to the thing that starts the software.

The env file lives OUTSIDE the repo because it holds secrets. Path is overridable with
DARK_FACTORY_VALIDATION_ENV; on the VPS it is /opt/dark-factory/validation.env. Point it
at a DEDICATED validation database - an E2E against production data is a data-loss
incident waiting for a slow afternoon.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "app" / "backend"

REQUIRED = ["DATABASE_URL", "OPENROUTER_API_KEY", "JWT_SECRET",
            "SUPADATA_API_KEY", "YOUTUBE_CHANNEL_ID"]


def load_env_file(path: Path) -> int:
    """Minimal KEY=VALUE loader. Deliberately not python-dotenv: this runs before the
    backend's dependencies are guaranteed importable, and a harness that needs the app's
    venv to tell you the app cannot start is not much of a harness."""
    loaded = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
        loaded += 1
    return loaded


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    args = ap.parse_args()

    env_path = Path(os.environ.get("DARK_FACTORY_VALIDATION_ENV",
                                   "/opt/dark-factory/validation.env"))
    if env_path.is_file():
        print(f"loaded {load_env_file(env_path)} vars from {env_path}", flush=True)
    else:
        print(f"WARN: no validation env at {env_path}", file=sys.stderr, flush=True)

    missing = [v for v in REQUIRED if not os.environ.get(v)]
    if missing:
        # NON-ZERO, and named. appproc's health poll would otherwise report a generic
        # boot timeout, which sends you to look at the app instead of at the env file.
        print(f"APP_START_REFUSED missing={','.join(missing)}", file=sys.stderr, flush=True)
        print(f"Populate {env_path} (outside the repo) or set "
              f"DARK_FACTORY_VALIDATION_ENV. Use a DEDICATED validation database.",
              file=sys.stderr, flush=True)
        return 1

    return subprocess.call(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
         "--port", str(args.port)],
        cwd=BACKEND,
    )


if __name__ == "__main__":
    sys.exit(main())
