# Project Overview

## What DClaw Marketing is

**An agent-driven marketing operating system.** A small team — or one operator plus AI agents — runs a full marketing function. Humans set the brand kit and feed in source material; AI agents draft content, schedule posts, run ads, surface analytics, and propose actions. Humans supervise from their **Station** and approve outbound actions in an **Approval Inbox**. Agents never publish without consent.

The system is:
- **Multi-tenant by design** — Organization → Project → Asset hierarchy with strict isolation.
- **Brand-aware** — versioned BrandKit + KG write-back insights injected into every agent prompt.
- **Knowledge-grounded** — file/URL/git ingestion → embeddings → semantic search.
- **Auditable end-to-end** — every admin action, agent run, and publish is recorded.
- **Cost-metered** — every LLM call lands in the cost ledger; sliding-window QuotaCounter + cost-cap prevent runaway spend.

## Target audience

| Persona | What DClaw does for them |
|---------|--------------------------|
| Solo Operator | One person running marketing for one business. DClaw acts as their force multiplier. |
| Boutique Agency | 2–10 people serving multiple clients. Tenant isolation, white-labelled dashboards, retainer + invoices + time tracking. |
| In-House Marketing | Growing company's marketing team. Goal alignment, approval workflows, attribution, one pane across CRM + email + social + SEO. |

## Differentiators

- **Approval-first** — every outbound action ends in an Approval Inbox before going out.
- **Brand-conditioned generation** — the BrandKit + KG insights are injected into every prompt; agents inherit the brand voice automatically.
- **MCP-first integrations** — 14 concrete adapters + BYO MCP marketplace; no bespoke per-integration code.
- **Self-hosted by default** — Docker Compose stack; the operator owns the Fernet master key and can swap LLM providers.
- **Auditable** — every admin action, agent run, and outbound publish is recorded in `audit_events`.

## Related

- [[Architecture]]
- [[Release Timeline]]
- [[Glossary]]
