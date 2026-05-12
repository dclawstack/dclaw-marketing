# DClaw Marketing — Pending Work (post-stretch snapshot)
**Snapshot:** 2026-05-13
**Main HEAD at snapshot:** post-#206 (Knowledge Console UI) — #207–#210 in CI
**Stretch shipped:** PRs #194–#210 (19 PRs in the autonomous 8-hour window)
**Sprint:** Sprint 2 closed at #193 (v1.2.0-rc1). This file = Sprint 3 backlog.

---

## What's still genuinely pending

### Truly deferred (called out in CHANGELOG `Deferred past 1.2`)
- [ ] React-flow visual editors (sequence / workflow / segment) — plain forms cover v1
- [ ] Markov-chain attribution
- [ ] Helm chart rebuild
- [ ] True PDF for client reports (HTML browser-printable works today)
- [ ] Snapchat / Telegram publishers (low priority)

### Phase 1 UI gaps not addressed in this stretch
- [ ] Tabbed `/orgs/[id]` detail UI (Overview / Members / Brand / Knowledge / Goals / Projects unified)
- [ ] Member-invite-by-email UI (invite token, accept page, role chooser)
- [ ] Per-Org `autonomy_posture_json` settings panel
- [ ] v1 routers (`/campaigns`, `/leads`, `/analytics`, `/dashboard`) made Org-scoped — currently global with a `TEMPORARY` comment on `/api/v1/dashboard`

### Phase 10 J–P gaps
- [ ] Client onboarding wizard (guided multi-step form)
- [ ] Per-Org retainer + monthly budget caps
- [ ] Kanban + Gantt project view
- [ ] Time-tracker timer widget (TimeEntry CRUD exists; no UI start/stop timer)
- [ ] Stripe invoice management UI (model exists; admin UI sparse)

### Phase 2 / Q2 polish
- [ ] Knowledge Console exists but doesn't yet show extracted-chunks drill-down per source
- [ ] No git-repo ingestion worker (URL works via #205, file works, git + zip still stub)

### Tech debt called out in §2
- [ ] Pydantic v2 `ConfigDict` migration — several models / pydantic schemas still use `class Config:` (warning at import; not broken)
- [ ] Async/sync session boundary cleanup — `webhooks_email` already fixed (#168), other webhook handlers may still have warnings

---

## Pending against PLAN-v1.2 themes (not in the stretch backlog above)

### Theme B — Content Generation polish
- [ ] **B4 Repurposing Engine** — given one approved asset, derive channel-shaped variants (LinkedIn post → X thread → IG carousel → blog snippet). Backend `RepurposeJob`; frontend `/library/[asset]/repurpose` multi-select preview.
- [ ] **B5 Variant A/B Studio** — `VariantSet(campaign_id, slot, hypothesis)` + `Variant(set_id, asset_id, weight, status)`; scheduler honors weights; `/campaigns/[id]/ab` gallery with real-time win-rate + auto-promote-winner toggle.
- [ ] **B6 Hook & Headline Lab** — paste a draft, get 30 hooks ranked by historical CTR of similar hooks in this Org's content. Lightweight delight feature.

### Theme D — MCP gaps
- [ ] **D3 BYO MCP marketplace** — paste an MCP server URL + auth; runtime introspects tools; `/integrations/byo` form with tool inspector + per-tool allow/deny.

### Theme E — Lead enrichment gap
- [ ] **E2 Lead enrichment fan-out** — on Lead creation, call Apollo / Clearbit / PDL via MCP and merge findings. `app/services/enrichment.py` with provider chain + idempotency on (org_id, email). Visitor-identity resolution (#169) is done; this is the *external* provider chain.

### Theme F — Analytics depth
- [ ] **F1 Dashboard drill-down** — basic `/analytics` page exists; per-campaign drill-down + brand-themed recharts surface still pending.
- [ ] **F2 Content Performance Heatmap** — hooks vs CTR, post-times vs engagement, persona vs conversion. Surfaces "what's working".

### Theme G — Agent surfaces
- [ ] **G1 Marketing-Agent chat dock** — full-screen `/agent` exists; docked side-panel `<AgentChat>` available on every page is the missing UX piece.

### Theme H — Sites / SEO long-form (depth beyond #195)
- [ ] **H1 Landing-Page Builder** — `Page(org_id, slug, sections_json, status, published_url)` + `PageVariant`; brand-locked builder UI; publish to Org subdomain or push to Webflow/WordPress/Ghost via MCP.
- [ ] **H2 SEO Blog Pipeline (full)** — keyword research → topic-cluster planner → outline → draft → editorial review → publish to CMS. #195 ships audit + internal-link + ranking-delta; the keyword→outline→draft chain is the missing half.

### Theme Q — Onboarding gap
- [ ] **Q6 Project Setup Wizard** (issue #30) — guided onboarding: brand assets → social accounts → persona → goals. Backend supports all; wizard UX missing.

### v2.0 themes J–P — Agency polish (beyond gaps already listed)
- [ ] **M Embeddable read-only dashboard URLs** — share-with-client signed URLs into a white-label `/share/<token>` analytics view (separate from logged-in `/client/*`).
- [ ] **N Playbook search UI + editor** — `Playbook` model exists; `/playbooks` listing exists; KG-embedded retrieval (semantic search across playbooks) + Markdown editor with `{{variables}}` and agent-callable invocation still pending.
- [ ] **O Client Portal — white-label polish** — basic `/client/*` portal exists (#188); per-Org logo / favicon / domain mapping + branding overrides still pending.

### Appendix A.11 — Future auth (long-term, no v1.2 commitment)
- [ ] **A.11.3 Magic-link email auth (admin-issued)** — admin clicks "send magic link to user@…"; user clicks the link, lands on a one-time-token consume route, gets a session.
- [ ] **A.11.6 2FA / TOTP** — opt-in per user; enrollment QR + recovery codes; rate-limited TOTP verify on login.

### Plan P2 deferrals (explicit in PLAN-v1.2, listed for visibility)
- [ ] C5 SMS / WhatsApp (Twilio + WhatsApp Cloud API)
- [ ] C6 Push & In-App (OneSignal / Customer.io / Knock)
- [ ] F3 Competitor Tracker (weekly snapshots + LLM diff narrative)
- [ ] F4 Customer-Voice Mining (reviews / tickets / social mentions → theme clusters)
- [ ] G2 Inbox Agent (DM replies)
- [ ] G3 Trend Radar (daily 5 ranked content opportunities)
- [ ] G4 Comment Sentiment & Triage
- [ ] G5 Auto-Optimizer (bandit over Variant Sets)
- [ ] H3 Topic Cluster Map (visual react-flow graph)
- [ ] B7 Brand-Safe Image Editor

---

