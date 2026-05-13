# Glossary

| Term | Meaning |
|------|---------|
| **BrandKit** | Versioned per-org brand identity: palette, fonts, voice, personas. Injected into every agent prompt. |
| **BrandKitInsight** | KG write-back artefact: short atomic brand observations learned from prior runs and re-injected into the Creatives Agent system prompt. |
| **Bootstrap superadmin** | The single hardcoded account `admin@dclaw.io` with slug `s-admn-000000`. Re-asserted on every backend startup; cannot be deleted; recovery only via operator-held Fernet master key. |
| **Conductor** | Multi-agent orchestration agent that coordinates role-agents (Creatives, SEO, Analyst, etc.). |
| **Cost-cap evaluator** | Pre-action check that refuses an agent run if it would exceed the per-org budget. Supports warn / blocked states. |
| **Fernet master key** | Operator-held symmetric key encrypting SocialAccount tokens (and other secrets) at rest. Out-of-band. |
| **KG** | Knowledge Graph — semantic-search-indexed corpus of ingested documents, scoped by org. |
| **MCP** | Model Context Protocol — unified per-integration adapter spec. 14 concrete adapters + BYO marketplace. |
| **OrganizationMembership.role** | One of `admin` / `manager` / `viewer` (per-org); superadmin is a separate, bootstrap-only state. |
| **PLAN-v1.2** | The roadmap document (`PLAN-v1.2.md`). The version line was renamed in Sprint 3 to align release tags with this name. |
| **QuotaCounter** | Sliding-window quota enforcement with a circuit-breaker; protects against runaway agent runs. |
| **Slug** | Human-readable identifier — users `u-{first4}-{6hex}`, orgs `o-{first4}-{6hex}`, bootstrap `s-admn-000000`. |
| **Station** | The supervised UI a human operator runs DClaw from. Approval Inbox lives here. |
| **SP3-N** | Numbered sub-themes of Sprint 3's polish lane (SP3-1 … SP3-24). |
| **Two-tier admin model** | Sprint 3 introduction: a single bootstrap superadmin + per-org admins, with centralized guards, last-admin protection, audit + notifications. |

## Related

- [[Architecture]]
- [[Project Overview]]
