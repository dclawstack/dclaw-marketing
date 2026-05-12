"use client";

import { FormEvent, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import {
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkTextarea,
} from "@/components/dk";
import { createBrandKit } from "@/lib/api";

export default function NewBrandKitPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const orgId = params?.id ?? "";

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [primary, setPrimary] = useState("#7660A8");
  const [secondary, setSecondary] = useState("#9384BD");
  const [whatWeDo, setWhatWeDo] = useState("");
  const [whoWeServe, setWhoWeServe] = useState("");
  const [whyWeMatter, setWhyWeMatter] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const kit = await createBrandKit(orgId, {
        name,
        description: description || undefined,
        palette: { primary, secondary, ink: "#0F0F12" },
        fonts: { display: "Poppins", body: "Poppins" },
        positioning: {
          what_we_do: whatWeDo || undefined,
          who_we_serve: whoWeServe || undefined,
          why_we_matter: whyWeMatter || undefined,
        },
        voice: { formal_casual: 50, technical_witty: 50, calm_energetic: 50 },
      });
      router.push(`/orgs/${orgId}/brand/${kit.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          { label: "Org", href: `/orgs/${orgId}` },
          { label: "Brand Kits", href: `/orgs/${orgId}/brand` },
          { label: "New" },
        ]}
      />
      <DkPageHeader
        eyebrow="Theme Q1 · Setup"
        title="New Brand Kit"
        description="Start with the essentials — palette, name, positioning. You'll refine voice and add personas on the next screen."
      />

      <DkCard>
        <DkCardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-6 py-2">
            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="name" required>
                Brand kit name
              </DkLabel>
              <DkInput
                id="name"
                placeholder="Acme primary brand"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="desc">Description (optional)</DkLabel>
              <DkTextarea
                id="desc"
                rows={2}
                placeholder="One line about when to use this brand kit."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="primary">Primary color</DkLabel>
                <div className="flex items-center gap-2">
                  <input
                    id="primary"
                    type="color"
                    value={primary}
                    onChange={(e) => setPrimary(e.target.value)}
                    className="h-11 w-11 rounded-md border border-[var(--dk-border-strong)] cursor-pointer"
                  />
                  <DkInput
                    value={primary}
                    onChange={(e) => setPrimary(e.target.value)}
                    pattern="#[0-9A-Fa-f]{6}"
                    className="font-mono"
                  />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="secondary">Secondary color</DkLabel>
                <div className="flex items-center gap-2">
                  <input
                    id="secondary"
                    type="color"
                    value={secondary}
                    onChange={(e) => setSecondary(e.target.value)}
                    className="h-11 w-11 rounded-md border border-[var(--dk-border-strong)] cursor-pointer"
                  />
                  <DkInput
                    value={secondary}
                    onChange={(e) => setSecondary(e.target.value)}
                    pattern="#[0-9A-Fa-f]{6}"
                    className="font-mono"
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-4 rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] p-4">
              <h3 className="font-display text-base font-semibold text-ink">
                Positioning (optional)
              </h3>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="what">What we do</DkLabel>
                <DkInput
                  id="what"
                  placeholder="Designs and delivers …"
                  value={whatWeDo}
                  onChange={(e) => setWhatWeDo(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="who">Who we serve</DkLabel>
                <DkInput
                  id="who"
                  placeholder="Mid-market B2B SaaS marketing teams"
                  value={whoWeServe}
                  onChange={(e) => setWhoWeServe(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="why">Why we matter</DkLabel>
                <DkInput
                  id="why"
                  placeholder="From experimentation to production in weeks, not months"
                  value={whyWeMatter}
                  onChange={(e) => setWhyWeMatter(e.target.value)}
                />
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
              >
                {error}
              </div>
            )}

            <div className="flex items-center gap-2 pt-2 border-t border-[var(--dk-border)]">
              <Link href={`/orgs/${orgId}/brand`}>
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
                Create &amp; Configure
              </DkButton>
            </div>
          </form>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
