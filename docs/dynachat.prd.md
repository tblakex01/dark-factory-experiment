# DynaChat - Product Requirements

> **Provenance, stated plainly.** This document was written on 2026-08-12, and the
> factory has been running since April. It is a **reconstruction**: the scope it
> describes has governed the repository from the start, but it lived in `MISSION.md`
> and in a private planning note rather than in a product document.
>
> It is here because the mission is supposed to be a *compression of something*, and a
> compression with no source cannot be reconciled when the product moves. From here on
> the order is the normal one: this file changes first, `MISSION.md` changes with it, in
> the same commit.
>
> Deliberately excluded: the stack, the architecture, the data model, the file layout.
> Those are engineering decisions, they are settled in this codebase already, and a PRD
> that contains them is a spec nobody can change.

**Status:** live · **Owner:** human only · **Mission compressed from this:** `MISSION.md`

---

## The problem

A creator's back catalogue is the most useful thing they have made and the least
searchable. The answer to a viewer's question usually exists, in a video published
eighteen months ago, four minutes in - and there is no way to find it short of
remembering which video it was in and scrubbing for it.

YouTube search returns titles. It does not return the moment where something was
explained, and it cannot answer a question that spans three videos.

## Who it is for

Viewers of one configured channel who want to:

- ask a question about something the creator has covered, without re-watching
- find the specific moment where it was explained
- treat the back catalogue as a knowledge base they can interrogate in plain language

DynaChat is **not** a creator tool. The creator is not the user. Nobody logs in to
manage their channel; the admin surface exists only to keep the library current.

## The hypothesis, and what would falsify it

**Hypothesis:** a grounded answer with a timestamped citation is more useful than a
search result, because the citation is the thing that makes the answer checkable.

**What would falsify it:** viewers reading answers and not clicking citations. If the
citation is decoration rather than the point, the retrieval quality does not matter and
this is a worse chat interface than the ones that already exist.

That is why every answer cites, why the citation carries the quoted passage, and why
clicking one opens the video at the timestamp. The citation is the product.

## Scope for this version

**Content ingestion.** Every video from the configured channel, transcripts and
metadata, with scheduled sync so new uploads land without intervention. An admin view
for triggering a sync, adding a video, removing a video.

**Authenticated chat.** Google OAuth and email/password. No anonymous access. A
per-user daily message cap.

**Answers with rich citations.** Retrieval over transcript passages, streamed responses,
and every cited passage showing its video title, link, exact-timestamp deep link and the
quoted snippet. Clicking a citation opens a player at that timestamp beside the text.

**Conversation management.** Private per-user conversations that can be listed,
searched within, renamed, deleted and exported.

## Non-goals

Sorted, because the sort is the part that matters once an agent is reading this. **Never**
means the factory rejects it forever, including the quarter it becomes attractive.

**Never - additional surface area**
- Additional channels. Single-channel is an architectural assumption, not a limitation
  to be lifted.
- Any non-YouTube source: podcasts, articles, PDFs, uploaded files.
- A public API, webhooks, or third-party OAuth clients.
- Chat-platform integrations: Slack, Discord, Telegram.

**Never - product category changes**
- Payments, subscriptions, tiers, paywalls.
- Mobile apps, desktop apps, browser extensions.
- Social features of any kind: comments, reactions, bookmarks, follows, public sharing.
- Voice input or text-to-speech.

**Never - stack substitution presented as a feature**
- Alternative or user-selectable LLM providers, or local model support.
- A different embedding provider or model.

**Not yet, and therefore NOT in the mission's out-of-scope list** - these belong in the
backlog and the factory should not reject them on sight:
- Richer admin tooling around ingestion failures.
- Retrieval-quality work: re-ranking, chunking strategy, prompt iteration.

## Properties that cannot be edited

These are not features and no issue may argue them away. They are restated as hard
invariants in `MISSION.md` and as auto-reject triggers in `FACTORY_RULES.md`, because
the file read at reject time has to contain the rule.

1. **A per-user daily message cap.** It protects the inference budget, and a product
   whose cost scales with abuse is not a product.
2. **Authentication on every path that reaches the model.** No anonymous mode, no trial,
   no single free question.
3. **Conversations are private to their owner.** No share links, no admin reads.
4. **One channel, fixed at deploy time.**
5. **One inference provider.**

## Success

- A viewer asks a question and clicks a citation. That is the whole funnel.
- Answers stay correct as the catalogue grows - retrieval quality is the thing that
  degrades silently and it is what the end-to-end check exists to defend.
- The library stays current without anyone remembering to sync it.

## Open questions

Anything here is a `factory:needs-human`, never a guess:

- What the cap should be for a heavy but legitimate user.
- Whether conversation export is used enough to keep maintaining both formats.
