"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { ImageIcon, Sparkles, Type } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkEmptyState,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
  DkTabs,
  DkTabsContent,
  DkTabsList,
  DkTabsTrigger,
  DkTextarea,
} from "@/components/dk";
import {
  AspectRatio,
  GenerateImagesResultItem,
  GenerateResultItem,
  Organization,
  generateCreativeImages,
  generateCreatives,
  listOrgs,
} from "@/lib/api";

/**
 * Creatives Agent runner — copy variants OR image variants, both gated
 * through the Approval Inbox.
 */
export default function CreativesStationPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgId, setOrgId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Copy state
  const [brief, setBrief] = useState("");
  const [channel, setChannel] = useState("linkedin");
  const [nVariants, setNVariants] = useState(3);
  const [generatingCopy, setGeneratingCopy] = useState(false);
  const [copyResults, setCopyResults] = useState<GenerateResultItem[]>([]);

  // Image state
  const [prompt, setPrompt] = useState("");
  const [aspect, setAspect] = useState<AspectRatio>("1:1");
  const [nImages, setNImages] = useState(3);
  const [generatingImages, setGeneratingImages] = useState(false);
  const [imageResults, setImageResults] = useState<GenerateImagesResultItem[]>(
    [],
  );

  useEffect(() => {
    void (async () => {
      try {
        const list = await listOrgs();
        setOrgs(list);
        if (list.length > 0 && !orgId) setOrgId(list[0].id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load orgs.");
      }
    })();
  }, []);

  async function onGenerateCopy() {
    if (!orgId) return;
    setGeneratingCopy(true);
    setError(null);
    setCopyResults([]);
    try {
      const response = await generateCreatives({
        organization_id: orgId,
        brief,
        n_variants: nVariants,
        channel,
      });
      setCopyResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setGeneratingCopy(false);
    }
  }

  async function onGenerateImages() {
    if (!orgId) return;
    setGeneratingImages(true);
    setError(null);
    setImageResults([]);
    try {
      const response = await generateCreativeImages({
        organization_id: orgId,
        prompt,
        n: nImages,
        aspect_ratio: aspect,
      });
      setImageResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setGeneratingImages(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Agent · Creatives"
        title="Creatives Station"
        description="Hand the Creatives Agent a brief or a visual prompt — it pulls your active brand kit and drafts variants. Outputs land in the Approval Inbox; the agent never publishes on its own."
      />

      {orgs.length === 0 ? (
        <DkEmptyState
          icon={<Sparkles className="h-6 w-6" />}
          title="No organizations yet"
          description="Ask an admin to create one — or sign in as a superuser to create one yourself."
        />
      ) : (
        <>
          <div className="flex flex-col gap-1.5 max-w-md">
            <DkLabel htmlFor="org">Organization</DkLabel>
            <DkSelect
              id="org"
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
            >
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name} ({o.slug})
                </option>
              ))}
            </DkSelect>
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
            >
              {error}
            </div>
          )}

          <DkTabs defaultValue="copy">
            <DkTabsList>
              <DkTabsTrigger value="copy">
                <Type className="h-4 w-4" />
                Copy
              </DkTabsTrigger>
              <DkTabsTrigger value="images">
                <ImageIcon className="h-4 w-4" />
                Images
              </DkTabsTrigger>
            </DkTabsList>

            <DkTabsContent value="copy">
              <DkCard>
                <DkCardHeader>
                  <DkCardTitle>Generate Post Copy</DkCardTitle>
                  <DkCardDescription>
                    Pulls active brand kit + retrieves context from the
                    Knowledge Graph, drafts {nVariants} variants. All queued
                    in the{" "}
                    <Link href="/inbox" className="font-medium text-brand hover:underline">
                      Inbox
                    </Link>
                    .
                  </DkCardDescription>
                </DkCardHeader>
                <DkCardContent className="flex flex-col gap-4">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="flex flex-col gap-1.5">
                      <DkLabel htmlFor="channel">Channel</DkLabel>
                      <DkSelect
                        id="channel"
                        value={channel}
                        onChange={(e) => setChannel(e.target.value)}
                      >
                        <option value="linkedin">LinkedIn</option>
                        <option value="x">X / Twitter</option>
                        <option value="instagram">Instagram</option>
                        <option value="threads">Threads</option>
                        <option value="bluesky">Bluesky</option>
                      </DkSelect>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <DkLabel htmlFor="n">Number of variants</DkLabel>
                      <DkInput
                        id="n"
                        type="number"
                        min={1}
                        max={10}
                        value={nVariants}
                        onChange={(e) =>
                          setNVariants(Number(e.target.value) || 3)
                        }
                      />
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <DkLabel
                      htmlFor="brief"
                      description="One paragraph. The clearer the intent, the better the variants."
                    >
                      Brief
                    </DkLabel>
                    <DkTextarea
                      id="brief"
                      rows={5}
                      placeholder="Announce the Q2 release — lead with the customer outcome, friendly but professional…"
                      value={brief}
                      onChange={(e) => setBrief(e.target.value)}
                    />
                  </div>

                  <DkButton
                    onClick={() => void onGenerateCopy()}
                    disabled={!orgId || brief.length < 4 || generatingCopy}
                    loading={generatingCopy}
                    withArrow={!generatingCopy}
                  >
                    {generatingCopy ? "Generating" : "Generate Variants"}
                  </DkButton>
                </DkCardContent>
              </DkCard>

              {copyResults.length > 0 && (
                <DkCard className="mt-4">
                  <DkCardHeader>
                    <DkCardTitle>Copy Variants</DkCardTitle>
                    <DkCardDescription>
                      All {copyResults.length} queued in the{" "}
                      <Link href="/inbox" className="font-medium text-brand hover:underline">
                        Approval Inbox
                      </Link>
                      .
                    </DkCardDescription>
                  </DkCardHeader>
                  <DkCardContent className="flex flex-col gap-3">
                    {copyResults.map((r, i) => (
                      <div
                        key={r.approval_request_id}
                        className="rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] p-4"
                      >
                        <div className="mb-2 flex items-center gap-2">
                          <DkBadge tone="brand">Variant {i + 1}</DkBadge>
                          <span className="text-xs text-[var(--dk-fg-2)] font-mono">
                            approval #{r.approval_request_id.slice(0, 8)}
                          </span>
                        </div>
                        <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--dk-fg-1)]">
                          {r.variant}
                        </p>
                      </div>
                    ))}
                  </DkCardContent>
                </DkCard>
              )}
            </DkTabsContent>

            <DkTabsContent value="images">
              <DkCard>
                <DkCardHeader>
                  <DkCardTitle>Generate Image Drafts</DkCardTitle>
                  <DkCardDescription>
                    Renders via Replicate when{" "}
                    <code className="font-mono text-xs">
                      REPLICATE_API_TOKEN
                    </code>{" "}
                    is set, otherwise a deterministic SVG stub. Every output
                    is queued for approval.
                  </DkCardDescription>
                </DkCardHeader>
                <DkCardContent className="flex flex-col gap-4">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="flex flex-col gap-1.5">
                      <DkLabel htmlFor="aspect">Aspect ratio</DkLabel>
                      <DkSelect
                        id="aspect"
                        value={aspect}
                        onChange={(e) =>
                          setAspect(e.target.value as AspectRatio)
                        }
                      >
                        <option value="1:1">1:1 — square</option>
                        <option value="16:9">16:9 — landscape</option>
                        <option value="9:16">9:16 — story / reel</option>
                        <option value="4:5">4:5 — portrait</option>
                      </DkSelect>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <DkLabel htmlFor="ni">Number of images</DkLabel>
                      <DkInput
                        id="ni"
                        type="number"
                        min={1}
                        max={8}
                        value={nImages}
                        onChange={(e) =>
                          setNImages(Number(e.target.value) || 3)
                        }
                      />
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <DkLabel
                      htmlFor="prompt"
                      description="Describe the visual. Brand-aware retrieval lands in a follow-up PR."
                    >
                      Image prompt
                    </DkLabel>
                    <DkTextarea
                      id="prompt"
                      rows={4}
                      placeholder="A flat, modern illustration of a purple-shouldered claw cradling a glowing data crystal, warm light, soft shadows."
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                    />
                  </div>

                  <DkButton
                    onClick={() => void onGenerateImages()}
                    disabled={!orgId || prompt.length < 4 || generatingImages}
                    loading={generatingImages}
                    withArrow={!generatingImages}
                  >
                    {generatingImages ? "Generating" : "Generate Images"}
                  </DkButton>
                </DkCardContent>
              </DkCard>

              {imageResults.length > 0 && (
                <DkCard className="mt-4">
                  <DkCardHeader>
                    <DkCardTitle>Image Drafts</DkCardTitle>
                    <DkCardDescription>
                      All {imageResults.length} queued in the{" "}
                      <Link href="/inbox" className="font-medium text-brand hover:underline">
                        Approval Inbox
                      </Link>
                      .
                    </DkCardDescription>
                  </DkCardHeader>
                  <DkCardContent>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {imageResults.map((r, i) => (
                        <ImageCard key={r.approval_request_id} item={r} index={i} />
                      ))}
                    </div>
                  </DkCardContent>
                </DkCard>
              )}
            </DkTabsContent>
          </DkTabs>
        </>
      )}
    </div>
  );
}

function ImageCard({
  item,
  index,
}: {
  item: GenerateImagesResultItem;
  index: number;
}) {
  const isData = item.url.startsWith("data:");
  return (
    <div className="rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] overflow-hidden">
      <div className="aspect-square bg-white">
        {isData ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.url}
            alt={`Generated variant ${index + 1}`}
            className="h-full w-full object-cover"
          />
        ) : (
          <Image
            src={item.url}
            alt={`Generated variant ${index + 1}`}
            width={512}
            height={512}
            unoptimized
            className="h-full w-full object-cover"
          />
        )}
      </div>
      <div className="p-3 flex items-center justify-between gap-2">
        <DkBadge tone="brand">Variant {index + 1}</DkBadge>
        <span className="text-xs text-[var(--dk-fg-2)] font-mono">
          {item.provider} · approval #{item.approval_request_id.slice(0, 8)}
        </span>
      </div>
    </div>
  );
}
