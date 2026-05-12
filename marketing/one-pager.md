# DClaw Marketing

**The agent-driven marketing operating system. You set the brand once; the agents do the work.**

---

## The problem

Marketing teams of five spend 40% of their week on mechanical work: drafting variants, scheduling posts, monitoring inboxes, writing reports. Solo founders skip marketing entirely — they don't have the bandwidth.

Existing tools (Hootsuite, Buffer, Jasper, HubSpot) ship features for humans to operate. None of them ship a **crew that does the work for you**.

## What we built

DClaw Marketing replaces "tool you operate" with "crew you supervise". A small fleet of AI agents — Creatives, Social Media Manager, SEO, Paid Media, Analyst — each backed by a real LLM and a Knowledge Graph of your brand + content history.

You spend 15 min/day in the **Approval Inbox**. The agents do the rest.

## How it works

1. **One-time setup**: configure your Brand Kit (palette, voice, do-say / don't-say) and ingest your context (briefs, past content, customer interviews, brand books — any file).
2. **The Knowledge Graph** indexes everything via 1536-dim embeddings + cosine similarity.
3. **Brief in.** Tell the Creatives Agent what you want — "announce our Q2 release on LinkedIn".
4. **Variants out.** The agent pulls your brand kit + retrieves relevant context + drafts N variants in your voice.
5. **You approve.** Each variant lands in the Approval Inbox. Approve, reject with a reason, or regenerate. Outbound publishing is always Hard-gated — agents never publish without consent.
6. **Repeat across channels** — LinkedIn, X, Instagram, Threads, Bluesky, …

## What's different

| Existing tools | DClaw Marketing |
|---|---|
| You operate the tool | The agents operate; you supervise |
| Templates | Generation from your brand voice + context |
| Bolt-on AI feature | AI is the whole product |
| One channel per dashboard | One supervision surface across every channel |
| Trust by hope | 4-eye approvals + full audit trail |

## Built for

- **Solo founders** drowning in DIY marketing
- **Marketing teams of 1–10** scaling output without scaling headcount
- **Agencies** (v0.2+) running 10× more client work per FTE

## Inspired by

The best agent-shaped patterns from Y Combinator: Copy.ai (templates), Letterdrop (sales→social), Persana (ICP scoring), Junia (SEO blogs), Mutiny (personalised pages), Sutro (prompt→landing page), Outset (customer research), Magic Loops / Wordware (visual workflows), Lindy / Embra (workspace agents), Decagon / Sierra (customer-facing AI), Cluely (real-time AI overlay).

## Stack

FastAPI · Next.js 14 · Postgres + pgvector · Redis · Celery · MinIO · Claude Agent SDK · Anthropic API · OpenAI embeddings · Helm-shipped to Kubernetes · Light-mode-only DClaw brand system.

## What ships in v0.1.0 (May 2026)

Multi-tenant Org/Project hierarchy · admin-only user creation with mandatory first-login reset · versioned Brand Kits · file ingestion pipeline · Knowledge Graph with semantic search · Creatives Agent (LinkedIn / X / Instagram / Threads / Bluesky) · Approval Inbox with audit log + 4-eye rule · background workers + SSE progress · object storage · ~100 backend tests.

## Roadmap

**v0.2** — Conductor agent + full role fleet (SMM/SEO/Paid Media/Analyst) + real social publishing adapters + Helm chart with bundled deps + dual TLS.

**v1.0** — Themes J–P from PLAN-v1.2.md: Client Operations, Project Management, Time Tracking & Billing, Client Reporting, Knowledge Base & SOPs, Client Portal, Visual Workflow Builder.

---

Repo: [github.com/dclawstack/dclaw-marketing](https://github.com/dclawstack/dclaw-marketing) · Plan: [PLAN-v1.2.md](../PLAN-v1.2.md) · Docs: [USER-GUIDE](../docs/USER-GUIDE.md) · [ARCHITECTURE](../docs/ARCHITECTURE.md)
