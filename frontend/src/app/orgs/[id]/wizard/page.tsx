"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowRight, Check, Loader2, Sparkles } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
  DkTextarea,
} from "@/components/dk";
import {
  getOrg,
  listBrandKits,
  listSocialAccounts,
  type Organization,
} from "@/lib/api";
import { getToken } from "@/lib/auth";

type StepStatus = "todo" | "done" | "skipped";

interface Step {
  id: string;
  label: string;
  blurb: string;
}

const STEPS: Step[] = [
  { id: "brand", label: "Brand", blurb: "Voice, do-say / don't-say, positioning." },
  { id: "social", label: "Social", blurb: "Connect at least one outbound channel." },
  { id: "persona", label: "Persona", blurb: "Who are you talking to?" },
  { id: "goals", label: "Goals", blurb: "What does success look like?" },
  { id: "project", label: "Project", blurb: "Create the first project." },
];

async function authFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      ...(init?.headers as Record<string, string> | undefined),
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
  });
  if (!res.ok) throw new Error(await res.text());
  if (res.status === 204) return undefined as T;
  return res.json();
}

export default function OrgSetupWizard() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const orgId = params.id;
  const [org, setOrg] = useState<Organization | null>(null);
  const [statuses, setStatuses] = useState<Record<string, StepStatus>>({});
  const [activeStep, setActiveStep] = useState<string>("brand");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Brand step state
  const [voiceTone, setVoiceTone] = useState("");
  const [doSay, setDoSay] = useState("");
  const [dontSay, setDontSay] = useState("");

  // Persona step state
  const [personaName, setPersonaName] = useState("");
  const [personaPain, setPersonaPain] = useState("");

  // Goals step state
  const [primaryGoal, setPrimaryGoal] = useState("brand_awareness");
  const [monthlyBudgetUsd, setMonthlyBudgetUsd] = useState(1000);

  // Project step state
  const [projectName, setProjectName] = useState("");
  const [projectSlug, setProjectSlug] = useState("");

  useEffect(() => {
    if (!orgId) return;
    getOrg(orgId).then(setOrg).catch(() => null);
    void detectExisting(orgId);
  }, [orgId]);

  async function detectExisting(id: string) {
    try {
      const [kits, accounts] = await Promise.all([
        listBrandKits(id).catch(() => []),
        listSocialAccounts(id).catch(() => []),
      ]);
      const next: Record<string, StepStatus> = {};
      if (kits.length > 0) next["brand"] = "done";
      if (accounts.length > 0) next["social"] = "done";
      setStatuses((s) => ({ ...s, ...next }));
    } catch {
      /* best effort */
    }
  }

  function markDone(id: string) {
    setStatuses((s) => ({ ...s, [id]: "done" }));
    const idx = STEPS.findIndex((s) => s.id === id);
    if (idx >= 0 && idx + 1 < STEPS.length) setActiveStep(STEPS[idx + 1].id);
  }

  function skip(id: string) {
    setStatuses((s) => ({ ...s, [id]: "skipped" }));
    const idx = STEPS.findIndex((s) => s.id === id);
    if (idx >= 0 && idx + 1 < STEPS.length) setActiveStep(STEPS[idx + 1].id);
  }

  async function saveBrand() {
    if (!orgId) return;
    setBusy(true);
    setError(null);
    try {
      await authFetch(`/api/v1/orgs/${orgId}/brand-kits`, {
        method: "POST",
        body: JSON.stringify({
          name: "Default brand kit",
          voice_json: {
            sliders: {},
            do_say: doSay
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
            dont_say: dontSay
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
            tone: voiceTone || undefined,
          },
          positioning_json: {},
          palette_json: {},
          fonts_json: {},
        }),
      });
      markDone("brand");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save brand.");
    } finally {
      setBusy(false);
    }
  }

  async function savePersona() {
    if (!orgId) return;
    if (!personaName.trim()) {
      skip("persona");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      // Personas attach to a BrandKit; we read the active kit then POST a persona row.
      const kits = await listBrandKits(orgId);
      const active = kits.find((k) => k.is_active) ?? kits[0];
      if (!active) throw new Error("Create a brand kit first.");
      await authFetch(
        `/api/v1/orgs/${orgId}/brand-kits/${active.id}/personas`,
        {
          method: "POST",
          body: JSON.stringify({
            name: personaName.trim(),
            description: personaPain.trim() || undefined,
          }),
        },
      );
      markDone("persona");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save persona.");
    } finally {
      setBusy(false);
    }
  }

  async function saveGoals() {
    if (!orgId) return;
    setBusy(true);
    setError(null);
    try {
      await authFetch(`/api/v1/orgs/${orgId}/goals`, {
        method: "PATCH",
        body: JSON.stringify({
          goals_json: { primary: primaryGoal },
          constraints_json: { monthly_budget_usd: monthlyBudgetUsd },
        }),
      });
      markDone("goals");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save goals.");
    } finally {
      setBusy(false);
    }
  }

  async function createProject() {
    if (!orgId || !projectName.trim() || !projectSlug.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await authFetch(`/api/v1/orgs/${orgId}/projects`, {
        method: "POST",
        body: JSON.stringify({
          name: projectName.trim(),
          slug: projectSlug.trim(),
          status: "active",
        }),
      });
      markDone("project");
      // Done — bounce to the Org detail
      router.push(`/orgs/${orgId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create project.");
    } finally {
      setBusy(false);
    }
  }

  const doneCount = useMemo(
    () => Object.values(statuses).filter((s) => s === "done").length,
    [statuses],
  );

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow={org ? `Workspace · ${org.name}` : "Workspace"}
        title="Project Setup Wizard"
        description="Five quick steps to take a new Org from empty to first-project-running. You can skip any step and come back later."
        actions={<DkBadge tone="brand">Q6 · onboarding</DkBadge>}
      />

      {error ? (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-5">
        {STEPS.map((s, i) => {
          const status = statuses[s.id];
          const active = activeStep === s.id;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => setActiveStep(s.id)}
              className={
                "flex flex-col items-start gap-1 p-3 rounded-md border text-left transition-colors " +
                (active
                  ? "border-brand bg-[var(--dk-purple-50)]"
                  : "border-[var(--dk-border)] hover:bg-[var(--dk-gray-50)]")
              }
            >
              <div className="flex items-center gap-2 text-xs text-[var(--dk-fg-2)]">
                <span>Step {i + 1}</span>
                {status === "done" ? (
                  <Check className="h-3 w-3 text-[var(--dk-success)]" />
                ) : status === "skipped" ? (
                  <span className="opacity-60">skipped</span>
                ) : null}
              </div>
              <div className="font-medium">{s.label}</div>
              <div className="text-xs opacity-70">{s.blurb}</div>
            </button>
          );
        })}
      </div>

      {activeStep === "brand" && (
        <DkCard>
          <DkCardHeader>
            <DkCardTitle>Brand voice</DkCardTitle>
            <DkCardDescription>
              Optional now — you can edit later under the Brand tab. Comma-separate the do-say / don&apos;t-say lists.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent className="flex flex-col gap-3">
            <div>
              <DkLabel>Tone</DkLabel>
              <DkInput
                placeholder="warm, expert, no jargon"
                value={voiceTone}
                onChange={(e) => setVoiceTone(e.target.value)}
              />
            </div>
            <div>
              <DkLabel>Do say (comma-separated)</DkLabel>
              <DkInput
                placeholder="customers, partners, build"
                value={doSay}
                onChange={(e) => setDoSay(e.target.value)}
              />
            </div>
            <div>
              <DkLabel>Don&apos;t say (comma-separated)</DkLabel>
              <DkInput
                placeholder="users, leverage, synergy"
                value={dontSay}
                onChange={(e) => setDontSay(e.target.value)}
              />
            </div>
            <div className="flex gap-2 pt-2">
              <DkButton onClick={saveBrand} disabled={busy}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Save brand kit
              </DkButton>
              <DkButton variant="ghost" onClick={() => skip("brand")}>
                Skip for now
              </DkButton>
            </div>
          </DkCardContent>
        </DkCard>
      )}

      {activeStep === "social" && (
        <DkCard>
          <DkCardHeader>
            <DkCardTitle>Connect a channel</DkCardTitle>
            <DkCardDescription>
              The Conductor needs at least one outbound channel to schedule anything. Connect on the /channels page, then come back.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent className="flex gap-2">
            <Link href="/channels">
              <DkButton>
                <ArrowRight className="h-4 w-4" /> Go to /channels
              </DkButton>
            </Link>
            <DkButton variant="ghost" onClick={() => markDone("social")}>
              I&apos;ve connected one
            </DkButton>
            <DkButton variant="ghost" onClick={() => skip("social")}>
              Skip for now
            </DkButton>
          </DkCardContent>
        </DkCard>
      )}

      {activeStep === "persona" && (
        <DkCard>
          <DkCardHeader>
            <DkCardTitle>Define your persona (optional)</DkCardTitle>
            <DkCardDescription>
              Helps the Creatives Agent target voice + tone. Skippable.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent className="flex flex-col gap-3">
            <div>
              <DkLabel>Name</DkLabel>
              <DkInput
                placeholder="e.g. Marketing manager at a 50-person SaaS"
                value={personaName}
                onChange={(e) => setPersonaName(e.target.value)}
              />
            </div>
            <div>
              <DkLabel>Top pain point</DkLabel>
              <DkTextarea
                rows={3}
                placeholder="What's the biggest problem this persona is trying to solve?"
                value={personaPain}
                onChange={(e) => setPersonaPain(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <DkButton onClick={savePersona} disabled={busy}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save persona
              </DkButton>
              <DkButton variant="ghost" onClick={() => skip("persona")}>
                Skip
              </DkButton>
            </div>
          </DkCardContent>
        </DkCard>
      )}

      {activeStep === "goals" && (
        <DkCard>
          <DkCardHeader>
            <DkCardTitle>Goals + budget</DkCardTitle>
            <DkCardDescription>
              Sets <code>goals_json</code> + <code>constraints_json.monthly_budget_usd</code> on the Org. The autonomy posture has sensible defaults you can tune later under Goals.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent className="grid gap-3 md:grid-cols-2">
            <div>
              <DkLabel>Primary goal</DkLabel>
              <DkSelect
                value={primaryGoal}
                onChange={(e) => setPrimaryGoal(e.target.value)}
              >
                <option value="brand_awareness">Brand awareness</option>
                <option value="lead_gen">Lead generation</option>
                <option value="conversion">Conversion</option>
                <option value="retention">Retention</option>
              </DkSelect>
            </div>
            <div>
              <DkLabel>Monthly budget (USD)</DkLabel>
              <DkInput
                type="number"
                min={0}
                value={monthlyBudgetUsd}
                onChange={(e) => setMonthlyBudgetUsd(Number(e.target.value || 0))}
              />
            </div>
            <div className="md:col-span-2 flex gap-2 pt-2">
              <DkButton onClick={saveGoals} disabled={busy}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save goals
              </DkButton>
              <DkButton variant="ghost" onClick={() => skip("goals")}>
                Skip
              </DkButton>
            </div>
          </DkCardContent>
        </DkCard>
      )}

      {activeStep === "project" && (
        <DkCard>
          <DkCardHeader>
            <DkCardTitle>Create your first project</DkCardTitle>
            <DkCardDescription>
              Projects scope content + analytics under a name. You can rename or archive later.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent className="grid gap-3 md:grid-cols-2">
            <div>
              <DkLabel>Project name</DkLabel>
              <DkInput
                placeholder="Q3 Launch"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
              />
            </div>
            <div>
              <DkLabel>Slug</DkLabel>
              <DkInput
                placeholder="q3-launch"
                value={projectSlug}
                onChange={(e) => setProjectSlug(e.target.value)}
              />
            </div>
            <div className="md:col-span-2 flex gap-2 pt-2">
              <DkButton
                onClick={createProject}
                disabled={busy || !projectName.trim() || !projectSlug.trim()}
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Create project &amp; finish
              </DkButton>
              <DkButton variant="ghost" onClick={() => skip("project")}>
                Skip
              </DkButton>
            </div>
          </DkCardContent>
        </DkCard>
      )}

      <div className="text-sm opacity-60 text-center">
        {doneCount} of {STEPS.length} steps complete
      </div>
    </div>
  );
}
