# The validation harness

```bash
python harness/ci.py --quick   # static + unit. ~3 min. Runs anywhere.
python harness/ci.py           # the whole gate. Needs the validation env (below).
```

Measured 2026-08-13 on `main`:

```
HARNESS_START mode=quick driver=http
STATIC_OK
UNIT_PASSED tests=549
GATE_OK mode=quick
```

549 = 390 backend (pytest, 67 skipped) + 159 frontend (vitest).

## What is in here, and where it came from

| File | Origin |
|---|---|
| `ci.py` · `appproc.py` | **Verbatim from the `build-dark-factory` skill.** The ladder and the app-process manager are the same in every factory; do not edit them here. |
| `harness.config.json` | This repo. Every command DynaChat runs. |
| `static.py` · `unit.py` | This repo. `ci.py` runs one command per rung and DynaChat is two stacks, so the split lives here rather than in the ladder. |
| `serve.py` | This repo. Starts the backend, or refuses with a named reason. |
| `e2e.py` | This repo. **A floor, not the full journey - read the next section.** |

Every command in `harness.config.json` is lifted from
`.archon/workflows/dark-factory-validate-pr.yaml`, so there is one definition of a green
build. **If you change one, change the other**, or the gate and the workflow will
disagree about what passing means and only one of them decides a merge.

## The honest gap

**This harness does not yet run FACTORY_RULES.md section 4.** Section 4 is the real
journey - sign in, ask a question with a known answer, watch the response stream, check
the citation renders with a timestamp deep-link, click it, see the modal open at the
right moment. That runs today in the validate-pr workflow's `behavioral-e2e` node via
agent-browser, and it is what actually has authority over a merge.

`e2e.py` asserts the HTTP contract underneath it: the app is genuinely serving, it can
report its version, and MISSION hard invariant 2 (no anonymous access to chat) holds
against a live process rather than against a mock. Five assertions. Real, worth having,
and **a smaller claim than section 4.**

## What exists above the independence line

```
python .factory/holdout/run.py     HOLDOUT_PASSED scenarios=3 assertions=9
python harness/mutations/run.py    MUTATIONS_TOTAL=4 CAUGHT=4 NOT_INJECTED=0
```

- **Holdout** - `.factory/holdout/run.py`, three composed scenarios aimed at MISSION
  hard invariants 1 and 2. Read its header before citing a green result: **it was
  written 2026-08-13, after the code it judges.** That makes it a floor from today
  forward, with authority over future diffs and none over the 390 PRs already in `main`.
- **Mutation set** - `harness/mutations/`, four defects, all four caught.
- **Ratchet** - `.factory/locks/floor.json`, floors set equal to what is observed today
  so the slack is zero.

**The number that matters is 1.** Of four mutations, exactly one is caught *above* the
independence line - `lock-key-is-constant`, by the holdout. The other three are caught by
static or unit, which the builder can read and edit. The cause is the shape of those
defects rather than a weakness in the holdout: they break type-checking rather than
behaviour, and the compiler finds those. See `.factory/decisions.md` D-003.

Re-run the mutation set after any harness change. If nothing is caught above the line,
the gate has become entirely dependent on checks the builder controls.

## The validation env

The backend hard-requires `DATABASE_URL`, `OPENROUTER_API_KEY`, `JWT_SECRET`,
`SUPADATA_API_KEY` and `YOUTUBE_CHANNEL_ID` at **import** time. `serve.py` refuses to
start without them and names which are missing:

```
APP_START_REFUSED missing=DATABASE_URL,OPENROUTER_API_KEY,...
```

That refusal is deliberate. On 2026-04-18 the workflow launched uvicorn without loading
them, the process crashed at import, the health poll failed, and the synthesizer scored
it as `not_e2e_testable`. PR #80 auto-merged having never been driven through a browser
(`3fc03a0`). **A step that cannot run has to be loud, not absent.**

The file lives outside the repo because it holds secrets. Override the path with
`DARK_FACTORY_VALIDATION_ENV`; on the VPS it is `/opt/dark-factory/validation.env`.
Point it at a **dedicated validation database** - an E2E against production data is a
data-loss incident waiting for a slow afternoon.
