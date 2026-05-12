"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Check, Palette, Plus, Sparkles } from "lucide-react";

import {
  DkBadge,
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkEmptyState,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import {
  BrandKit,
  Organization,
  activateBrandKit,
  getOrg,
  listBrandKits,
} from "@/lib/api";

export default function BrandKitsPage() {
  const params = useParams<{ id: string }>();
  const orgId = params?.id ?? "";

  const [org, setOrg] = useState<Organization | null>(null);
  const [kits, setKits] = useState<BrandKit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const [o, k] = await Promise.all([getOrg(orgId), listBrandKits(orgId)]);
      setOrg(o);
      setKits(k);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function activate(kitId: string) {
    setActivating(kitId);
    try {
      await activateBrandKit(orgId, kitId);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Activate failed.");
    } finally {
      setActivating(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          {
            label: org?.name ?? "…",
            href: orgId ? `/orgs/${orgId}` : "/orgs",
          },
          { label: "Brand Kits" },
        ]}
      />

      <DkPageHeader
        eyebrow="Organization · Theme Q1"
        title="Brand Kits"
        description="Each Brand Kit captures palette, type, voice, positioning, and personas. Versioned — editing creates a new revision; only the active version is read by agents."
        actions={
          <Link href={`/orgs/${orgId}/brand/new`}>
            <DkButton>
              <Plus className="h-4 w-4" />
              New Brand Kit
            </DkButton>
          </Link>
        }
      />

      {error && (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <DkSkeleton key={i} className="h-48" />
          ))}
        </div>
      ) : kits.length === 0 ? (
        <DkEmptyState
          icon={<Palette className="h-6 w-6" />}
          title="No brand kit yet"
          description="A Brand Kit is the agent's design brain — palette + type + voice + positioning + personas. Set yours up once; agents pull from it every run."
          actions={
            <Link href={`/orgs/${orgId}/brand/new`}>
              <DkButton withArrow>Set Up Your Brand</DkButton>
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {kits.map((k) => {
            const palette = k.palette_json ?? {};
            const swatches = [
              palette.primary,
              palette.secondary,
              palette.ink,
              palette.surface,
              palette.surface_muted,
            ].filter(Boolean) as string[];
            return (
              <DkCard key={k.id} hover className="h-full flex flex-col">
                <DkCardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <DkCardTitle className="text-base">
                      {k.name}
                    </DkCardTitle>
                    {k.is_active ? (
                      <DkBadge tone="success">
                        <Check className="h-3 w-3" />
                        active
                      </DkBadge>
                    ) : (
                      <DkBadge tone="neutral">v{k.version}</DkBadge>
                    )}
                  </div>
                  {k.description && (
                    <p className="text-sm text-[var(--dk-fg-2)] leading-normal">
                      {k.description}
                    </p>
                  )}
                </DkCardHeader>
                <DkCardContent className="flex-1 flex flex-col gap-3">
                  {swatches.length > 0 && (
                    <div className="flex items-center gap-1">
                      {swatches.map((c, i) => (
                        <div
                          key={`${c}-${i}`}
                          className="h-6 w-6 rounded-md border border-[var(--dk-border)]"
                          style={{ background: c }}
                          title={c}
                        />
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-xs text-[var(--dk-fg-2)]">
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>{k.personas.length} personas</span>
                  </div>
                </DkCardContent>
                <div className="px-6 pb-6 flex items-center gap-2">
                  <Link
                    href={`/orgs/${orgId}/brand/${k.id}`}
                    className="flex-1"
                  >
                    <DkButton
                      variant="secondary"
                      size="sm"
                      className="w-full"
                    >
                      Edit
                    </DkButton>
                  </Link>
                  {!k.is_active && (
                    <DkButton
                      size="sm"
                      onClick={() => activate(k.id)}
                      loading={activating === k.id}
                    >
                      Set Active
                    </DkButton>
                  )}
                </div>
              </DkCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
