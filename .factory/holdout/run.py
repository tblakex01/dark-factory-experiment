#!/usr/bin/env python3
"""HOLDOUT SCENARIOS for DynaChat. The builder is blocked from reading this directory.

    .factory/holdout/run.py      <- here. Deny-listed per node, protected by the guard
    harness/                     <- NOT here. The builder reads everything in harness/

Everything under `harness/` sits inside the agent's optimisation loop: it can read those
checks, run them, and iterate until they are green. These assertions differ only in that
the builder never sees them, and that is the only honest reason to merge code nobody read.

═══════════════════════════════════════════════════════════════════════════════════════
WRITTEN 2026-08-13, AND THE DATE MATTERS. READ THIS BEFORE CITING A GREEN RESULT.
═══════════════════════════════════════════════════════════════════════════════════════

Rule 1 of a holdout is that it is written BEFORE the work, because a scenario written
after seeing the implementation is a description of the implementation. **These were
written after.** Every line of DynaChat below them was merged months earlier.

So what these are is a **floor from today forward**, not a retrospective audit of the
390 PRs already in `main`. They cannot tell you the existing code is correct - they were
written by reading it. They can tell you the invariants below stop holding, which is the
job from the next issue onward.

The clean way to read that: these assertions have authority over FUTURE diffs and none
over past ones. Anything written from here on inherits the property properly, because
the code it judges will not exist yet.

THE RULES THIS FILE STILL FOLLOWS:

  1. COMPOSE. The dominant real failure is not cheating, it is feature isolation:
     components individually correct that never work together. Every scenario below
     asserts something no single unit test is positioned to see.
  2. Duplicate, do not import. Nothing here comes from `harness/` or from
     `app/backend/tests/`. The env setup below is a deliberate copy of conftest's, not
     an import of it - importing the suite's fixtures would put this inside the same
     optimisation loop it exists to sit outside of.
  3. Assert the PROPERTY, not one algebraic consequence of it. A derived constant in a
     holdout is a second silent copy of a decision and it goes stale without anyone
     editing it.

Emits `HOLDOUT_PASSED scenarios=N assertions=M`.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = ROOT / "app" / "backend"

# --- run under the backend's interpreter, not the harness's -------------------------
# `ci.py` invokes this with sys.executable, which is the top-level python. DynaChat's
# dependencies live in app/backend/.venv. Rather than make ci.py know that (it is the
# same ladder in every factory and should stay that way), re-exec once, here.
#
# Unconditional rather than conditional-on-ImportError: a top-level environment that
# happens to have fastapi installed would otherwise run these scenarios against a
# DIFFERENT dependency set than the app uses, and pass or fail for reasons that have
# nothing to do with DynaChat.
if os.environ.get("_HOLDOUT_REEXEC") != "1":
    _env = dict(os.environ, _HOLDOUT_REEXEC="1")
    sys.exit(subprocess.call(
        ["uv", "run", "python", str(Path(__file__).resolve())], cwd=BACKEND, env=_env))

# Duplicated from conftest deliberately - see rule 2. Values are placeholders; nothing
# below touches a network or a database.
for _k, _v in {
    "JWT_SECRET": "holdout-not-a-real-secret",
    "DATABASE_URL": "postgresql://holdout:holdout@localhost:5432/holdout",
    "SUPADATA_API_KEY": "holdout-placeholder",
    "YOUTUBE_CHANNEL_ID": "UC_holdout",
    "OPENROUTER_API_KEY": "holdout-placeholder",
}.items():
    os.environ.setdefault(_k, _v)

# `backend` is a package under app/, so app/ is the import root - not app/backend/.
sys.path.insert(0, str(ROOT / "app"))

ASSERTIONS = 0
FAILURES: list[str] = []


def expect(name: str, ok: bool, detail: str = "") -> None:
    global ASSERTIONS
    ASSERTIONS += 1
    if not ok:
        FAILURES.append(f"{name}: {detail}")


def _api_routes():
    """Every /api route on the ASSEMBLED app, with its dependency count.

    The assembled app is the point. A decorator is present in a source file; whether it
    is REACHED depends on router ordering, prefix nesting and include_router calls, and
    that only exists once everything is wired together.
    """
    from backend.main import app

    out = []
    for r in app.routes:
        path = getattr(r, "path", "") or ""
        if not path.startswith("/api"):
            continue
        dep = getattr(r, "dependant", None)
        out.append((path, frozenset(getattr(r, "methods", None) or []),
                    len(dep.dependencies) if dep is not None else -1))
    return out


# ---------------------------------------------------------------------------
def scenario_no_unauthenticated_path_reaches_a_conversation() -> None:
    """MISSION hard invariant 2, asserted against the wired app rather than a decorator.

    Composes routing, router inclusion and the auth dependency. Every unit test in the
    suite that covers auth does so by calling a route it already knows about; none of
    them can notice a NEW route added without the dependency, or an existing one whose
    guard stopped being reached after a router was re-nested. That is precisely the
    failure this invariant would die of, and it is invisible below the line.
    """
    routes = _api_routes()

    expect("the app actually assembled some API routes",
           len(routes) >= 20, f"found {len(routes)}")

    # The public surface is a WHITELIST, deliberately. Asserting "conversations are
    # guarded" would pass while a brand-new unguarded /api/messages route existed.
    public_allowed = {"/api/auth/signup", "/api/auth/login", "/api/auth/logout",
                      "/api/health", "/api/version"}
    unguarded = sorted({p for p, _m, n in routes if n == 0} - public_allowed)
    expect("no API route outside the known-public set is dependency-free",
           not unguarded,
           f"unguarded={unguarded} - a route with no dependency is reachable "
           f"anonymously, which is MISSION invariant 2")

    # ...and the private surface specifically.
    private = [(p, n) for p, _m, n in routes
               if p.startswith(("/api/conversations", "/api/admin"))]
    expect("every conversation and admin route carries at least one dependency",
           private and all(n >= 1 for _p, n in private),
           f"routes={private}")


# ---------------------------------------------------------------------------
def scenario_the_cap_is_one_number_and_only_one() -> None:
    """MISSION hard invariant 1, and the composed half nobody tests: SINGLE DEFINITION.

    A unit test asserting `DAILY_MESSAGE_CAP == 25` passes happily while a second copy
    of the number lives in a route module and is the one actually enforced. The invariant
    is not "the constant equals 25" - it is "there is one cap and it is 25". Issue #361
    was exactly this shape: the enforcement state was partitioned across four uvicorn
    workers, so the constant was right and the limit was not.
    """
    from backend import rate_limit

    expect("the daily cap is 25", rate_limit.DAILY_MESSAGE_CAP == 25,
           f"cap={rate_limit.DAILY_MESSAGE_CAP}")
    expect("the window is 24 hours", rate_limit.WINDOW_HOURS == 24,
           f"window={rate_limit.WINDOW_HOURS}")

    # A SECOND definition anywhere in backend source is the failure. Matches an
    # assignment of a cap-shaped name, not the bare number 25, so ordinary arithmetic
    # and unrelated constants do not trip it.
    pattern = re.compile(r"^\s*(?!#)\w*(?:DAILY_MESSAGE_CAP|MESSAGE_CAP|DAILY_CAP)\s*[:=]",
                         re.MULTILINE)
    definitions = []
    for py in BACKEND.rglob("*.py"):
        parts = set(py.parts)
        if {".venv", "tests", "__pycache__", "alembic"} & parts:
            continue
        if pattern.search(py.read_text(encoding="utf-8", errors="replace")):
            definitions.append(str(py.relative_to(BACKEND)).replace("\\", "/"))

    expect("the cap is defined in exactly one module",
           definitions == ["rate_limit.py"],
           f"defined in {definitions} - a second definition means the number a test "
           f"reads and the number the request path enforces can drift apart silently")


# ---------------------------------------------------------------------------
def scenario_two_users_cannot_share_one_rate_limit_lock() -> None:
    """The limiter's atomicity is a per-user advisory lock. Compose that with two users.

    Stated as a property rather than as an expected hash value. Pinning the literal
    would make this a second copy of the hashing decision, and it would fail every
    correct implementation the day someone changes the algorithm.
    """
    from uuid import UUID

    from backend import rate_limit

    a = UUID("11111111-1111-4111-8111-111111111111")
    b = UUID("22222222-2222-4222-8222-222222222222")

    expect("the same user always resolves to the same lock",
           rate_limit._advisory_lock_key(a) == rate_limit._advisory_lock_key(a))
    expect("two different users do not share a lock",
           rate_limit._advisory_lock_key(a) != rate_limit._advisory_lock_key(b),
           "a shared lock serialises unrelated users and, worse, lets one user's "
           "count gate another's")
    # THE COMPOSED ONE. `check_and_record` and `get_status` both normalise through
    # `_as_uuid` before deriving the key, and a user id genuinely arrives as both types
    # depending on the call site. If the normaliser is ever dropped from one path, that
    # path locks under a different key, the two stop serialising against each other, and
    # the effective cap silently doubles. Neither function's own unit test can see that -
    # it only exists where the two are used together.
    expect("a user id arriving as a string locks the same row as the UUID",
           rate_limit._advisory_lock_key(rate_limit._as_uuid(str(a)))
           == rate_limit._advisory_lock_key(rate_limit._as_uuid(a)),
           "the normaliser and the key derivation disagree, so the limit is enforced "
           "under two keys and the real cap doubles")


SCENARIOS = [
    scenario_no_unauthenticated_path_reaches_a_conversation,
    scenario_the_cap_is_one_number_and_only_one,
    scenario_two_users_cannot_share_one_rate_limit_lock,
]


def main() -> int:
    for fn in SCENARIOS:
        try:
            fn()
        except Exception as e:                                     # noqa: BLE001
            FAILURES.append(f"{fn.__name__} raised {type(e).__name__}: {e}")

    if FAILURES:
        for f in FAILURES:
            print(f"  HOLDOUT_FAIL  {f}", flush=True)
        print(f"HOLDOUT_FAILED scenarios={len(SCENARIOS)} assertions={ASSERTIONS} "
              f"failures={len(FAILURES)}", flush=True)
        return 1

    print(f"HOLDOUT_PASSED scenarios={len(SCENARIOS)} assertions={ASSERTIONS}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
