# Decisions

Product values the factory chose on its own, and the questions it stopped to ask.

**How this file works.** `FACTORY_RULES.md` §7 splits values in two. A **product** value -
a price, a rate, a default, a name, a layout - the factory may choose, record here, and
carry on; the merge is held for a human but the work is not blocked. A **judgement**
value - a lock, a floor, a tolerance, a sample size, a required marker - it may never
choose, because choosing one is tuning the judge.

**Ask a given decision once.** A second issue that needs the same answer references the
ID and carries on. It does not re-ask. An earlier version of this rule told the plan node
to stop for "an answer to any open question", and a PRD that was honest about what it had
not settled blocked every issue downstream of it - four issues, four escalations, zero
PRs, and the same question asked four times. The more honest the spec, the less the
factory could do.

Append only. Newest at the bottom.

---

## D-001 · The e2e floor is not set

**Status:** open · **Raised:** 2026-08-13 · **Blocks:** nothing today

`.factory/locks/floor.json` carries floors for unit, static, holdout and mutations, and
deliberately none for e2e. `harness/e2e.py` asserts five HTTP-level checks, but running
them requires the validation env that lives outside the repo, so the number has never
been observed on a real run.

**Recommendation:** run `python harness/ci.py` on the VPS, where
`/opt/dark-factory/validation.env` exists, and add `e2e_steps` to the lock at whatever it
actually reports. Not before - a floor nobody has watched the harness clear is the same
kind of claim this directory exists to refuse.

This is a **judgement** value, so the factory may not set it. That is the correct
behaviour and it is why this entry exists rather than a number.

---

## D-002 · Section 4's journey lives in two places

**Status:** open · **Raised:** 2026-08-13 · **Blocks:** nothing today, everything eventually

`FACTORY_RULES.md` §4 defines the eleven-step agent-browser journey. It runs in the
validate-pr workflow's `behavioral-e2e` node, and it is the check with real authority
over a merge. `harness/e2e.py` asserts a much smaller HTTP-level floor.

So "the app works" has two definitions, and only one of them is in the harness the
`build-dark-factory` skill expects to be authoritative.

**Recommendation:** port §4 into `harness/e2e.py` and have the workflow node call the
harness rather than reimplement it, so there is one definition. Until then the workflow's
version is authoritative and the harness's is a floor - stated in `harness/README.md` so
nobody reads a green `GATE_OK` as the journey having passed.

---

## D-003 · Three of four mutations are caught below the independence line

**Status:** open · **Raised:** 2026-08-13

Measured 2026-08-13: `cap-raised-to-100` caught by unit, `uuid-normaliser-dropped` and
`conversations-list-loses-its-guard` caught by static, `lock-key-is-constant` caught by
the holdout. One above the line, three below.

Below-the-line checks are ones the builder can read and edit, so a defect caught only
there is a defect a sufficiently motivated agent could arrange not to be caught. The
cause is the shape of the defects rather than a weakness in the holdout: all three break
type-checking rather than behaviour, and the compiler finds those. Rewriting
`lock-key-is-constant` to be type-clean is what moved it above the line.

**Recommendation:** give the other two the same treatment - a mutation that type-checks
and is behaviourally wrong - and add defects aimed at the RAG and citation path, which is
where DynaChat's value actually lives and where nothing currently probes at all.
