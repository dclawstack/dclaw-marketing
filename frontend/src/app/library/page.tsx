"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Archive,
  Brain,
  Database,
  Download,
  File,
  FileText,
  Image as ImageIcon,
  Loader2,
  Music,
  Video,
  Trash2,
} from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkEmptyState,
  DkPageHeader,
  DkSelect,
  DkSkeleton,
} from "@/components/dk";
import {
  Asset,
  AssetKind,
  deleteAsset,
  ingestAssetIntoKG,
  getAssetDownloadUrl,
  listAssets,
} from "@/lib/api";
import { useOrg } from "@/contexts/org-context";

const KIND_ICON: Record<AssetKind, React.ComponentType<{ className?: string }>> = {
  image: ImageIcon,
  video: Video,
  audio: Music,
  document: FileText,
  data: Database,
  archive: Archive,
  other: File,
};

const KIND_LABEL: Record<AssetKind, string> = {
  image: "Image",
  video: "Video",
  audio: "Audio",
  document: "Document",
  data: "Data",
  archive: "Archive",
  other: "Other",
};

function formatSize(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function LibraryPage() {
  const { currentOrg } = useOrg();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<AssetKind | "">("");

  const refresh = useCallback(async () => {
    if (!currentOrg) {
      setAssets([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await listAssets(currentOrg.id, filter || undefined);
      setAssets(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [currentOrg, filter]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function download(a: Asset) {
    try {
      const { presigned_get_url } = await getAssetDownloadUrl(a.id);
      window.open(presigned_get_url, "_blank", "noopener");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Download failed.");
    }
  }

  async function remove(a: Asset) {
    if (!confirm(`Delete ${a.original_filename ?? a.id}? This cannot be undone.`))
      return;
    try {
      await deleteAsset(a.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  const [ingestingId, setIngestingId] = useState<string | null>(null);

  async function ingest(a: Asset) {
    if (!currentOrg) return;
    setIngestingId(a.id);
    try {
      await ingestAssetIntoKG(currentOrg.id, a.id, a.original_filename ?? undefined);
      alert(
        `Ingestion queued. Watch progress on /knowledge — the source will move through queued → fetching → parsing → chunking → embedding → ready.`,
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Ingest failed.");
    } finally {
      setIngestingId(null);
    }
  }

  const kinds = useMemo<AssetKind[]>(
    () =>
      Array.from(new Set(assets.map((a) => a.kind))) as AssetKind[],
    [assets],
  );

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Workspace · DAM"
        title="Asset Library"
        description={
          currentOrg
            ? `All files and generated outputs in ${currentOrg.name}. Click any asset to download a fresh presigned URL.`
            : "Pick an organization in the nav to see its assets."
        }
        actions={
          <div className="flex items-center gap-2">
            <DkSelect
              value={filter}
              onChange={(e) => setFilter(e.target.value as AssetKind | "")}
              className="w-40"
            >
              <option value="">All kinds</option>
              {(Object.keys(KIND_LABEL) as AssetKind[]).map((k) => (
                <option key={k} value={k}>
                  {KIND_LABEL[k]}
                </option>
              ))}
            </DkSelect>
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

      {!currentOrg ? (
        <DkEmptyState
          icon={<File className="h-6 w-6" />}
          title="Pick an organization"
          description="The library is org-scoped — use the switcher in the nav to choose one."
        />
      ) : loading ? (
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <DkSkeleton key={i} className="h-40" />
          ))}
        </div>
      ) : assets.length === 0 ? (
        <DkEmptyState
          icon={<File className="h-6 w-6" />}
          title="No assets yet"
          description="Upload a file via the Knowledge Hub, or generate one through the Creatives Agent. Everything lands here."
        />
      ) : (
        <>
          {kinds.length > 1 && (
            <div className="flex items-center gap-2 text-xs text-[var(--dk-fg-2)]">
              <span>By kind:</span>
              {kinds.map((k) => (
                <DkBadge key={k} tone="neutral">
                  {KIND_LABEL[k]}: {assets.filter((a) => a.kind === k).length}
                </DkBadge>
              ))}
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {assets.map((a) => {
              const Icon = KIND_ICON[a.kind];
              return (
                <DkCard key={a.id} hover className="h-full flex flex-col">
                  <DkCardContent className="flex flex-col gap-3 py-4">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-[var(--dk-purple-50)] text-brand shrink-0">
                        <Icon className="h-4 w-4" />
                      </div>
                      <DkBadge tone="neutral" className="uppercase text-[10px]">
                        {KIND_LABEL[a.kind]}
                      </DkBadge>
                    </div>
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <p
                        className="font-medium text-ink text-sm truncate"
                        title={a.original_filename ?? a.id}
                      >
                        {a.original_filename ?? a.id.slice(0, 12)}
                      </p>
                      <p className="text-xs text-[var(--dk-fg-2)] font-mono">
                        {formatSize(a.size_bytes)} · {a.mime_type}
                      </p>
                    </div>
                  </DkCardContent>
                  <div className="px-4 pb-4 flex items-center gap-1.5">
                    <DkButton
                      size="sm"
                      variant="secondary"
                      onClick={() => download(a)}
                      className="flex-1"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Download
                    </DkButton>
                    {(a.kind === "document" || a.kind === "data") && (
                      <DkButton
                        size="sm"
                        variant="ghost"
                        aria-label="Ingest into Knowledge Graph"
                        title="Ingest into Knowledge Graph"
                        onClick={() => ingest(a)}
                        disabled={ingestingId === a.id}
                        className="px-2"
                      >
                        {ingestingId === a.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Brain className="h-3.5 w-3.5" />
                        )}
                      </DkButton>
                    )}
                    <DkButton
                      size="sm"
                      variant="ghost"
                      aria-label="Delete"
                      onClick={() => remove(a)}
                      className="text-[var(--dk-fg-2)] hover:text-[var(--dk-danger)] px-2"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </DkButton>
                  </div>
                </DkCard>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
