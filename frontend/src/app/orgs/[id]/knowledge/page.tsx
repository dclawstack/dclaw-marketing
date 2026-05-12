"use client";

import * as React from "react";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  BookOpen,
  FileText,
  Globe,
  GitBranch,
  Archive,
  Plus,
  RefreshCw,
  Search,
} from "lucide-react";

import {
  DkBadge,
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkEmptyState,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSkeleton,
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
  DkTabs,
  DkTabsContent,
  DkTabsList,
  DkTabsTrigger,
  DkTextarea,
} from "@/components/dk";
import {
  DocumentChunk,
  IngestionSource,
  IngestionStatus,
  KGSearchResponse,
  KGStats,
  getIngestionChunks,
  kgSearch,
  kgStats,
  listIngestions,
} from "@/lib/api";

const STATUS_TONE: Record<
  IngestionStatus,
  "neutral" | "info" | "warning" | "success" | "danger" | "brand"
> = {
  queued: "neutral",
  fetching: "info",
  parsing: "info",
  chunking: "info",
  embedding: "brand",
  ready: "success",
  failed: "danger",
};

const SOURCE_ICON = {
  file: FileText,
  url: Globe,
  git: GitBranch,
  zip: Archive,
} as const;

export default function KnowledgePage() {
  const params = useParams<{ id: string }>();
  const orgId = params?.id ?? "";

  const [sources, setSources] = useState<IngestionSource[]>([]);
  const [stats, setStats] = useState<KGStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Chunks viewer (drawer-like inline)
  const [expanded, setExpanded] = useState<string | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);

  // Semantic search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchTopK, setSearchTopK] = useState(5);
  const [searchResults, setSearchResults] = useState<KGSearchResponse | null>(
    null,
  );
  const [searching, setSearching] = useState(false);

  const refresh = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const [src, st] = await Promise.all([
        listIngestions(orgId),
        kgStats(orgId),
      ]);
      setSources(src);
      setStats(st);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function viewChunks(sourceId: string) {
    if (expanded === sourceId) {
      setExpanded(null);
      setChunks([]);
      return;
    }
    setExpanded(sourceId);
    setChunksLoading(true);
    try {
      const c = await getIngestionChunks(sourceId);
      setChunks(c);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to load chunks.");
      setExpanded(null);
    } finally {
      setChunksLoading(false);
    }
  }

  async function runSearch() {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await kgSearch(orgId, searchQuery, searchTopK);
      setSearchResults(res);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  const statCards = stats
    ? [
        { label: "Sources", value: stats.source_count, tone: "neutral" as const },
        {
          label: "Total Chunks",
          value: stats.chunk_count,
          tone: "neutral" as const,
        },
        {
          label: "Embedded",
          value: stats.embedded_count,
          tone:
            stats.chunk_count > 0 && stats.embedded_count < stats.chunk_count
              ? "warning"
              : "success",
        },
      ]
    : [];

  return (
    <div className="flex flex-col gap-8">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          { label: "…", href: orgId ? `/orgs/${orgId}` : "/orgs" },
          { label: "Knowledge" },
        ]}
      />

      <DkPageHeader
        eyebrow="Organization · Theme Q3"
        title="Knowledge Graph"
        description="Every file, URL, repo, and zip ingested into this org. Agents read from this graph at run time; the more grounded context here, the better their output."
        actions={
          <>
            <DkButton variant="secondary" onClick={() => void refresh()}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </DkButton>
            <Link href={`/orgs/${orgId}/knowledge/sources/new`}>
              <DkButton>
                <Plus className="h-4 w-4" />
                Add Source
              </DkButton>
            </Link>
          </>
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

      {/* Stats strip */}
      <div className="grid gap-3 sm:grid-cols-3">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => (
              <DkSkeleton key={i} className="h-24" />
            ))
          : statCards.map((s) => (
              <DkCard key={s.label}>
                <DkCardContent className="flex flex-col gap-1 py-5">
                  <span className="text-xs uppercase tracking-wide font-semibold text-[var(--dk-fg-2)]">
                    {s.label}
                  </span>
                  <span className="font-display text-3xl font-bold tabular-nums text-ink">
                    {s.value}
                  </span>
                </DkCardContent>
              </DkCard>
            ))}
      </div>

      <DkTabs defaultValue="sources">
        <DkTabsList>
          <DkTabsTrigger value="sources">Sources</DkTabsTrigger>
          <DkTabsTrigger value="search">Semantic Search</DkTabsTrigger>
        </DkTabsList>

        <DkTabsContent value="sources" className="flex flex-col gap-4 pt-4">
          {loading ? (
            <DkSkeleton className="h-64" />
          ) : sources.length === 0 ? (
            <DkEmptyState
              icon={<BookOpen className="h-6 w-6" />}
              title="Nothing ingested yet"
              description="Upload files, paste URLs, point at a git repo. Sources are extracted, chunked, embedded into pgvector — and become memory the agents pull from."
              actions={
                <Link href={`/orgs/${orgId}/knowledge/sources/new`}>
                  <DkButton withArrow>Add the First Source</DkButton>
                </Link>
              }
            />
          ) : (
            <DkCard>
              <DkCardContent className="p-0">
                <DkTable>
                  <DkTableHeader>
                    <DkTableRow>
                      <DkTableHead>Source</DkTableHead>
                      <DkTableHead>Type</DkTableHead>
                      <DkTableHead>Status</DkTableHead>
                      <DkTableHead className="text-right">Chunks</DkTableHead>
                      <DkTableHead className="text-right">Actions</DkTableHead>
                    </DkTableRow>
                  </DkTableHeader>
                  <DkTableBody>
                    {sources.map((s) => {
                      const Icon = SOURCE_ICON[s.source_type];
                      const open = expanded === s.id;
                      return (
                        <React.Fragment key={s.id}>
                          <DkTableRow>
                            <DkTableCell>
                              <div className="flex items-center gap-2.5">
                                <Icon className="h-4 w-4 text-[var(--dk-fg-2)] shrink-0" />
                                <div className="flex flex-col">
                                  <span className="font-medium text-ink">
                                    {s.name ?? s.source_reference}
                                  </span>
                                  {s.name && (
                                    <span className="text-xs font-mono text-[var(--dk-fg-2)] truncate max-w-md">
                                      {s.source_reference}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </DkTableCell>
                            <DkTableCell className="text-sm text-[var(--dk-fg-2)] capitalize">
                              {s.source_type}
                            </DkTableCell>
                            <DkTableCell>
                              <DkBadge tone={STATUS_TONE[s.status]}>
                                {s.status}
                              </DkBadge>
                              {s.error_message && (
                                <p className="mt-1 text-xs text-[var(--dk-danger)] max-w-xs truncate">
                                  {s.error_message}
                                </p>
                              )}
                            </DkTableCell>
                            <DkTableCell className="text-right tabular-nums">
                              {s.document_chunks_created}
                            </DkTableCell>
                            <DkTableCell className="text-right">
                              <DkButton
                                size="sm"
                                variant="secondary"
                                onClick={() => viewChunks(s.id)}
                                disabled={s.document_chunks_created === 0}
                              >
                                {open ? "Hide" : "View"} Chunks
                              </DkButton>
                            </DkTableCell>
                          </DkTableRow>
                          {open && (
                            <DkTableRow>
                              <DkTableCell
                                colSpan={5}
                                className="bg-[var(--dk-bg-tint)] p-4"
                              >
                                {chunksLoading ? (
                                  <DkSkeleton className="h-20" />
                                ) : chunks.length === 0 ? (
                                  <p className="text-sm text-[var(--dk-fg-2)]">
                                    No chunks for this source.
                                  </p>
                                ) : (
                                  <div className="flex flex-col gap-3">
                                    {chunks.map((c) => (
                                      <div
                                        key={c.id}
                                        className="rounded-md border border-[var(--dk-border)] bg-white p-3"
                                      >
                                        <div className="flex items-center justify-between mb-2">
                                          <DkBadge tone="brand">
                                            #{c.position}
                                          </DkBadge>
                                          {c.estimated_tokens && (
                                            <span className="text-xs font-mono text-[var(--dk-fg-2)]">
                                              {c.estimated_tokens} tok
                                            </span>
                                          )}
                                        </div>
                                        <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--dk-fg-1)]">
                                          {c.text}
                                        </p>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </DkTableCell>
                            </DkTableRow>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </DkTableBody>
                </DkTable>
              </DkCardContent>
            </DkCard>
          )}
        </DkTabsContent>

        <DkTabsContent value="search" className="flex flex-col gap-4 pt-4">
          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Test Semantic Search</DkCardTitle>
            </DkCardHeader>
            <DkCardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="kg-query">Query</DkLabel>
                <DkTextarea
                  id="kg-query"
                  rows={2}
                  placeholder="What does our customer say about price sensitivity?"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-3">
                <div className="flex flex-col gap-1.5">
                  <DkLabel htmlFor="kg-topk">Top K</DkLabel>
                  <DkInput
                    id="kg-topk"
                    type="number"
                    min={1}
                    max={50}
                    value={searchTopK}
                    onChange={(e) => setSearchTopK(Number(e.target.value) || 5)}
                    className="w-24"
                  />
                </div>
                <DkButton
                  onClick={() => void runSearch()}
                  disabled={!searchQuery.trim() || searching}
                  loading={searching}
                  className="self-end"
                >
                  <Search className="h-4 w-4" />
                  Search
                </DkButton>
              </div>
            </DkCardContent>
          </DkCard>

          {searchResults && (
            <DkCard>
              <DkCardHeader>
                <DkCardTitle className="text-base">
                  {searchResults.results.length} results
                </DkCardTitle>
              </DkCardHeader>
              <DkCardContent className="flex flex-col gap-3">
                {searchResults.results.length === 0 ? (
                  <p className="text-sm text-[var(--dk-fg-2)]">
                    No matches above the relevance threshold.
                  </p>
                ) : (
                  searchResults.results.map((r) => (
                    <div
                      key={r.chunk_id}
                      className="rounded-md border border-[var(--dk-border)] bg-white p-3"
                    >
                      <div className="flex items-center justify-between mb-2 gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <DkBadge tone="brand">
                            score {r.score.toFixed(3)}
                          </DkBadge>
                          <span className="text-xs text-[var(--dk-fg-2)] truncate">
                            {r.source_name ?? r.source_reference} · #
                            {r.position}
                          </span>
                        </div>
                      </div>
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--dk-fg-1)]">
                        {r.text}
                      </p>
                    </div>
                  ))
                )}
              </DkCardContent>
            </DkCard>
          )}
        </DkTabsContent>
      </DkTabs>
    </div>
  );
}
