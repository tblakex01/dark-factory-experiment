#!/usr/bin/env bash
# The stop button. Both halves of it.
#
#   bash scripts/factory-stop.sh          exit 0 = clear to dispatch, exit 1 = STOPPED
#
# The orchestrator is a bash script on the VPS at /opt/dark-factory/orchestrator.sh and
# it is deliberately not in this repository - it holds no state, and everything it reads
# is visible here as issues, PRs and labels. That had one bad consequence: the only off
# switch lived on a machine. Nothing in this repo could halt the factory, which meant the
# stop button was unreachable from anywhere except an SSH session.
#
# So the CHECK lives here, versioned and readable, and the orchestrator calls it first:
#
#   if ! bash /opt/dark-factory/repo/scripts/factory-stop.sh; then exit 0; fi
#
# Two mechanisms, on purpose, because they fail in different places.
#
#   1. A LOCAL kill file. Works with the network down, which is when you most want it.
#   2. A REMOTE label: any open issue tagged `factory:stop`. Reachable from a phone,
#      which is the entire reason it exists at 2am.
#
# Both are checked before anything else is read.

set -uo pipefail

REPO="${FACTORY_REPO:-coleam00/dark-factory-experiment}"
KILL_FILE="${FACTORY_KILL_FILE:-${FACTORY_WORKDIR:-.}/.factory-stop}"
STOP_LABEL="factory:stop"

# --- 1. the local half -------------------------------------------------------
if [ -f "$KILL_FILE" ]; then
  echo "STOPPED: $KILL_FILE present. Remove it to resume."
  [ -s "$KILL_FILE" ] && echo "reason: $(head -1 "$KILL_FILE")"
  exit 1
fi

# --- 2. the remote half, and it FAILS CLOSED ---------------------------------
# This is the polarity that matters and it is easy to get backwards. The obvious design
# is "the factory runs while a label is absent" - but an absent label cannot be told
# apart from an API call that failed to return it, so a network blip reads as "carry on"
# and the stop button works only while the network does.
#
# Inverted here: the label is something you ADD, and ANY error listing it counts as
# stopped. An unreadable stop button is a stop button you do not have.
if ! HITS=$(gh issue list -R "$REPO" --label "$STOP_LABEL" --state open \
              --json number,title --jq '.[] | "#\(.number) \(.title)"' 2>&1); then
  echo "STOPPED: cannot read the stop state from GitHub, halting: $HITS"
  exit 1
fi

if [ -n "$HITS" ]; then
  echo "STOPPED: an open issue carries $STOP_LABEL"
  echo "$HITS" | sed 's/^/  /'
  exit 1
fi

echo "STOP_CHECK_OK: no kill file, no $STOP_LABEL issue"
exit 0
