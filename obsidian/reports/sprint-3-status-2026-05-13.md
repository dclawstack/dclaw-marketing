# DClaw Marketing — Sprint 3 status (autonomous stretch close-out)
**Snapshot:** 2026-05-13
**Main HEAD:** post-v0.2.0 + 24 follow-on PRs in flight
**Sprint 3 close:** this file marks the end of the autonomous v0.2.x stretch.

---

## ✅ Cleared in the Sprint 3 stretch (PRs #213 → #236)

### Phase 1 UI gaps
- [x] Tabbed `/orgs/[id]` detail UI — SP3-2
- [x] Member-invite-by-email UI — SP3-3 (#229)
- [x] Per-Org autonomy posture settings panel — SP3-4
- [x] v1 routers Org-scoped — SP3-1 (#213)

### Phase 10 J–P gaps
- [x] Per-Org retainer + monthly budget caps — SP3-22 (#227)
- [x] Kanban project view — SP3-20 (#233)
- [x] Time-tracker timer widget — SP3-21
- [x] Stripe invoice management UI — SP3-23 (#228)

### Phase 2 / Q2 polish
- [x] Knowledge Console per-source chunk drill-down — SP3-7
- [x] Git-repo ingestion worker — SP3-8 (#232)

### Tech debt
- [x] Pydantic v2 ConfigDict migration — SP3-24 (#231)
- [x] Fernet-encrypted SocialAccount tokens — SP3-6 (#230)

### Theme B — Content
- [x] B4 Repurposing Engine — SP3-11
- [x] B5 Variant A/B Studio — SP3-10
- [x] B6 Hook & Headline Lab — SP3-9

### Theme D — MCP
- [x] D3 BYO MCP marketplace — SP3-15

### Theme E — Leads
- [x] E2 Lead enrichment fan-out — SP3-12

### Theme F — Analytics
- [x] F1 Dashboard drill-down (endpoint) — #236
- [x] F2 Content Performance Heatmap — SP3-13

### Theme G — Agents
- [x] G1 Docked agent chat sidebar — SP3-14

### Theme H — Sites / SEO
- [x] H1 Landing-Page Builder (minimal) — SP3-16 (#234)
- [x] H2 SEO Blog Pipeline (deterministic stub) — SP3-17 (#235)

### Theme Q — Onboarding
- [x] Q6 Project Setup Wizard — SP3-5

### v2.0 Themes J–P
- [x] M Embeddable read-only dashboard URLs — SP3-19
- [x] N Playbook search + editor — SP3-18 (#226)
- [x] O Client Portal white-label polish — #236

### Appendix A.11 — Future auth
- [x] A.11.3 Magic-link admin-issued — #236
- [x] A.11.6 2FA / TOTP (stdlib RFC-6238) — #236

---

## 🔵 Explicit P2 deferrals — scoped for v0.4

These remain pending because each requires a paid external service or a heavy
visual-editor library (react-flow). Tracked for visibility, not committable work
for this stretch.

### Truly deferred (CHANGELOG `Deferred past 1.2`)
- React-flow visual editors (sequence / workflow / segment)
- Markov-chain attribution
- Helm chart rebuild
- True PDF for client reports (HTML browser-printable works today)
- Snapchat / Telegram publishers

### Plan P2 deferrals (explicit in PLAN-v1.2)
- C5 SMS / WhatsApp (Twilio + WhatsApp Cloud API)
- C6 Push & In-App (OneSignal / Customer.io / Knock)
- F3 Competitor Tracker
- F4 Customer-Voice Mining
- G2 Inbox Agent (DM replies)
- G3 Trend Radar
- G4 Comment Sentiment & Triage
- G5 Auto-Optimizer (bandit over Variant Sets)
- H3 Topic Cluster Map (visual react-flow graph)
- B7 Brand-Safe Image Editor

### Optional polish
- F1 dashboard drill-down — frontend recharts UI (backend endpoint shipped)
- Marketing collaterals (#52, #53) — explicitly excluded from this stretch

---

**Status:** Every actionable v0.3 line item in the original snapshot is shipped or
in flight. Remaining items are external-integration-blocked P2 work scoped for v0.4.
