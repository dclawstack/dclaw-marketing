"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Check } from "lucide-react";

import {
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkCheckbox,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkTextarea,
} from "@/components/dk";
import { Organization, createProject, getOrg } from "@/lib/api";
import { cn } from "@/lib/utils";

const CHANNELS = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "x", label: "X / Twitter" },
  { value: "instagram", label: "Instagram" },
  { value: "threads", label: "Threads" },
  { value: "bluesky", label: "Bluesky" },
  { value: "facebook", label: "Facebook" },
  { value: "youtube", label: "YouTube" },
  { value: "tiktok", label: "TikTok" },
  { value: "newsletter", label: "Newsletter" },
  { value: "blog", label: "Blog / SEO" },
];

function slugify(s: string): string {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

type Step = 1 | 2 | 3;

export default function NewProjectPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const orgId = params?.id ?? "";

  const [org, setOrg] = useState<Organization | null>(null);
  const [step, setStep] = useState<Step>(1);

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugDirty, setSlugDirty] = useState(false);
  const [description, setDescription] = useState("");

  const [objective, setObjective] = useState("");
  const [channels, setChannels] = useState<string[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orgId) return;
    void getOrg(orgId).then(setOrg).catch(() => {});
  }, [orgId]);

  function onNameChange(v: string) {
    setName(v);
    if (!slugDirty) setSlug(slugify(v));
  }

  function toggleChannel(c: string) {
    setChannels((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c],
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (step !== 3) return;
    setError(null);
    setSubmitting(true);
    try {
      const project = await createProject(orgId, {
        slug,
        name,
        description: description || undefined,
        goals_json: {
          objective: objective || undefined,
          channels,
        },
      });
      router.push(`/orgs/${orgId}/projects`);
      // (Once the project detail page exists, redirect there instead.)
      void project;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const canAdvance =
    (step === 1 && name && slug) ||
    (step === 2 && objective.length > 0) ||
    step === 3;

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          {
            label: org?.name ?? "…",
            href: orgId ? `/orgs/${orgId}` : "/orgs",
          },
          { label: "Projects", href: `/orgs/${orgId}/projects` },
          { label: "New" },
        ]}
      />
      <DkPageHeader
        eyebrow="Project · Setup"
        title="New Project"
        description="A three-step wizard that captures what this project is, what it aims to achieve, and which channels it operates on."
      />

      <Stepper step={step} />

      <DkCard>
        <DkCardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-5 py-2">
            {step === 1 && (
              <>
                <h3 className="font-display text-lg font-semibold text-ink">
                  1. Basics
                </h3>
                <div className="flex flex-col gap-1.5">
                  <DkLabel htmlFor="name" required>
                    Project name
                  </DkLabel>
                  <DkInput
                    id="name"
                    placeholder="Q2 Launch"
                    value={name}
                    onChange={(e) => onNameChange(e.target.value)}
                    required
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <DkLabel
                    htmlFor="slug"
                    required
                    description="URL-safe identifier. Permanent once created."
                  >
                    Slug
                  </DkLabel>
                  <DkInput
                    id="slug"
                    placeholder="q2-launch"
                    value={slug}
                    onChange={(e) => {
                      setSlug(slugify(e.target.value));
                      setSlugDirty(true);
                    }}
                    pattern="[a-z0-9-]+"
                    required
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <DkLabel htmlFor="description">
                    Description (optional)
                  </DkLabel>
                  <DkTextarea
                    id="description"
                    rows={3}
                    placeholder="One-line summary of what this project does."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <h3 className="font-display text-lg font-semibold text-ink">
                  2. Objective
                </h3>
                <div className="flex flex-col gap-1.5">
                  <DkLabel
                    htmlFor="objective"
                    required
                    description="What does success look like? The Conductor uses this to decompose the brief."
                  >
                    Primary objective
                  </DkLabel>
                  <DkTextarea
                    id="objective"
                    rows={4}
                    placeholder="Announce the new agent calendar feature on LinkedIn + X over 3 weeks; drive demo signups."
                    value={objective}
                    onChange={(e) => setObjective(e.target.value)}
                    required
                  />
                </div>
              </>
            )}

            {step === 3 && (
              <>
                <h3 className="font-display text-lg font-semibold text-ink">
                  3. Channels
                </h3>
                <p className="text-sm text-[var(--dk-fg-1)]">
                  Which channels does this project operate on? Pick at least one — you can add more later.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {CHANNELS.map((c) => {
                    const checked = channels.includes(c.value);
                    return (
                      <label
                        key={c.value}
                        className={cn(
                          "flex items-center gap-3 rounded-md border px-3 py-2.5 cursor-pointer transition-colors duration-fast",
                          checked
                            ? "border-brand bg-[var(--dk-purple-50)]"
                            : "border-[var(--dk-border-strong)] hover:border-brand",
                        )}
                      >
                        <DkCheckbox
                          checked={checked}
                          onChange={() => toggleChannel(c.value)}
                        />
                        <span className="text-sm font-medium text-ink flex-1">
                          {c.label}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </>
            )}

            {error && (
              <div
                role="alert"
                className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
              >
                {error}
              </div>
            )}

            <div className="flex items-center justify-between gap-2 pt-2 border-t border-[var(--dk-border)]">
              {step === 1 ? (
                <Link href={`/orgs/${orgId}/projects`}>
                  <DkButton variant="secondary" type="button">
                    Cancel
                  </DkButton>
                </Link>
              ) : (
                <DkButton
                  variant="secondary"
                  type="button"
                  onClick={() => setStep((s) => (s - 1) as Step)}
                >
                  Back
                </DkButton>
              )}

              {step < 3 ? (
                <DkButton
                  type="button"
                  onClick={() => setStep((s) => (s + 1) as Step)}
                  disabled={!canAdvance}
                  withArrow
                >
                  Continue
                </DkButton>
              ) : (
                <DkButton
                  type="submit"
                  loading={submitting}
                  disabled={submitting || !name || !slug || channels.length === 0}
                >
                  Create Project
                </DkButton>
              )}
            </div>
          </form>
        </DkCardContent>
      </DkCard>
    </div>
  );
}

function Stepper({ step }: { step: Step }) {
  const labels = ["Basics", "Objective", "Channels"];
  return (
    <ol className="flex items-center gap-3 text-sm">
      {labels.map((l, i) => {
        const idx = (i + 1) as Step;
        const active = step === idx;
        const done = step > idx;
        return (
          <li key={l} className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-pill text-xs font-semibold transition-colors duration-fast",
                done
                  ? "bg-brand text-white"
                  : active
                  ? "bg-[var(--dk-purple-100)] text-brand"
                  : "bg-[var(--dk-gray-100)] text-[var(--dk-fg-2)]",
              )}
            >
              {done ? <Check className="h-3.5 w-3.5" /> : idx}
            </span>
            <span
              className={cn(
                "font-medium",
                active || done ? "text-ink" : "text-[var(--dk-fg-2)]",
              )}
            >
              {l}
            </span>
            {i < labels.length - 1 && (
              <span
                aria-hidden
                className={cn(
                  "h-px w-8 transition-colors duration-fast",
                  done ? "bg-brand" : "bg-[var(--dk-border)]",
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
