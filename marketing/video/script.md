# Demo Video Script — DClaw Marketing v0.1.0

**Target length:** ~3 minutes
**Tone:** confident, direct, no hype
**Voiceover style:** founder-explaining-the-product, not announcer
**Brand colors on screen:** DClaw purple `#7660A8`, light background

---

## Scene 1 — Hook (0:00–0:15)

**Visual:** Black title card → fades to DClaw Marketing logo → text appears: "The agent-driven marketing operating system."

**Voiceover:**
> "Marketing teams of five spend forty percent of their week on mechanical work. We replaced that. DClaw Marketing is the platform where AI agents *do* the marketing — and you supervise."

---

## Scene 2 — The setup (0:15–0:45)

**Visual:** Screen recording at 1× speed, no cuts:
1. `docker compose up -d` in terminal
2. Cut to browser → http://localhost:3015 → login screen
3. Type admin credentials → land on `/first-login` → set new password
4. Cursor moves to "Admin" in the nav → click → `/admin/users`
5. Click "Create user" → fill email + name → "Generate temp password"
6. Temp password appears in dialog with copy-to-clipboard button

**Voiceover:**
> "First-time setup. You bring up the stack. Log in as admin. Reset the bootstrap password. Then create users — admin only, no self-signup. Every new user gets a one-shot temp password and is forced to change it on first login. Full audit trail throughout."

---

## Scene 3 — Brand & context (0:45–1:30)

**Visual:** Switch to terminal, show the curl command for creating a Brand Kit. Highlight the JSON:
- palette (primary `#7660A8` etc.)
- voice sliders
- do-say / don't-say lists
- one Persona

Then switch back to browser → /agents/creatives. Show the Org selector now populated.

Then back to terminal, show:
1. `POST /assets/upload` → returns presigned URL
2. `curl PUT $URL` with a sample `brief.md`
3. `POST /assets/$id/confirm` → status: ready
4. `POST /ingest/files` → job queued
5. Brief poll → status: ready, chunks: 8

**Voiceover:**
> "Set your brand once. Palette, fonts, voice tone, do-say and don't-say lists, personas. Versioned — every edit creates a new revision.
>
> Upload your context. Briefs, past content, customer interviews. The platform parses the bytes, chunks the text, and embeds everything into a per-organization Knowledge Graph using pgvector. Files become searchable memory the agents pull from."

---

## Scene 4 — The agent run (1:30–2:15)

**Visual:** Browser, fullscreen on `/agents/creatives`:
1. Org pre-selected
2. Channel: LinkedIn
3. N variants: 3
4. Type the brief in the textarea (slowly enough to read):
   > "Announce our Q2 release: agent-driven calendar scheduling. Lead with the customer outcome — less manual work, faster turnaround. Friendly but professional."
5. Click "Generate variants"
6. Brief spinner (~2s) → results card appears with 3 variants
7. Scroll through each variant

**Voiceover:**
> "Now the loop. You give the Creatives Agent a brief. It fetches your active brand kit. It runs a semantic search against your knowledge graph for the top five most relevant chunks. It builds a structured prompt with your voice rules, your positioning, the retrieved context, and the brief itself. Then it calls Claude.
>
> Three variants back. In your voice. Grounded in your context. Never invented from nothing.
>
> But — and this is the important part — the agent does not publish."

---

## Scene 5 — The Inbox (2:15–2:45)

**Visual:**
1. Click "Inbox" in nav → `/inbox`
2. Three pending approval cards visible
3. Each card shows: action_type (`publish_social_post`), channel (`linkedin`), agent attribution (`creatives_agent_v1`), the variant text, the original brief
4. Click into the reason input, type "great hook"
5. Click "Approve" → card flips to status: approved
6. Show that you can also reject with a reason

**Voiceover:**
> "Every variant lands here — the Approval Inbox. Pending until you decide. Approve with a comment. Reject with a reason that the agent can learn from later. Every decision writes an immutable audit event with your identity, timestamp, IP, and the agent that prepared the request.
>
> Four-eye rule enforced: you can't approve your own requests. Hard-gate by default on every outbound action."

---

## Scene 6 — The vision (2:45–3:00)

**Visual:** Cut to architecture diagram from the README → fade through:
1. The roadmap table from the slides
2. The capability matrix
3. The YC inspiration row
4. End on the title: "DClaw Marketing — the agent-driven marketing operating system."

**Voiceover:**
> "Today: one agent. The Creatives Agent.
>
> Next month: the full crew. Social Media Manager scheduling and publishing. SEO Specialist running blog pipelines. Paid Media Specialist managing ad spend. Analyst writing your Monday-morning narrative. All coordinated by a Conductor agent.
>
> Marketing as supervision, not labor.
>
> github.com slash dclawstack slash dclaw-marketing. Built with Claude Code."

**End card:** Repo URL + "Built with Claude Code" + DClaw logo.

---

## Recording notes

- **Recommended capture tool:** macOS QuickTime or Loom at 1920×1200 (so the browser zoom can be 90%)
- **Browser:** Chrome with the only tab; bookmark bar hidden
- **Resolution:** export 1080p mp4, H.264, 6 Mbps
- **Audio:** record VO separately (Audacity / Garage Band) then sync to video — easier than live; lets you re-take individual lines
- **Cursor highlight:** enable macOS "Pointer enlarge" + "Pointer locator" for visibility
- **Pre-recording prep:**
  - Seed DB with: one admin user, one org "Acme Inc" (slug `acme`), one Brand Kit, 2-3 ingested files (so the KG isn't empty)
  - Clear browser history of the localhost:3015 domain to look fresh
  - Have the brief text ready in a paste buffer
  - Have the bootstrap password copied

---

## Stretch — generate it programmatically

A Playwright script that drives the full demo and captures it to mp4 is in `scripts/record-demo.ts` (coming in a follow-up PR). Pair with an AI voiceover from ElevenLabs or Cartesia using this script as input text.
