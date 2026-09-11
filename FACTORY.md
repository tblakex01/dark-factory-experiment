# The factory

<!--
  Maintainer: whoever changes what runs unattended. Update the level and the date in the
  SAME commit that changes either - a stale level here is a lie about what is running
  with nobody watching.
-->

**Current autonomy level: 4** - an untriaged issue is classified, planned, built,
reviewed, independently validated and **merged** with no human in the chain. A person
files the issues and promotes releases.
**Level 5 is deliberately not the goal.** The factory does not write its own issues.
**Stop button:** `.factory-stop` in the orchestrator's working copy (works with the
network down) **and** the `factory:stop` label on any open issue (reachable from a
phone). Both fail closed. Checked by `scripts/factory-stop.sh` before anything else is
read. Tested on purpose, both directions, 2026-08-12.
**Built from PRD:** [`docs/dynachat.prd.md`](docs/dynachat.prd.md) - `MISSION.md` is its
compression. **Change one, change both**, in the same commit. Nothing warns you: the
factory will keep faithfully building the old scope until someone notices.

## The five components, as built here

| # | Component | This repo's version |
|---|---|---|
| 1 | Workflow-driven repo | **Archon**, four YAML workflows in `.archon/workflows/`. State in GitHub labels |
| 2 | The trigger | Pure-bash orchestrator on the VPS at `/opt/dark-factory/orchestrator.sh`, cron every 30 min, `MAX_PARALLEL=4` with per-target locks |
| 3 | Deployment | `deploy/deploy.sh` - polls `main`, rebuilds the inactive colour, waits for the Docker healthcheck, swaps the Caddy upstream. Rollback is flipping it back |
| 4 | Guidance layer | `MISSION.md` · `FACTORY_RULES.md` · `CLAUDE.md`, all three protected |
| 5 | Validation harness | `harness/ci.py` (added 2026-08-13) **plus** the agent-browser journey in the validate-pr workflow. See the gap below |

**The orchestrator is deliberately not in this repo.** It holds no state of its own, and
everything it reads is visible here as issues, PRs and labels. The one bad consequence -
that the only off switch lived on a machine - is fixed: `scripts/factory-stop.sh` is
versioned here and the orchestrator calls it first.

## The gates that are actually code

Everything else is a prompt instruction, which is a suggestion with good manners. These
cannot be argued past:

1. **`apply-verdict`** in `dark-factory-validate-pr.yaml` - bash reads a verdict file and
   branches on it. The merge is never a model deciding to merge.
2. **The `APP_STARTED` backstop**, same node. Deterministic bash reads `start-app`'s
   output and flips any `approve` to `reject`+escalate when the marker is absent.
   Added after PR #80 (`3fc03a0`).

**Two. That is the honest number**, and it is why component 5 is the one that decides
whether the other four produced anything worth keeping.

## The end-to-end path

`FACTORY_RULES.md` section 4, eleven steps, driven with agent-browser in the validate-pr
workflow's `behavioral-e2e` node: sign in, open a conversation, ask a question with a
known answer, watch it stream, check the citation renders with title + link + timestamp +
quoted snippet, click it, confirm the modal opens at the cited moment.

**That journey is not yet in `harness/`.** See below.

## Component 5, stated honestly

`harness/` was added 2026-08-13 to give this repo the single validate entrypoint the
`build-dark-factory` skill expects. What it genuinely provides:

```
python harness/ci.py --quick
  HARNESS_START mode=quick driver=http
  STATIC_OK
  UNIT_PASSED tests=549
  GATE_OK mode=quick
```

Real, measured, and reproducible: 390 backend tests + 159 frontend, ruff + ruff-format +
mypy + tsc + biome. The full run additionally starts the backend and asserts five
HTTP-level checks, including MISSION hard invariant 2 against a live process.

Above the independence line, added the same day:

```
python .factory/holdout/run.py     HOLDOUT_PASSED scenarios=3 assertions=9
python harness/mutations/run.py    MUTATIONS_TOTAL=4 CAUGHT=4 NOT_INJECTED=0
```

`.factory/holdout/` holds three composed scenarios aimed at MISSION hard invariants 1
and 2, `harness/mutations/` holds four defects that all go red, and
`.factory/locks/floor.json` is the ratchet with zero slack.

**Read the holdout's header before citing it.** It was written 2026-08-13, after the
code it judges - so it is a floor from today forward, with authority over future diffs
and none over the 390 PRs already in `main`. A holdout's first rule is that it precedes
the work; stating plainly that this one does not is the difference between a holdout and
a directory named like one.

**What is still missing, named rather than quietly absent:**

| Gap | Consequence | Tracked |
|---|---|---|
| Section 4's journey is in the workflow, not in `harness/e2e.py` | Two definitions of "the app works". The workflow's is authoritative; the harness's is a floor | D-002 |
| Only **1 of 4** mutations is caught above the independence line | The gate depends mostly on checks the builder can read and edit | D-003 |
| No e2e floor in the ratchet | The number has never been observed - it needs the validation env, so measure it on the VPS | D-001 |
| No mutation probes the RAG or citation path | The product's actual value is unexercised by the thing that measures the harness | D-003 |

## Incident log

Append only. Every entry is a rule that now exists because of it.

| Date | What happened | What changed |
|---|---|---|
| 2026-04-14 | The first twelve hours of the factory were quoting, heredocs and shell escaping across a Windows `bash -c` boundary. Almost nothing was about AI | The agent is the interchangeable part; the plumbing is not |
| 2026-04-15 | The verdict schema allowed `e2e_status: "not_e2e_testable"`, giving the model an honest-looking exit when the app failed to start. The health poll also targeted `/health`, but the backend only serves `/api/health` - so every run would have failed identically and masked the real bug | Rule 0 gained an explicit FORBIDDEN clause. **An enum value with no deterministic check behind it is an escape hatch** (`c4997c4`) |
| 2026-04-18 | `start-app` launched uvicorn with no env, the backend crashed at import with `RuntimeError: DATABASE_URL is not set`, and the synthesizer scored it `not_e2e_testable`. **PR #80 auto-merged having never been driven through a browser**, and was reverted the same day | The deterministic `APP_STARTED` backstop. Bash reads the raw output and overrides the model (`3fc03a0`) |
| 2026-05 → 2026-08 | The factory ran on a 30-minute cron for roughly three months and found nothing to do. A benchmark run had parked all 17 open issues as `factory:in-progress`, and the priority order correctly refuses to start new work while work is in flight. **The rule that keeps a factory healthy is the rule that starved it** | Backlog cleared by hand 2026-08-11 (`#364`). A stall reaper is the outstanding fix |
| 2026-08-12 | The comprehensive-test workflow scored an unreadable result as a clean one: a missing fenced JSON block set `FAILURES_JSON=[]` and printed ALL GREEN | Both paths exit non-zero, and the run emits `SCENARIOS_RAN` (`c97f9ff`) |
| 2026-08-12 | The only off switch lived on the VPS, unreachable except over SSH | `scripts/factory-stop.sh`, versioned here, called first by the orchestrator. Fails closed |
