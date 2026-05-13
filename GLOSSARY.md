# Glossary

Terms used throughout the planning docs and code. See [[PLAN-v1.2]] for full context.

## Concepts

**Organization (Org)** — Top-level tenant in a single Helm install. Owns members, brand kits, social accounts, MCP integrations, billing. Future external clients = additional Orgs with `is_external=true`. GitHub-shaped (like a GitHub org). See [[PLAN-v1.2#1.-Hierarchy]].

**Project** — Sub-unit inside an Org. Owns goals, KPIs, brief, team assignments, and a chosen subset of the Org's social accounts. Team members are assigned per-project with project-level roles.

**Campaign** — A time-boxed initiative inside a Project (e.g., "Q2 Launch Week").

**Asset** — Output of an agent. A social post, image, video, blog draft, ad creative.

**Brand Kit** — Per-Org (or per-Project override) visual and voice identity. Logo, palette, fonts, voice sliders, do-say/don't-say lists, personas. Versioned. See [[PLAN-v1.2#Theme-Q1]].

## Roles & access

**Supervision scope** — What human roles actually grant in v2.0. Agents do the work; humans *supervise* their corresponding agent's Station, approve actions, override outputs. Roles are scoping labels, not job descriptions. See [[PLAN-v1.2#2.1-The-reframe]].

**Station** — Per-role UI surface where a human watches and steers their agent. Studio Station (Creatives), Calendar Station (SMM), Search Station (SEO), Spend Station (Paid Media), Insights Station (Analyst), Conductor Station (Manager), Approval Inbox (Reviewer), System Console (Admin).

**T0–T3 Tiering** — Progressive disclosure of role complexity by team size. T0 = solo (just Admin). T3 = agency-scale (full grid + custom roles).

## Agent runtime

**Agent** — A specialist that does real work. Has a system prompt (its role), a toolbelt (MCP tools), persistent memory (the Knowledge Graph), and produces audit-logged actions.

**Conductor** — Manager-level agent. Decomposes briefs from human Manager into per-role tasks, dispatches to role-Agents, escalates when stuck. Reports rollup status to the Manager Station.

**Claude Agent SDK** — Anthropic's framework for building agents. Native MCP support, sub-agent patterns, persistent memory. Our chosen runtime. See [[PLAN-v1.2#A.5-Agent-runtime]].

**MCP (Model Context Protocol)** — Standard way agents talk to external systems. Every social platform, CRM, drive, etc. is an **MCP server** exposing typed tools the agent can call. Our integration hub (Theme D) is the MCP registry layer.

## Autonomy & gating

**Autopilot** — Trust mode for internal-only actions (drafts, research, summaries, KG updates). Agent acts immediately; logged in audit trail.

**Soft gate** — Trust mode for customer-facing low-risk actions. Agent proposes; auto-approves after a timeout unless a reviewer objects.

**Hard gate** — Trust mode for high-stakes actions (outbound posting, sending email to >1k, ad spend > threshold, brand-kit changes). Agent prepares; human must explicitly approve before it fires. **All outbound posting is Hard-gate by default.**

**Approval Inbox** — The human's primary UI surface for Hard-gate items. List of pending agent outputs; approve / reject / regenerate / edit-and-approve.

## Data & memory

**Knowledge Graph (KG)** — Shared memory all agents read from and write to. Stored as embeddings in Postgres + pgvector plus structured entity tables. Brand kit, personas, past wins/failures, performance history, content embeddings. **Org-scoped — no cross-Org leak.** See [[PLAN-v1.2#Theme-Q3]].

**Ingestion** — Process of pulling external content into the KG. Sources: URLs (crawler), files (PDF/DOCX/etc.), git repos, zip archives. Output: chunked text + embeddings + extracted entities. See [[PLAN-v1.2#Theme-Q2]].

**Audit trail** — Every agent action records timestamp, agent identity, inputs used, alternatives considered, confidence, output, approver, cost. Humans can replay any decision.

## Channels

**SocialAccount** — A single (Org, platform, handle) triple. One Org can have N accounts on the same platform (3 X handles, 2 LinkedIn pages, etc.). Each is its own OAuth grant. Publisher adapters take a `social_account_id`, never just `platform`.

**Publisher adapter** — Per-channel code in `app/services/publishing/{channel}.py` that knows how to draft, schedule, and publish for that platform. Encapsulates rate limits and content-shape rules.

## Phases

**Phase 0 — Baseline** — Plumbing: alembic baseline, auth (Org/User/Project), Celery+Redis worker, S3/MinIO storage, audit log + approval queue, Helm chart rebuild.

**Phase 1 — Theme Q (Foundation)** — Brand Setup Studio, Input Channel Hub, Knowledge Graph, Freshness, Goals, Project Wizard. The onboarding flow. Agents have nothing to work with until Q is set up.

**Phase 2 — Agent Runtime + Creatives MVP** — Claude Agent SDK integration, Conductor shell, Creatives Agent end-to-end, Approval Inbox UI, trust-mode resolver.

**Phase 3 — Full Role Fleet** — SMM, SEO, Paid Media, Analyst agents + their Stations.

**Phase 4 — Multi-channel Publishing** — `SocialAccount` model, per-platform adapters, real Resend email integration.

**Phase 5 — Docs + Marketing** — README, USER-GUIDE, ARCHITECTURE, API ref, slides, one-pager, demo video, `v1.0.0` tag.

**Phase 6 — Polish + External Clients** — Tier 3 role UI, Client Portal (when `is_external=true` flips on), white-label. Post-deadline.
