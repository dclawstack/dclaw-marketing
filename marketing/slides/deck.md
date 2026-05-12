---
marp: true
theme: default
paginate: true
backgroundColor: "#F8F8FA"
color: "#0F0F12"
style: |
  section { font-family: 'Poppins', sans-serif; padding: 56px 64px; }
  h1 { color: #7660A8; font-weight: 800; letter-spacing: -0.02em; }
  h2 { color: #7660A8; font-weight: 700; }
  strong { color: #4A3878; }
  code { background: #F1EEF8; color: #4A3878; padding: 2px 6px; border-radius: 4px; }
  blockquote { border-left: 4px solid #7660A8; padding-left: 16px; color: #404049; }
  table th { background: #F1EEF8; color: #4A3878; }
  .accent { color: #7660A8; }
---

# DClaw Marketing

## The agent-driven marketing operating system

> You set the brand once. The agents do the work. You supervise.

v0.1.0 · May 2026

---

## The problem

Marketing teams of five spend **40%** of their week on mechanical work:
- Drafting variants
- Scheduling posts
- Monitoring inboxes
- Writing weekly reports

Solo founders skip marketing entirely — no bandwidth.

Existing tools (Hootsuite, Buffer, Jasper, HubSpot) ship features for humans to **operate**.

**None of them ship a crew that does the work for you.**

---

## What we built

A small fleet of AI agents — backed by Claude + your brand voice + your context — that **do** marketing.

You spend 15 minutes/day in the **Approval Inbox**.

The agents do the rest.

---

## How it works — one-time setup

1. **Brand Kit** — palette, fonts, voice sliders (formal↔casual, technical↔witty), do-say / don't-say
2. **Personas** — your target customer (CMO at a B2B SaaS, mid-market RevOps, …)
3. **Knowledge Graph** — upload briefs, past content, customer interviews, brand books. Everything embedded into 1536-dim vectors via pgvector for fast retrieval.
4. **Goals + Constraints** — business objectives, brand-safety lines, monthly budgets, **autonomy posture** per action class.

That's it. Once. Then you're done with setup.

---

## How it works — the daily loop

```
You: "Announce our Q2 release on LinkedIn."
                        │
                        ▼
              Creatives Agent
                        │
        ┌───────────────┼──────────────┐
        ▼               ▼              ▼
   Brand Kit      KG retrieval    Voice rules
   (active)       (top-5 chunks)  (do/don't)
                        │
                        ▼
              Claude (Sonnet)
                        │
                        ▼
         3 variants → Approval Inbox
                        │
                        ▼
            You: ✓ Approve / ✗ Reject
                        │
                        ▼
              (v0.2) Real publish
```

---

## What's different

| Existing tools | DClaw Marketing |
|---|---|
| You operate the tool | The agents operate; you supervise |
| Templates | Generation from your voice + context |
| Bolt-on AI feature | AI is the whole product |
| One channel per dashboard | One supervision surface across every channel |
| Trust by hope | 4-eye approvals + full audit trail |

---

## Hard-gate by default

> **Agents never publish without your explicit consent.**

Every outbound action passes through the Approval Inbox.

- **Autopilot**: internal drafts, research, KG updates
- **Soft gate**: customer-facing low-risk (auto-approve after timeout)
- **Hard gate** *(default for posting)*: human must explicitly approve

Per-Org + per-Project + per-channel overrides. The platform never surprises you.

---

## Architecture at a glance

```
Browser  →  Next.js 14  →  FastAPI  ↔  Postgres + pgvector
                              ↓
                          Redis (queue)
                              ↓
                          Celery workers
                              ↓
                    ┌─────────┼──────────┐
                    ▼         ▼          ▼
                Anthropic   OpenAI    MinIO/S3
                (Claude)  (embeddings)
```

Ships as a **Helm chart** to any Kubernetes cluster. Customer brings the cluster; we ship the chart + images.

---

## What's in v0.1.0

- 10-role supervision model · Org/Project hierarchy · admin-only user creation
- **Versioned Brand Kits** · per-Org Knowledge Graph (pgvector)
- **Creatives Agent** — LinkedIn / X / Instagram / Threads / Bluesky
- **Approval Inbox** with 4-eye rule + audit log
- Background workers + SSE progress streams
- S3-compatible object storage with presigned uploads
- ~100 backend tests · CI/CD via GitHub Actions · Helm chart scaffolded

---

## The Y Combinator pattern map

We folded patterns from 16 YC marketing/AI companies:

**Copy.ai** templates · **Letterdrop** sales→social · **Persana** ICP scoring · **Junia** SEO blogs · **Mutiny** personalised pages · **Sutro** prompt→page · **Outset** customer research · **Magic Loops / Wordware** visual workflows · **Lindy / Embra** workspace agents · **Decagon / Sierra** customer-facing agents · **Cluely** real-time AI overlay · **Default** RevOps automation · **Crayon / Klue** competitive intel · **Mintlify** AI docs · **Cresta** real-time coaching.

We don't ship 16 features. We ship the **shape** these companies converged on.

---

## Roadmap

| | Theme |
|---|---|
| **v0.2** | Conductor agent · SMM / SEO / Paid Media / Analyst agents · real social adapters · Helm chart polish |
| **v1.0** | Client Operations · Project Mgmt · Time Tracking & Billing · Client Reporting · Knowledge Base & SOPs · Client Portal · Visual Workflow Builder |
| **v2.0** | Multi-agency SaaS · External client portals · MCP integration marketplace |

---

## Try it

```bash
git clone https://github.com/dclawstack/dclaw-marketing
cd dclaw-marketing
docker compose up -d
open http://localhost:3015
```

Works offline. No API keys required — agents fall back to deterministic stubs. Add `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` for real generation + embeddings.

---

# Thank you.

**Repo:** github.com/dclawstack/dclaw-marketing
**Plan:** PLAN-v1.2.md
**Docs:** docs/USER-GUIDE.md · docs/ARCHITECTURE.md

Built with **Claude Code** by **@deepro713**.
