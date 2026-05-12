"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Save, Trash2 } from "lucide-react";

import {
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

type StepKind = "email" | "wait" | "branch" | "linkedin_dm" | "webhook";

interface Step {
  kind: StepKind;
  delay_seconds?: number;
  template_id?: string;
  note?: string;
}

const KIND_LABEL: Record<StepKind, string> = {
  email: "Email",
  wait: "Wait",
  branch: "Branch",
  linkedin_dm: "LinkedIn DM",
  webhook: "Webhook",
};

export default function NewSequencePage() {
  const router = useRouter();
  const { currentOrg } = useOrg();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<Step[]>([{ kind: "email" }]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function add() {
    setSteps((s) => [...s, { kind: "wait", delay_seconds: 86400 }]);
  }
  function remove(i: number) {
    setSteps((s) => s.filter((_, idx) => idx !== i));
  }
  function update(i: number, patch: Partial<Step>) {
    setSteps((s) => s.map((st, idx) => (idx === i ? { ...st, ...patch } : st)));
  }

  async function submit() {
    if (!currentOrg) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/v1/orgs/${currentOrg.id}/sequences`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getToken()}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name,
            description: description || null,
            status: "draft",
            steps: steps.map((s, idx) => ({
              position: idx + 1,
              kind: s.kind,
              delay_seconds: s.delay_seconds ?? null,
              template_id: s.template_id ?? null,
              config_json: s.note ? { note: s.note } : null,
            })),
          }),
        },
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
      }
      router.push("/email/sequences");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save sequence.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 7 — Sequences"
        title="New sequence"
        description="Linear multi-step automation. Each step is an email, a wait, a branch (condition on Lead.score / stage), a LinkedIn DM, or a webhook. The runner from #178 walks the steps in order, advancing every 5 minutes."
        actions={
          <DkButton onClick={submit} disabled={saving || !name} loading={saving}>
            <Save className="h-4 w-4" />
            Save sequence
          </DkButton>
        }
      />

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Identification</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-3">
          <div>
            <DkLabel htmlFor="name" required>Name</DkLabel>
            <DkInput
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Cold-outreach drip"
            />
          </div>
          <div>
            <DkLabel htmlFor="desc">Description</DkLabel>
            <DkInput
              id="desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="4-step nurture for newly-imported MQLs"
            />
          </div>
        </DkCardContent>
      </DkCard>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Steps</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-3">
          {steps.map((s, i) => (
            <div
              key={i}
              className="rounded-md border border-[var(--dk-border)] p-3 flex flex-col gap-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="rounded-pill bg-[var(--dk-purple-50)] px-2 py-0.5 text-xs font-mono text-brand">
                    {i + 1}
                  </span>
                  <select
                    value={s.kind}
                    onChange={(e) =>
                      update(i, { kind: e.target.value as StepKind })
                    }
                    className="rounded-md border border-[var(--dk-border-strong)] px-2 py-1 text-sm"
                  >
                    {(Object.keys(KIND_LABEL) as StepKind[]).map((k) => (
                      <option key={k} value={k}>
                        {KIND_LABEL[k]}
                      </option>
                    ))}
                  </select>
                </div>
                <DkButton
                  size="sm"
                  variant="ghost"
                  onClick={() => remove(i)}
                  aria-label="Remove step"
                >
                  <Trash2 className="h-4 w-4" />
                </DkButton>
              </div>
              {s.kind === "wait" && (
                <div>
                  <DkLabel>Delay (seconds)</DkLabel>
                  <DkInput
                    type="number"
                    value={s.delay_seconds ?? 0}
                    onChange={(e) =>
                      update(i, { delay_seconds: Number(e.target.value) })
                    }
                  />
                </div>
              )}
              {s.kind === "email" && (
                <div>
                  <DkLabel>Email template id (optional)</DkLabel>
                  <DkInput
                    value={s.template_id ?? ""}
                    onChange={(e) =>
                      update(i, { template_id: e.target.value })
                    }
                    placeholder="UUID of an EmailTemplate row"
                  />
                </div>
              )}
              {(s.kind === "branch" ||
                s.kind === "linkedin_dm" ||
                s.kind === "webhook") && (
                <div>
                  <DkLabel>Note (free-form)</DkLabel>
                  <DkInput
                    value={s.note ?? ""}
                    onChange={(e) => update(i, { note: e.target.value })}
                    placeholder="Configured in JSON later"
                  />
                </div>
              )}
            </div>
          ))}
          <DkButton size="sm" variant="secondary" onClick={add}>
            <Plus className="h-4 w-4" />
            Add step
          </DkButton>
          {error && (
            <p className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]">
              {error}
            </p>
          )}
        </DkCardContent>
      </DkCard>
    </div>
  );
}
