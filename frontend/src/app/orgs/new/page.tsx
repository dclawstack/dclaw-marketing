"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

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
import { createOrg } from "@/lib/api";
import { useOrg } from "@/contexts/org-context";


export default function NewOrgPage() {
  const router = useRouter();
  const { refresh, setCurrentOrg } = useOrg();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isExternal, setIsExternal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const org = await createOrg({
        name,
        description: description || undefined,
        is_external: isExternal,
      });
      await refresh();
      setCurrentOrg(org);
      router.push(`/orgs/${org.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          { label: "New" },
        ]}
      />
      <DkPageHeader
        eyebrow="Workspace"
        title="New Organization"
        description="Set up a new workspace. Slug is auto-generated server-side as o-{first4(name)}-{random6hex} and is permanent."
      />

      <DkCard>
        <DkCardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-5 py-2">
            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="name" required>
                Organization name
              </DkLabel>
              <DkInput
                id="name"
                placeholder="Acme Inc"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={submitting}
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="description">Description (optional)</DkLabel>
              <DkTextarea
                id="description"
                rows={3}
                placeholder="What's this organization for?"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={submitting}
              />
            </div>

            <label className="flex items-start gap-2.5 cursor-pointer pt-1">
              <DkCheckbox
                checked={isExternal}
                onChange={(e) => setIsExternal(e.target.checked)}
              />
              <div className="flex flex-col">
                <span className="text-sm font-medium text-ink">
                  External / client organization
                </span>
                <span className="text-xs text-[var(--dk-fg-2)]">
                  Unlocks the Client Portal flow once it ships (v0.2+). Leave unchecked for in-house orgs.
                </span>
              </div>
            </label>

            {error && (
              <div
                role="alert"
                className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
              >
                {error}
              </div>
            )}

            <div className="flex items-center gap-2 pt-2">
              <Link href="/orgs">
                <DkButton variant="secondary" type="button">
                  Cancel
                </DkButton>
              </Link>
              <DkButton
                type="submit"
                loading={submitting}
                disabled={submitting || !name}
                withArrow={!submitting}
              >
                Create Organization
              </DkButton>
            </div>
          </form>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
