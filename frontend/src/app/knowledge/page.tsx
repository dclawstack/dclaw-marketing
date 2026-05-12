"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Brain,
  Database,
  Globe,
  Link2,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Upload,
} from "lucide-react";

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
  DkTabs,
  DkTabsContent,
  DkTabsList,
  DkTabsTrigger,
} from "@/components/dk";
import {
  confirmAssetUpload,
  ingestAssetIntoKG,
  inferAssetKind,
  startAssetUpload,
} from "@/lib/api";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

type IngestStatus =
  | "queued"
  | "fetching"
  | "parsing"
  | "chunking"
  | "embedding"
  | "ready"
  | "failed";

type IngestSource = {
  id: string;
  organization_id: string;
  source_type: "file" | "url" | "git" | "zip";
  source_reference: string;
  name: string | null;
  status: IngestStatus;
  document_chunks_created: number;
  error_message: string | null;
  metadata_json: Record<string, unknown> | null;
  job_id: string | null;
};

type SearchResult = {
  chunk_id: string;
  source_id: string;
  text: string;
  similarity: number;
};

const STATUS_TONE: Record<IngestStatus, "success" | "warning" | "danger" | "neutral" | "info"> =
  {
    queued: "neutral",
    fetching: "info",
    parsing: "info",
    chunking: "info",
    embedding: "info",
    ready: "success",
    failed: "danger",
  };

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

export default function KnowledgeConsolePage() {
  const { currentOrg } = useOrg();
  const [sources, setSources] = useState<IngestSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Add URL form
  const [urlInput, setUrlInput] = useState("");
  const [urlName, setUrlName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // File upload
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploadStage, setUploadStage] = useState<
    null | "presign" | "upload" | "confirm" | "ingest"
  >(null);

  // Search
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  const refresh = useCallback(async () => {
    if (!currentOrg) return;
    setLoading(true);
    setError(null);
    try {
      const rows = await authFetch<IngestSource[]>(
        `/api/v1/ingest?organization_id=${currentOrg.id}`,
      );
      setSources(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [currentOrg]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Auto-refresh while anything is in-flight.
  useEffect(() => {
    const anyInFlight = sources.some(
      (s) => s.status !== "ready" && s.status !== "failed",
    );
    if (!anyInFlight || !currentOrg) return;
    const id = window.setInterval(() => {
      void refresh();
    }, 4000);
    return () => window.clearInterval(id);
  }, [sources, currentOrg, refresh]);

  async function uploadAndIngest(file: File) {
    if (!currentOrg) return;
    setError(null);
    try {
      setUploadStage("presign");
      const kind = inferAssetKind(file.type, file.name);
      const { asset, presigned_put_url } = await startAssetUpload({
        filename: file.name,
        mime_type: file.type || "application/octet-stream",
        kind,
        organization_id: currentOrg.id,
      });

      setUploadStage("upload");
      const putRes = await fetch(presigned_put_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });
      if (!putRes.ok) {
        throw new Error(`Upload PUT failed (${putRes.status})`);
      }

      setUploadStage("confirm");
      await confirmAssetUpload(asset.id);

      setUploadStage("ingest");
      await ingestAssetIntoKG(currentOrg.id, asset.id, file.name);

      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploadStage(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function onFilePick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) await uploadAndIngest(f);
  }

  async function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) await uploadAndIngest(f);
  }

  async function addUrl() {
    if (!currentOrg || !urlInput.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await authFetch("/api/v1/ingest/urls", {
        method: "POST",
        body: JSON.stringify({
          organization_id: currentOrg.id,
          url: urlInput.trim(),
          name: urlName.trim() || undefined,
        }),
      });
      setUrlInput("");
      setUrlName("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Add URL failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function runSearch() {
    if (!currentOrg || !query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const j = await authFetch<{ results: SearchResult[] }>(
        `/api/v1/kg/search`,
        {
          method: "POST",
          body: JSON.stringify({
            organization_id: currentOrg.id,
            query: query.trim(),
            top_k: 5,
          }),
        },
      );
      setSearchResults(j.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  function iconFor(t: IngestSource["source_type"]) {
    if (t === "url") return <Globe className="h-4 w-4" />;
    if (t === "git") return <Link2 className="h-4 w-4" />;
    if (t === "zip") return <Database className="h-4 w-4" />;
    return <Database className="h-4 w-4" />;
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Knowledge · Theme Q2 / Q3"
        title="Knowledge Console"
        description="Feed the Knowledge Graph: paste a URL, watch the agent crawl + chunk + embed it, then semantic-search across everything you've ingested."
      />

      {error ? (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      ) : null}

      {!currentOrg ? (
        <DkEmptyState
          icon={<Brain className="h-6 w-6" />}
          title="Pick an organization"
          description="The Knowledge Graph is per-Org — use the workspace switcher."
        />
      ) : (
        <DkTabs defaultValue="sources">
          <DkTabsList>
            <DkTabsTrigger value="sources">
              <Database className="h-4 w-4" /> Sources
            </DkTabsTrigger>
            <DkTabsTrigger value="search">
              <Search className="h-4 w-4" /> Search
            </DkTabsTrigger>
          </DkTabsList>

          {/* SOURCES TAB */}
          <DkTabsContent value="sources">
            <DkCard>
              <DkCardHeader>
                <DkCardTitle>Upload a file</DkCardTitle>
                <DkCardDescription>
                  PDF / Markdown / text / CSV / JSON. The worker extracts text,
                  chunks, and embeds it. Drop here or pick from your machine.
                </DkCardDescription>
              </DkCardHeader>
              <DkCardContent>
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={onDrop}
                  className="flex flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed border-[var(--dk-border-strong)] py-6 px-3 text-center"
                >
                  <Upload className="h-6 w-6 text-brand" />
                  <div className="text-sm">
                    {uploadStage
                      ? {
                          presign: "Requesting upload URL…",
                          upload: "Uploading bytes…",
                          confirm: "Confirming asset…",
                          ingest: "Queueing ingestion…",
                        }[uploadStage]
                      : "Drag and drop a file here"}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={onFilePick}
                    accept=".pdf,.md,.markdown,.txt,.csv,.json,.xml,.yaml,.yml"
                  />
                  <DkButton
                    variant="ghost"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={!!uploadStage}
                  >
                    {uploadStage ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Plus className="h-4 w-4" />
                    )}
                    Choose file
                  </DkButton>
                </div>
              </DkCardContent>
            </DkCard>

            <DkCard>
              <DkCardHeader>
                <DkCardTitle>Add a URL</DkCardTitle>
                <DkCardDescription>
                  The worker fetches the page (5 MiB cap, 30s timeout), strips
                  HTML, chunks, and embeds. Re-fetches replace prior chunks for
                  the same source.
                </DkCardDescription>
              </DkCardHeader>
              <DkCardContent className="grid gap-3 md:grid-cols-[1fr_220px_auto]">
                <div>
                  <DkLabel>URL</DkLabel>
                  <DkInput
                    placeholder="https://example.com/pricing"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                  />
                </div>
                <div>
                  <DkLabel>Friendly name (optional)</DkLabel>
                  <DkInput
                    placeholder="Pricing page"
                    value={urlName}
                    onChange={(e) => setUrlName(e.target.value)}
                  />
                </div>
                <div className="flex items-end">
                  <DkButton
                    onClick={addUrl}
                    disabled={submitting || !urlInput.trim()}
                  >
                    {submitting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Plus className="h-4 w-4" />
                    )}
                    Add URL
                  </DkButton>
                </div>
              </DkCardContent>
            </DkCard>

            <div className="flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold">
                Sources ({sources.length})
              </h2>
              <DkButton variant="ghost" onClick={refresh} disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                Refresh
              </DkButton>
            </div>

            {sources.length === 0 ? (
              <DkEmptyState
                icon={<Brain className="h-6 w-6" />}
                title="No sources yet"
                description="Paste a URL above (or upload a file via the Assets page) to seed the Knowledge Graph."
              />
            ) : (
              <div className="grid gap-2">
                {sources.map((s) => (
                  <DkCard key={s.id}>
                    <DkCardContent className="flex flex-wrap items-center gap-3 py-3">
                      {iconFor(s.source_type)}
                      <div className="grow min-w-0">
                        <div className="font-medium truncate">
                          {s.name || s.source_reference}
                        </div>
                        <div className="text-xs font-mono opacity-60 truncate">
                          {s.source_type}: {s.source_reference}
                        </div>
                        {s.error_message ? (
                          <div className="text-xs text-[var(--dk-danger)] mt-1">
                            {s.error_message}
                          </div>
                        ) : null}
                      </div>
                      <DkBadge tone={STATUS_TONE[s.status]}>
                        {s.status}
                      </DkBadge>
                      <span className="text-sm opacity-70">
                        {s.document_chunks_created} chunks
                      </span>
                    </DkCardContent>
                  </DkCard>
                ))}
              </div>
            )}
          </DkTabsContent>

          {/* SEARCH TAB */}
          <DkTabsContent value="search">
            <DkCard>
              <DkCardContent className="flex flex-col gap-3">
                <DkLabel>Query</DkLabel>
                <div className="flex gap-2">
                  <DkInput
                    placeholder="What does the agent know about pricing?"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void runSearch();
                    }}
                  />
                  <DkButton onClick={runSearch} disabled={searching || !query.trim()}>
                    {searching ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                    Search
                  </DkButton>
                </div>
              </DkCardContent>
            </DkCard>

            {searchResults.length === 0 ? (
              <DkEmptyState
                icon={<Search className="h-6 w-6" />}
                title="No results yet"
                description="Type a question or topic above to search the embedded chunks via pgvector cosine similarity."
              />
            ) : (
              <div className="flex flex-col gap-2">
                {searchResults.map((r) => (
                  <DkCard key={r.chunk_id}>
                    <DkCardContent className="py-3">
                      <div className="flex items-center justify-between mb-2">
                        <DkBadge tone="brand">
                          {(r.similarity * 100).toFixed(0)}% match
                        </DkBadge>
                        <span className="text-xs font-mono opacity-50">
                          source {r.source_id.slice(0, 8)}
                        </span>
                      </div>
                      <div className="text-sm whitespace-pre-wrap line-clamp-6">
                        {r.text}
                      </div>
                    </DkCardContent>
                  </DkCard>
                ))}
              </div>
            )}
          </DkTabsContent>
        </DkTabs>
      )}
    </div>
  );
}
