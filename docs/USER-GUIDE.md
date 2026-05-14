# User Guide

How to use DClaw Marketing end-to-end. Covers the v0.1 demo flow:
**log in → set up brand → ingest context → generate content → approve → (mock) publish.**

> Want to skim? See the [3-minute demo walkthrough](#3-minute-demo-walkthrough) at the bottom.

---

## 1. First login

After `docker compose up -d`, navigate to **http://localhost:3015**. You'll be redirected to `/login`.

Default bootstrap credentials (configurable in `.env`):

```
Email:    admin@dclaw.io
Password: ChangeMeOnFirstLogin!
```

The platform forces a password reset on first login — you'll be sent to `/first-login`, set a new password (≥ 10 chars), and land on the dashboard.

> **The bootstrap admin is the only path in.** Self-service signup is disabled by design.

---

## 2. Create users (Admin only)

Click **Admin** in the nav → `/admin/users`. From here you can:

1. **Create user** — pick email + full name. Optionally promote to admin.
2. Copy the **one-shot temp password** that appears. Share it with the user out-of-band (Slack DM, email).
3. The user logs in, is forced to reset, and is good to go.
4. **Reset password** — re-issue a temp password for an existing user (e.g., if they forgot).
5. **Revoke** — soft-disable. They can no longer log in.

---

## 3. Create an Organization

In the v0.1 UI, Orgs are created via the API. To create one:

```bash
curl -X POST http://localhost:8102/api/v1/orgs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT" \
  -d '{"slug": "acme", "name": "Acme Inc"}'
```

(The creating user — must be a superuser — is auto-added as Org Admin.)

An in-UI org-creator page is on the v0.2 roadmap.

---

## 4. Set up your Brand Kit

Brand Kits live per-Org and are versioned (editing creates a new active revision; old versions are preserved).

```bash
curl -X POST http://localhost:8102/api/v1/orgs/$ORG_ID/brand-kits \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Brand v1",
    "palette": {"primary": "#7660A8", "secondary": "#9384BD"},
    "fonts": {"display": "Poppins", "body": "Poppins"},
    "voice": {
      "sliders": {"formal_casual": 0.6, "technical_witty": 0.4},
      "do_say": ["clear", "direct", "specific"],
      "dont_say": ["AI-magic", "revolutionary", "synergy"]
    },
    "positioning": {"tagline": "Marketing on autopilot"},
    "personas": [
      {
        "name": "B2B SaaS CMO",
        "fears": ["budget overrun", "team burnout"],
        "desires": ["pipeline growth", "calm execution"]
      }
    ]
  }'
```

The Creatives Agent reads from this kit when drafting copy.

---

## 5. Ingest context files

Anything you want the agent to know about — product brief, brand book, top-performing past posts, customer interview transcripts — should be ingested into the **Knowledge Graph**.

**Step 1 — upload the bytes** (presigned PUT to S3/MinIO):

```bash
# Get a presigned URL
curl -X POST http://localhost:8102/api/v1/assets/upload \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "'"$ORG_ID"'",
    "filename": "brief.md",
    "mime_type": "text/markdown",
    "kind": "document"
  }'
# → returns { asset: {id, ...}, presigned_put_url, expires_in }

# Upload the file
curl -X PUT "$PRESIGNED_URL" \
  -H "Content-Type: text/markdown" \
  --data-binary @brief.md

# Confirm the upload completed
curl -X POST http://localhost:8102/api/v1/assets/$ASSET_ID/confirm \
  -H "Authorization: Bearer $JWT"
```

**Step 2 — trigger ingestion** (fires a Celery task that parses → chunks → embeds):

```bash
curl -X POST http://localhost:8102/api/v1/ingest/files \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "'"$ORG_ID"'",
    "asset_id": "'"$ASSET_ID"'",
    "name": "Q2 launch brief"
  }'
# → returns { source_id, job_id, status: "queued" }
```

**Step 3 — watch progress**:

```bash
# Poll status
curl http://localhost:8102/api/v1/ingest/$SOURCE_ID \
  -H "Authorization: Bearer $JWT"

# OR live-stream via Server-Sent Events:
curl -N http://localhost:8102/api/v1/jobs/$JOB_ID/stream \
  -H "Authorization: Bearer $JWT"
```

**Supported formats** (v0.1): text/plain · text/markdown · text/csv · application/json · application/xml · application/yaml · application/pdf.

---

## 6. Generate content with the Creatives Agent

Now the fun part. From the UI: **Creatives** in the nav → `/agents/creatives`.

1. Pick an Org.
2. Pick a channel (LinkedIn / X / Instagram / Threads / Bluesky).
3. Set N variants (1–10).
4. Write your brief (≥ 4 chars):

   > *"Announce that our Q2 release ships agent-driven calendar scheduling. Lead with the customer outcome (less manual work, faster turnaround). Friendly but professional tone."*

5. Click **Generate variants**.

The Creatives Agent will:

1. Fetch your active Brand Kit
2. Retrieve the top 5 most relevant chunks from your Knowledge Graph (via pgvector cosine similarity)
3. Build a structured system prompt (voice sliders + do-say / don't-say + positioning)
4. Call Claude (or fall back to a deterministic stub if no `ANTHROPIC_API_KEY` is configured)
5. Parse out the variants
6. **Create a pending ApprovalRequest for each variant**

You'll see the variants listed. Click through to **Inbox** to act on them.

---

## 7. Approve / Reject in the Inbox

**Inbox** in the nav → `/inbox`.

Each card shows:

- **Action type** (`publish_social_post`) and **channel**
- **Agent attribution** (e.g., `creatives_agent_v1`)
- **Variant text** (what would be published)
- **Original brief** that prompted it
- **Status** badge

Decision UI:

- **Approve** — flips status to `approved`, writes an `AuditEvent` recording the decision + your user as approver. (In v0.2, this triggers the actual publish.)
- **Reject** — requires a reason; writes a rejection AuditEvent.

> **4-eye rule.** You can't approve your own requests. The Creatives Agent's requests aren't owned by anyone, so any admin/manager/reviewer can decide.

---

## 8. (Mock) Publish

In v0.1 the publish step is mocked — approving a `publish_social_post` ApprovalRequest sets its status to `approved` but doesn't actually call X/LinkedIn/IG. Phase 4 wires the real publisher adapters per channel.

---

## 9. Browse the audit log

Every decision (approve / reject) writes an `AuditEvent`. Browse via:

```bash
# Direct DB query in dev
docker compose exec postgres psql -U postgres -d dclaw_marketing \
  -c 'SELECT created_at, action_type, actor_user_id, target_id FROM audit_events ORDER BY created_at DESC LIMIT 20;'
```

An audit UI is on the v0.2 roadmap.

---

## 3-minute demo walkthrough

1. `docker compose up -d` (wait ~30s for healthchecks)
2. Open `http://localhost:3015` → log in as `admin@dclaw.io` / `ChangeMeOnFirstLogin!`
3. Set new password → land on dashboard
4. Create Org + Brand Kit via API (or use a seeded one — coming in v0.2)
5. Upload `brief.md` + ingest → KG populated
6. Click **Creatives** in nav → type a brief → **Generate variants**
7. Click **Inbox** → approve one variant with a reason like "great hook"
8. Show the AuditEvent rows in the DB — full traceability

The whole flow ships in v0.1 with no LLM API keys required (stubs make it deterministic). Add `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` to `.env` for real generation + embeddings.

---

## Troubleshooting

**Login fails immediately.** Check `docker compose logs backend` — first start needs ~10s for the bootstrap admin to seed. Retry.

**File upload returns 403.** You're not a member of the Org you're uploading to. Check `/api/v1/orgs` and your membership.

**Generation returns the same text every time.** You haven't set `ANTHROPIC_API_KEY` — the agent is using the deterministic stub. Add it to `.env` and `docker compose restart backend celery-worker`.

**KG search returns no results.** Either no chunks have embeddings (set `OPENAI_API_KEY` then re-ingest) or no chunks exist at all (run the file ingestion flow).

**Bootstrap admin password rejected.** You're typing the wrong default — copy/paste `ChangeMeOnFirstLogin!` exactly (including the exclamation mark). Or override via `BOOTSTRAP_ADMIN_TEMP_PASSWORD` in `.env`.

---

## End-to-end walkthrough (Sprint 4)

The Sprint 4 demo run is one continuous flow:

1. **Sign in** as the bootstrap admin → first-login password reset.
2. **Add a model provider** at `/admin/models` → pick **Anthropic**, paste your API key, **Test Connection**, save. Auto-discovery populates the Models table within a few seconds.
3. **Set a default model**: under any role agent (Conductor or Creatives) hit the Model Settings panel and pick the entry you just discovered for the `text` capability.
4. **Open `/conductor`** → drop a brief like _"Launch announcement for v1.1.2 on LinkedIn + X next Tuesday"_ → **Dispatch**. Decomposition plan appears, then each role-agent's output card.
5. **Approve hard-gated steps** in `/inbox` if the workflow templates' `approval` nodes paused. Hit Sign-off twice if `approvers_required=2`.
6. **Watch the trace** at `/api/v1/agents/runs/{request_id}/trace` for the chronological model-call trail (Logs / Metrics buttons on `/admin/models` use the same data).
7. **Run a Workflow template** at `/workflows/templates` → clone _Launch Announcement_ → edit → smoke-test → schedule.
8. **Check costs** at `/admin/costs` — every model call rolled up into per-agent / per-model totals.

This sequence exercises every Sprint-4 surface end-to-end.
