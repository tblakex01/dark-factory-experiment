#!/usr/bin/env python3
"""The E2E rung. Returns the number of steps asserted, or None if the journey broke.

READ THIS BEFORE TRUSTING A GREEN GATE FROM THIS FILE.

**This is a floor, not FACTORY_RULES.md section 4.** Section 4 is the real journey - sign
in, ask a question with a known answer, watch it stream, check the citation renders with a
timestamp deep-link, click it, see the modal open at the right moment. That runs today in
the validate-pr workflow's `behavioral-e2e` node via agent-browser, and it is the thing
with actual authority over a merge.

What is asserted here is the HTTP-level contract underneath it: the app is genuinely
serving, it reports its version, and the hard invariant that matters most - no anonymous
access to chat - actually holds against a live process rather than in a unit test with a
mocked dependency.

That is a real check and it is worth having. It is not the same claim as section 4, and
writing it here without saying so would be the exact failure this repo keeps filing
issues about: a smaller check wearing a bigger check's name.

**Porting section 4 into this file is the remaining work on component 5.** See FACTORY.md.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

TIMEOUT = 20


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def _post(url: str, payload: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def run_e2e(app) -> int | None:
    """`app` is the driver from appproc; `app.base` is the running server's root URL."""
    base = app.base.rstrip("/")
    steps = 0
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal steps
        steps += 1
        if not ok:
            failures.append(f"{name}: {detail}")

    # 1-2. It is genuinely up, and says so in the documented shape.
    status, body = _get(f"{base}/api/health")
    check("health returns 200", status == 200, f"got {status}")
    check("health body reports ok", "ok" in body.lower(), f"body={body[:200]!r}")

    # 3. It can say what it is. A server answering 200 on /health and nothing else is a
    #    load balancer, not an application.
    status, body = _get(f"{base}/api/version")
    check("version endpoint answers", status == 200, f"got {status}")

    # 4-5. MISSION hard invariant 2: authentication is required for all chat access.
    #      Asserted against a LIVE process, which is the only place it is really true -
    #      a unit test proves the decorator is present, not that the route is reachable
    #      without it after someone reorders the router.
    status, _ = _post(f"{base}/api/conversations", {})
    check("anonymous cannot create a conversation", status in (401, 403), f"got {status}")

    status, _ = _get(f"{base}/api/conversations")
    check("anonymous cannot list conversations", status in (401, 403), f"got {status}")

    if failures:
        for f in failures:
            print(f"  E2E_FAIL  {f}", flush=True)
        return None

    return steps
