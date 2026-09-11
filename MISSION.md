# Mission

**Derived from:** `docs/dynachat.prd.md`
**Last reconciled with that PRD:** 2026-08-12

> This file is the PRD compressed to the part the factory has to obey. When the product
> changes, both files change in the same commit - otherwise the factory keeps faithfully
> building the old scope and nothing warns you. The PRD is a live document here, not a
> kickoff artifact.

## What DynaChat Is

DynaChat is a RAG-powered chat interface that lets viewers ask questions about a single YouTube channel's back catalog and get answers grounded in the actual video content. Every answer cites the videos it came from, with deep-links that jump straight to the timestamp where the relevant moment happens.

For the initial deployment, the channel is Cole Medin's YouTube channel. The architecture assumes one channel, one deployment.

## Who It's For

Viewers of the configured channel who want to:
- Ask questions about topics the creator has covered without having to re-watch old videos
- Find the specific moment in a video where something was explained
- Use past videos as a searchable knowledge base they can interrogate in natural language

DynaChat is not a creator tool, a general-purpose AI assistant, or a multi-tenant SaaS. It is a public-facing chat interface wrapped around one creator's content.

## Core Capabilities (In Scope)

**Content ingestion**
- Ingest every video from the configured YouTube channel (transcripts + metadata)
- Automatic channel sync on a schedule so new uploads land in the RAG database without intervention
- Admin-only UI for manually triggering a sync, adding a specific video, or removing a video

**Authenticated chat**
- Google OAuth sign-in
- Email + password sign-in
- All chat access requires authentication — there is no anonymous mode
- Per-user daily message cap of **25 messages per 24 hours** (see Hard Invariants below)

**RAG responses with rich citations**
- Hybrid retrieval over the channel's transcript chunks
- Streaming responses rendered in the chat UI
- Every cited chunk shows: video title, link to the video, exact-timestamp deep-link, and the quoted transcript snippet
- Clicking a citation opens a modal with an embedded YouTube player that starts playing at the cited timestamp, alongside the transcript snippet

**Conversation management**
- Each user has private conversations, visible only to them
- Users can list and browse their own conversation history
- Users can search within their own conversation history
- Users can rename and delete their own conversations
- Users can export a conversation as markdown or PDF

**Administrative surface**
- A logged-in admin view for managing the video library (add / remove / re-sync)
- Admin is identified by a hardcoded user identifier, not by a role system

## Out of Scope (Factory Must Never Build)

The factory is forbidden from accepting issues that expand the product in any of these directions. Issues asking for these things must be rejected at triage.

**Content sources**
- Adding support for additional YouTube channels beyond the configured one
- Any non-YouTube content source (podcasts, articles, PDFs, transcripts from other platforms, uploaded files)

**LLM and embedding stack**
- Swapping the LLM provider away from OpenRouter
- Adding alternative LLM providers as user-selectable options
- Swapping the embedding provider or model
- Adding local/self-hosted model support (Ollama, llama.cpp, etc.)

**Monetization and distribution**
- Payments, subscriptions, tiers, paywalls, or any monetization feature
- Mobile apps (React Native, Flutter), desktop apps (Electron, Tauri), or browser extensions

**Customization and personalization**
- User theming beyond whatever ships by default (no dark/light toggle unless already present, no custom colors)
- Profile pages, avatars, display names beyond what auth provides
- User-editable system prompts or model parameters

**Social and community features**
- Comments or replies on messages, answers, or videos
- Likes, upvotes, reactions, bookmarks, follows, or any social graph
- Sharing conversations publicly (conversations are strictly private — see Hard Invariants)

**Audio and alternative input modes**
- Voice input (speech-to-text)
- Text-to-speech output or read-aloud features
- Any audio processing beyond what the transcript ingestion pipeline already does

**External integrations**
- Slack, Discord, Telegram, or any chat platform integrations
- Webhooks sent to third-party services
- A public REST or GraphQL API for third parties to query the RAG database
- OAuth app registration for third-party clients

## Hard Invariants (Not Tunable by Factory Issues)

These are not features. They are constraints that define what DynaChat is. The factory is explicitly forbidden from modifying them even if an issue asks nicely, explains a good reason, or claims it's a bug.

1. **Daily message cap is 25 messages per user per 24 hours.** This number protects the OpenRouter budget. Any issue requesting the cap be raised, lowered, removed, made configurable, or bypassed for specific users must be rejected at triage as a security concern. Only a human commit can change this value.

2. **Authentication is required for all chat access.** No anonymous mode, no trial mode, no preview mode, no "one free question" escape hatch. Every request that hits the LLM must be attributable to an authenticated user.

3. **Conversations are private to their owner.** No share links, no public conversations, no admin access to user conversations. The only reads of a conversation are by its owner.

4. **The factory cannot modify governance files.** `MISSION.md`, `FACTORY_RULES.md`, and `CLAUDE.md` are the constitution. Any PR that touches them is an automatic reject.

5. **The channel is hardcoded.** DynaChat is single-channel by design. Support for additional channels is not a feature the factory can add later — it's out of scope forever.

## Allowed Evolutions

These are explicitly in scope and the factory can work on them when issues are filed:

- **Postgres migration.** DynaChat ships on SQLite. Migrating to Postgres is an allowed architectural change when an issue is filed for it. This is the one database-layer change the factory may perform.
- **Admin UI improvements.** The admin surface for managing the video library can grow.
- **Conversation management UX.** Browse, search, rename, delete, and export can all be improved.
- **Retrieval quality.** Chunking, re-ranking, embedding strategies, and prompt engineering are fair game as long as citations remain accurate.
- **Citation UX.** The citation modal, timestamp player, and transcript rendering can all evolve.

## Quality Standards (Definition of Done)

Every change the factory ships must clear all three gates. A PR that skips any of these is not done.

**Gate 1 — Static checks pass**
- Type-check: zero errors
- Lint: zero warnings
- Format: clean
- Build: succeeds
- Unit and integration tests: all pass

**Gate 2 — UI is discoverable without docs**
- Any new user-facing feature must be usable by a first-time visitor without reading external documentation
- No hidden keyboard shortcuts, no undocumented URL parameters, no "you have to know about this" affordances
- If a feature needs an explanation, the explanation belongs in the UI

**Gate 3 — Full end-to-end regression test via agent-browser**
Every change — bug fix, feature, refactor, docs update that touches runnable code — must pass an end-to-end browser test that exercises the full happy path:

1. Start the backend and frontend
2. Sign in as a test user
3. Open a new conversation
4. Send a question about a known video in the RAG database
5. Verify the response streams in
6. Verify the response renders with citations (title, timestamp link, quoted snippet)
7. Click a citation and verify the modal opens with an embedded player at the correct timestamp

This regression test runs via the `agent-browser` CLI (see `.claude/skills/agent-browser/SKILL.md`). It is not optional. A PR that skips it is not done, regardless of whether the change "seems unrelated" to the chat flow.

## Non-Goals (Things DynaChat Is Explicitly Not Trying To Be)

- A platform
- A multi-tenant SaaS
- A creator tool sold to other YouTubers
- A general AI assistant
- A social network
- A monetized product
- A mobile app
- A marketplace
- A developer tool with an API

DynaChat is a focused chat interface over one creator's YouTube content. Every feature decision should reinforce that focus. When in doubt, the answer is "that's out of scope."
