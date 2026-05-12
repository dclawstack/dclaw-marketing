"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Check, Plus, Save, Sparkles, X } from "lucide-react";

import {
  DkBadge,
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkChip,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSkeleton,
  DkSlider,
  DkTextarea,
} from "@/components/dk";
import {
  BrandKit,
  activateBrandKit,
  getBrandKit,
  updateBrandKit,
} from "@/lib/api";

const VOICE_SLIDERS = [
  { key: "formal_casual", left: "Formal", right: "Casual" },
  { key: "technical_witty", left: "Technical", right: "Witty" },
  { key: "calm_energetic", left: "Calm", right: "Energetic" },
] as const;

export default function BrandKitEditorPage() {
  const params = useParams<{ id: string; kitId: string }>();
  const orgId = params?.id ?? "";
  const kitId = params?.kitId ?? "";

  const [kit, setKit] = useState<BrandKit | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Editable state mirrors kit fields
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [primary, setPrimary] = useState("#7660A8");
  const [secondary, setSecondary] = useState("#9384BD");
  const [ink, setInk] = useState("#0F0F12");
  const [voice, setVoice] = useState<Record<string, number>>({
    formal_casual: 50,
    technical_witty: 50,
    calm_energetic: 50,
  });
  const [doSay, setDoSay] = useState<string[]>([]);
  const [doSayDraft, setDoSayDraft] = useState("");
  const [dontSay, setDontSay] = useState<string[]>([]);
  const [dontSayDraft, setDontSayDraft] = useState("");
  const [whatWeDo, setWhatWeDo] = useState("");
  const [whoWeServe, setWhoWeServe] = useState("");
  const [whyWeMatter, setWhyWeMatter] = useState("");

  const refresh = useCallback(async () => {
    if (!orgId || !kitId) return;
    setLoading(true);
    setError(null);
    try {
      const k = await getBrandKit(orgId, kitId);
      setKit(k);
      setName(k.name);
      setDescription(k.description ?? "");
      setPrimary(k.palette_json?.primary ?? "#7660A8");
      setSecondary(k.palette_json?.secondary ?? "#9384BD");
      setInk(k.palette_json?.ink ?? "#0F0F12");
      const v = k.voice_json ?? {};
      setVoice({
        formal_casual: v.formal_casual ?? 50,
        technical_witty: v.technical_witty ?? 50,
        calm_energetic: v.calm_energetic ?? 50,
      });
      setDoSay(v.do_say ?? []);
      setDontSay(v.dont_say ?? []);
      const p = k.positioning_json ?? {};
      setWhatWeDo(p.what_we_do ?? "");
      setWhoWeServe(p.who_we_serve ?? "");
      setWhyWeMatter(p.why_we_matter ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [orgId, kitId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await updateBrandKit(orgId, kitId, {
        name,
        description: description || undefined,
        palette: { primary, secondary, ink },
        voice: {
          ...voice,
          do_say: doSay,
          dont_say: dontSay,
        },
        positioning: {
          what_we_do: whatWeDo || undefined,
          who_we_serve: whoWeServe || undefined,
          why_we_matter: whyWeMatter || undefined,
        },
      });
      await refresh();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  async function handleActivate() {
    setActivating(true);
    try {
      await activateBrandKit(orgId, kitId);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Activate failed.");
    } finally {
      setActivating(false);
    }
  }

  function addDoSay() {
    const v = doSayDraft.trim();
    if (v && !doSay.includes(v)) setDoSay([...doSay, v]);
    setDoSayDraft("");
  }
  function addDontSay() {
    const v = dontSayDraft.trim();
    if (v && !dontSay.includes(v)) setDontSay([...dontSay, v]);
    setDontSayDraft("");
  }

  if (loading || !kit) {
    return (
      <div className="flex flex-col gap-4">
        <DkSkeleton className="h-8 w-64" />
        <DkSkeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          { label: "Org", href: `/orgs/${orgId}` },
          { label: "Brand Kits", href: `/orgs/${orgId}/brand` },
          { label: kit.name },
        ]}
      />

      <DkPageHeader
        eyebrow={`Brand Kit · v${kit.version}`}
        title={kit.name}
        description="Edit palette, voice, positioning, and do-say / don't-say lists. Saving creates a new revision; the previous version stays available in history."
        actions={
          <div className="flex items-center gap-3">
            {kit.is_active ? (
              <DkBadge tone="success">
                <Check className="h-3 w-3" />
                active
              </DkBadge>
            ) : (
              <DkButton
                variant="secondary"
                onClick={handleActivate}
                loading={activating}
              >
                Set Active
              </DkButton>
            )}
            <DkButton onClick={handleSave} loading={saving}>
              <Save className="h-4 w-4" />
              Save
            </DkButton>
          </div>
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
      {saved && (
        <div
          role="status"
          className="rounded-md border border-[var(--dk-success)] bg-[var(--dk-success-bg)] px-3 py-2 text-sm text-[var(--dk-success)]"
        >
          Saved.
        </div>
      )}

      {/* Basics */}
      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Basics</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="grid gap-4 md:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <DkLabel htmlFor="name">Name</DkLabel>
            <DkInput
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <DkLabel htmlFor="desc">Description</DkLabel>
            <DkInput
              id="desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </DkCardContent>
      </DkCard>

      {/* Palette */}
      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Palette</DkCardTitle>
          <DkCardDescription>
            Primary is used for CTAs and brand accents; secondary for soft
            backgrounds and decorative; ink is the body / headline color.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="grid gap-4 md:grid-cols-3">
          {[
            { label: "Primary", v: primary, set: setPrimary },
            { label: "Secondary", v: secondary, set: setSecondary },
            { label: "Ink", v: ink, set: setInk },
          ].map((c) => (
            <div key={c.label} className="flex flex-col gap-1.5">
              <DkLabel>{c.label}</DkLabel>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={c.v}
                  onChange={(e) => c.set(e.target.value)}
                  className="h-11 w-11 rounded-md border border-[var(--dk-border-strong)] cursor-pointer"
                />
                <DkInput
                  value={c.v}
                  onChange={(e) => c.set(e.target.value)}
                  pattern="#[0-9A-Fa-f]{6}"
                  className="font-mono"
                />
              </div>
            </div>
          ))}
        </DkCardContent>
      </DkCard>

      {/* Voice */}
      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Voice</DkCardTitle>
          <DkCardDescription>
            Where on each spectrum does this brand sit? Agents use these
            sliders to colour their generation.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-5">
          {VOICE_SLIDERS.map((s) => (
            <div key={s.key} className="flex flex-col gap-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-ink">{s.left}</span>
                <span className="font-medium text-ink">{s.right}</span>
              </div>
              <DkSlider
                min={0}
                max={100}
                value={voice[s.key]}
                onChange={(e) =>
                  setVoice({ ...voice, [s.key]: Number(e.target.value) })
                }
                showValue
              />
            </div>
          ))}
        </DkCardContent>
      </DkCard>

      {/* Do say / Don't say */}
      <div className="grid gap-4 md:grid-cols-2">
        <DkCard>
          <DkCardHeader>
            <DkCardTitle className="text-base">Do Say</DkCardTitle>
            <DkCardDescription>
              Phrases / words the agents should lean toward.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent className="flex flex-col gap-3">
            <div className="flex gap-2">
              <DkInput
                placeholder="e.g. enterprise-grade"
                value={doSayDraft}
                onChange={(e) => setDoSayDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addDoSay();
                  }
                }}
                className="flex-1"
              />
              <DkButton variant="secondary" onClick={addDoSay}>
                <Plus className="h-4 w-4" />
              </DkButton>
            </div>
            <div className="flex flex-wrap gap-2">
              {doSay.length === 0 && (
                <p className="text-sm text-[var(--dk-fg-2)]">Nothing yet.</p>
              )}
              {doSay.map((s) => (
                <DkChip key={s} tone="success" className="pr-1.5">
                  {s}
                  <button
                    type="button"
                    onClick={() => setDoSay(doSay.filter((x) => x !== s))}
                    aria-label={`Remove ${s}`}
                    className="ml-1 rounded-pill p-0.5 hover:bg-[var(--dk-success-bg)]"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </DkChip>
              ))}
            </div>
          </DkCardContent>
        </DkCard>

        <DkCard>
          <DkCardHeader>
            <DkCardTitle className="text-base">Don&apos;t Say</DkCardTitle>
            <DkCardDescription>
              Phrases / words to avoid — runs as a post-gen lint pass.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent className="flex flex-col gap-3">
            <div className="flex gap-2">
              <DkInput
                placeholder="e.g. supercharge"
                value={dontSayDraft}
                onChange={(e) => setDontSayDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addDontSay();
                  }
                }}
                className="flex-1"
              />
              <DkButton variant="secondary" onClick={addDontSay}>
                <Plus className="h-4 w-4" />
              </DkButton>
            </div>
            <div className="flex flex-wrap gap-2">
              {dontSay.length === 0 && (
                <p className="text-sm text-[var(--dk-fg-2)]">Nothing yet.</p>
              )}
              {dontSay.map((s) => (
                <DkChip key={s} tone="danger" className="pr-1.5">
                  {s}
                  <button
                    type="button"
                    onClick={() => setDontSay(dontSay.filter((x) => x !== s))}
                    aria-label={`Remove ${s}`}
                    className="ml-1 rounded-pill p-0.5 hover:bg-[var(--dk-danger-bg)]"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </DkChip>
              ))}
            </div>
          </DkCardContent>
        </DkCard>
      </div>

      {/* Positioning */}
      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Positioning</DkCardTitle>
          <DkCardDescription>
            What we do, who we serve, why we matter. The Conductor reads these
            to anchor every brief.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <DkLabel htmlFor="what">What we do</DkLabel>
            <DkTextarea
              id="what"
              rows={2}
              value={whatWeDo}
              onChange={(e) => setWhatWeDo(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <DkLabel htmlFor="who">Who we serve</DkLabel>
            <DkTextarea
              id="who"
              rows={2}
              value={whoWeServe}
              onChange={(e) => setWhoWeServe(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <DkLabel htmlFor="why">Why we matter</DkLabel>
            <DkTextarea
              id="why"
              rows={2}
              value={whyWeMatter}
              onChange={(e) => setWhyWeMatter(e.target.value)}
            />
          </div>
        </DkCardContent>
      </DkCard>

      {/* Personas (read-only for now) */}
      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Personas</DkCardTitle>
          <DkCardDescription>
            {kit.personas.length} persona{kit.personas.length === 1 ? "" : "s"}.
            Persona editing lands in a follow-up.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-3">
          {kit.personas.length === 0 ? (
            <p className="text-sm text-[var(--dk-fg-2)]">
              No personas yet. Use the API or add a persona via the JSON
              editor (coming soon).
            </p>
          ) : (
            kit.personas.map((p) => (
              <div
                key={p.id}
                className="rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] p-3"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="h-4 w-4 text-brand" />
                  <span className="font-semibold text-ink">{p.name}</span>
                </div>
                {p.description && (
                  <p className="text-sm text-[var(--dk-fg-1)] leading-relaxed">
                    {p.description}
                  </p>
                )}
              </div>
            ))
          )}
        </DkCardContent>
      </DkCard>

      <div className="flex items-center justify-end gap-2 pt-2">
        <Link href={`/orgs/${orgId}/brand`}>
          <DkButton variant="secondary">Back to brand kits</DkButton>
        </Link>
        <DkButton onClick={handleSave} loading={saving}>
          <Save className="h-4 w-4" />
          Save Changes
        </DkButton>
      </div>
    </div>
  );
}
