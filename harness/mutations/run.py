#!/usr/bin/env python3
"""MUTATION TESTING. Break the software on purpose and require the gate to notice.

    python harness/mutations/run.py

THE ONLY THING IN THIS GATE THAT MEASURES THE HARNESS RATHER THAN THE CODE. Everything
else answers "is this build good?". This answers "would this gate know if it were not?",
and they are completely different questions. Until one of these has been injected and
caught there is no evidence any check here can fail at all.

═══════════════════════════════════════════════════════════════════════════════════════
TWO DELIBERATE DEVIATIONS FROM THE SKILL'S TEMPLATE, both forced by this repo.
═══════════════════════════════════════════════════════════════════════════════════════

**1. It mutates IN PLACE and restores with git, instead of copying the tree.**
The template copies `["app", "tests", "harness", ".factory"]` into a temp dir per defect.
Here `app/` contains `app/backend/.venv` and `app/frontend/node_modules` - gigabytes, and
several minutes per defect. Excluding them instead breaks the copy, because the checks
need that venv to run at all.

So: apply the mutation to the real file, run the checks, and restore with
`git checkout --`. The tree must be CLEAN before this starts, which is asserted below,
and every path restores in a `finally`. If this process is killed mid-defect, `git status`
shows exactly one modified file and `git checkout -- <file>` is the fix.

**2. It runs `ci.py --quick` PLUS the holdout, not the full `ci.py`.**
The full gate starts the backend, which requires a validation env that holds secrets and
lives outside the repo. On any machine without it the app refuses to start and the gate
exits non-zero - which would mark every single defect CAUGHT, for a reason that has
nothing to do with the defect. A mutation suite that passes because the app cannot boot
is worse than no mutation suite, so the E2E rung is excluded rather than faked.

The consequence is stated rather than hidden: **these four defects are caught by static,
unit and holdout only.** A defect that only the browser journey could catch would escape
here and this file would not know. That is a real hole and it is the same hole
`harness/README.md` names - section 4 lives in the workflow, not in this harness yet.

Emits `MUTATIONS_TOTAL=N` and `MUTATIONS_CAUGHT=N`. The gate requires them equal.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEFECTS = Path(__file__).resolve().parent / "defects.json"


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def tree_is_clean() -> bool:
    return not git("status", "--porcelain").stdout.strip()


def apply(defect: dict) -> bool:
    target = ROOT / defect["file"]
    if not target.exists():
        return False
    body = target.read_text(encoding="utf-8")
    if defect["find"] not in body:
        return False
    target.write_text(body.replace(defect["find"], defect["replace"], 1), encoding="utf-8")
    return True


def run_checks() -> tuple[bool, str]:
    """Returns (went_red, which_rung). Runs the rungs a mutation build can honestly use."""
    env = dict(os.environ, FACTORY_IN_MUTATION="1")

    quick = subprocess.run([sys.executable, "harness/ci.py", "--quick"], cwd=ROOT,
                           env=env, capture_output=True, text=True, timeout=900)
    if quick.returncode != 0:
        rung = "gate"
        for line in (quick.stdout or "").splitlines():
            if line.startswith("GATE_FAILED:"):
                rung = line.split(":", 1)[1].strip()
        return True, rung

    holdout = subprocess.run([sys.executable, ".factory/holdout/run.py"], cwd=ROOT,
                             env=env, capture_output=True, text=True, timeout=900)
    if holdout.returncode != 0:
        return True, "holdout"

    return False, ""


def main() -> int:
    if not DEFECTS.exists():
        print("MUTATIONS_ABSENT no defects.json next to this script", flush=True)
        return 0

    if not tree_is_clean():
        # REFUSE. Restoring with `git checkout --` would destroy uncommitted work, and a
        # mutation runner that eats your changes is a tool nobody runs twice.
        print("MUTATIONS_REFUSED the working tree is dirty. This runner mutates in place "
              "and restores with git, so it will not start on an unclean tree. Commit or "
              "stash first.", flush=True)
        return 1

    defects = json.loads(DEFECTS.read_text(encoding="utf-8"))["defects"]
    total = caught = not_injected = 0

    print("MUTATION_START", flush=True)
    for d in defects:
        total += 1
        injected = False
        try:
            if not apply(d):
                # NOT a pass. The anchor moved, so this defect tested nothing - and a
                # mutation set that silently stops injecting reports a perfect score for
                # doing nothing at all.
                not_injected += 1
                print(f"  NOT_INJECTED  {d['id']:<38} anchor not found in {d['file']}",
                      flush=True)
                continue
            injected = True
            went_red, rung = run_checks()
            if went_red:
                caught += 1
                print(f"  CAUGHT        {d['id']:<38} by {rung}", flush=True)
            else:
                print(f"  ESCAPED       {d['id']:<38} <-- {d['why']}", flush=True)
        finally:
            if injected:
                git("checkout", "--", d["file"])

    if not tree_is_clean():
        print("MUTATIONS_DIRTY the tree did not restore cleanly - inspect `git status` "
              "before trusting anything above", flush=True)
        return 1

    print(f"MUTATIONS_TOTAL={total}", flush=True)
    print(f"MUTATIONS_CAUGHT={caught}", flush=True)
    print(f"MUTATIONS_NOT_INJECTED={not_injected}", flush=True)
    if caught == total and not_injected == 0:
        print("MUTATIONS_OK", flush=True)
        return 0
    print("MUTATIONS_FAILED - every escaped defect is a class of bug that can currently "
          "merge unreviewed", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
