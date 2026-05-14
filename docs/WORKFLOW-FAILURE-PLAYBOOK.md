# Workflow Failure Playbook (S4-D5)

Operator-facing runbook for when a Workflow run fails mid-execution.

## Diagnose

1. Open `/workflows/runs` — the failing run is at the top.
2. Click the run → the step table shows which node tripped.
3. The `error_message` column is the raw exception. The most common ones:

| Symptom                                  | Likely cause                                | Action |
|------------------------------------------|----------------------------------------------|--------|
| `WorkflowDeferredError` on `approval`    | Approval still pending                       | Decide it in `/inbox`; runner resumes automatically. |
| `MCPInvocationError: 401`                | Connection token expired                      | Reconnect under `/integrations`. |
| `model_provider unhealthy`               | Provider key bad / quota                      | Check `/admin/models`; the right column shows the last error. |
| `dont_say` rejected after refine pass    | Content keeps hitting brand-banned phrases   | Tighten / loosen `BrandKit.do_not_say_terms`. |
| `quota exceeded`                          | Soft- or hard-cap tripped                    | `/admin/quotas` to raise the cap; rerun. |
| `pydantic.ValidationError` on tool_call  | DSL `arguments_template` produced bad shape  | Edit the workflow node; rerun smoke. |

## Rerun

- **Resume a paused run**: approve or reject the approval; the beat task
  picks it up within 30 s. To force-resume, hit
  `POST /api/v1/workflows/runs/{id}/resume`.
- **Restart from scratch**: `POST /api/v1/workflows/{id}/run` with the
  same input.
- **Smoke test before retry**: hit
  `POST /api/v1/workflows/{id}/smoke` — sandbox mode dry-runs every node
  (LLM stubs, tool_calls skipped, approvals auto-approved) and surfaces
  any obvious DSL bugs.

## Escalate

If two consecutive runs fail on the same node:

1. Move the workflow's status to `paused` via PATCH `/workflows/{id}`.
2. Capture a sample of the failing `run.context_snapshot` from the DB.
3. Page the workflow author in `#dclaw-eng` with the context dump and
   the run id.

## Health checks

`/admin/health` aggregates per-subsystem status. Green on Postgres /
Redis / MinIO + at least one healthy model provider is a precondition
for any workflow execution.
