"use client";

import { useCallback, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { CloudUpload, FileText, GitBranch, Globe, Archive } from "lucide-react";

import {
  DkBadge,
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkProgress,
  DkTabs,
  DkTabsContent,
  DkTabsList,
  DkTabsTrigger,
} from "@/components/dk";
import {
  confirmAssetUpload,
  inferAssetKind,
  ingestFile,
  startAssetUpload,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Phase =
  | "idle"
  | "creating"
  | "uploading"
  | "confirming"
  | "ingesting"
  | "done"
  | "error";

export default function NewSourcePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const orgId = params?.id ?? "";

  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const onPick = useCallback((f: File | null) => {
    setFile(f);
    setError(null);
    setPhase("idle");
    setProgress(0);
    if (f && !name) setName(f.name.replace(/\.[^.]+$/, ""));
  }, [name]);

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onPick(f);
  }

  async function uploadAndIngest() {
    if (!file) return;
    setError(null);
    try {
      // 1. Create asset + get presigned PUT
      setPhase("creating");
      setProgress(5);
      const kind = inferAssetKind(file.type, file.name);
      const created = await startAssetUpload({
        filename: file.name,
        mime_type: file.type || "application/octet-stream",
        kind,
        organization_id: orgId,
      });

      // 2. PUT bytes to presigned URL
      setPhase("uploading");
      setProgress(15);
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", created.presigned_put_url);
        xhr.setRequestHeader(
          "Content-Type",
          file.type || "application/octet-stream",
        );
        xhr.upload.onprogress = (ev) => {
          if (ev.lengthComputable) {
            const pct = 15 + (ev.loaded / ev.total) * 60;
            setProgress(Math.round(pct));
          }
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) resolve();
          else reject(new Error(`Upload failed (${xhr.status})`));
        };
        xhr.onerror = () => reject(new Error("Network error during upload"));
        xhr.send(file);
      });

      // 3. Confirm
      setPhase("confirming");
      setProgress(80);
      await confirmAssetUpload(created.asset.id);

      // 4. Trigger ingestion
      setPhase("ingesting");
      setProgress(92);
      await ingestFile({
        organization_id: orgId,
        asset_id: created.asset.id,
        name: name || undefined,
      });

      setProgress(100);
      setPhase("done");
      setTimeout(() => router.push(`/orgs/${orgId}/knowledge`), 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setPhase("error");
    }
  }

  const phaseLabels: Record<Phase, string> = {
    idle: "Ready",
    creating: "Preparing upload…",
    uploading: "Uploading…",
    confirming: "Confirming…",
    ingesting: "Queuing for ingestion…",
    done: "Done — redirecting",
    error: "Failed",
  };

  return (
    <div className="flex flex-col gap-8 max-w-3xl">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          { label: "Org", href: `/orgs/${orgId}` },
          { label: "Knowledge", href: `/orgs/${orgId}/knowledge` },
          { label: "Add source" },
        ]}
      />
      <DkPageHeader
        eyebrow="Theme Q2 · Input Channel Hub"
        title="Add Source"
        description="Drop in content for the Knowledge Graph. Files become memory the agents pull from at run time."
      />

      <DkTabs defaultValue="file">
        <DkTabsList>
          <DkTabsTrigger value="file">
            <FileText className="h-4 w-4 mr-1.5" />
            File
          </DkTabsTrigger>
          <DkTabsTrigger value="url">
            <Globe className="h-4 w-4 mr-1.5" />
            URL
          </DkTabsTrigger>
          <DkTabsTrigger value="git">
            <GitBranch className="h-4 w-4 mr-1.5" />
            Git
          </DkTabsTrigger>
          <DkTabsTrigger value="zip">
            <Archive className="h-4 w-4 mr-1.5" />
            Zip
          </DkTabsTrigger>
        </DkTabsList>

        <DkTabsContent value="file" className="pt-4">
          <DkCard>
            <DkCardContent className="flex flex-col gap-4 py-6">
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                className={cn(
                  "flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-fast",
                  dragOver
                    ? "border-brand bg-[var(--dk-purple-50)]"
                    : "border-[var(--dk-border-strong)] hover:border-brand hover:bg-[var(--dk-bg-tint)]",
                )}
              >
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--dk-purple-50)] text-brand">
                  <CloudUpload className="h-7 w-7" />
                </div>
                <div className="flex flex-col gap-1">
                  <p className="font-display text-base font-semibold text-ink">
                    {file ? file.name : "Drop a file or click to browse"}
                  </p>
                  {file ? (
                    <p className="text-sm text-[var(--dk-fg-2)]">
                      {(file.size / 1024).toFixed(1)} KB ·{" "}
                      {file.type || "unknown type"}
                    </p>
                  ) : (
                    <p className="text-sm text-[var(--dk-fg-2)]">
                      PDF · DOCX · PPTX · Markdown · text · CSV · images · audio · video
                    </p>
                  )}
                </div>
              </button>
              <input
                ref={inputRef}
                type="file"
                className="hidden"
                onChange={(e) => onPick(e.target.files?.[0] ?? null)}
              />

              {file && (
                <div className="flex flex-col gap-3">
                  <div className="flex flex-col gap-1.5">
                    <DkLabel htmlFor="src-name">
                      Display name (optional)
                    </DkLabel>
                    <DkInput
                      id="src-name"
                      placeholder="Q2 customer-interview transcript"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </div>

                  {phase !== "idle" && phase !== "error" && (
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-ink">
                          {phaseLabels[phase]}
                        </span>
                        <span className="font-mono text-xs text-[var(--dk-fg-2)]">
                          {progress}%
                        </span>
                      </div>
                      <DkProgress
                        value={progress}
                        tone={phase === "done" ? "success" : "brand"}
                      />
                    </div>
                  )}

                  {error && (
                    <div
                      role="alert"
                      className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
                    >
                      {error}
                    </div>
                  )}

                  <div className="flex items-center gap-2 pt-1">
                    <Link href={`/orgs/${orgId}/knowledge`}>
                      <DkButton variant="secondary">Cancel</DkButton>
                    </Link>
                    <DkButton
                      onClick={uploadAndIngest}
                      disabled={
                        !file ||
                        phase === "creating" ||
                        phase === "uploading" ||
                        phase === "confirming" ||
                        phase === "ingesting" ||
                        phase === "done"
                      }
                      loading={
                        phase === "creating" ||
                        phase === "uploading" ||
                        phase === "confirming" ||
                        phase === "ingesting"
                      }
                      withArrow={phase === "idle" || phase === "error"}
                    >
                      {phase === "done" ? "Done" : "Upload &amp; Ingest"}
                    </DkButton>
                  </div>
                </div>
              )}
            </DkCardContent>
          </DkCard>
        </DkTabsContent>

        {(["url", "git", "zip"] as const).map((t) => (
          <DkTabsContent key={t} value={t} className="pt-4">
            <DkCard>
              <DkCardHeader>
                <DkCardTitle className="text-base capitalize flex items-center gap-2">
                  {t === "url" && <Globe className="h-4 w-4" />}
                  {t === "git" && <GitBranch className="h-4 w-4" />}
                  {t === "zip" && <Archive className="h-4 w-4" />}
                  {t === "url"
                    ? "URL ingestion"
                    : t === "git"
                    ? "Git repository"
                    : "Zip archive"}
                  <DkBadge tone="brand">soon</DkBadge>
                </DkCardTitle>
                <DkCardDescription>
                  {t === "url" &&
                    "Sitemap-aware crawler that follows internal links, extracts text, and chunks per page. Ships in a follow-up PR."}
                  {t === "git" &&
                    "Clone a public repo or supply a token for a private one; READMEs, docs and code get chunked into the KG."}
                  {t === "zip" &&
                    "Drop in a zip archive; the worker unpacks it and ingests every supported file inside."}
                </DkCardDescription>
              </DkCardHeader>
              <DkCardContent>
                <p className="text-sm text-[var(--dk-fg-2)]">
                  This source type isn&apos;t wired up yet — backend support ships
                  next.
                </p>
              </DkCardContent>
            </DkCard>
          </DkTabsContent>
        ))}
      </DkTabs>
    </div>
  );
}
