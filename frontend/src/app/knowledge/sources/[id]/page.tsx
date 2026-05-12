"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Database } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkEmptyState,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { getToken } from "@/lib/auth";

type Source = {
  id: string;
  organization_id: string;
  source_type: string;
  source_reference: string;
  name: string | null;
  status: string;
  document_chunks_created: number;
  error_message: string | null;
  metadata_json: Record<string, unknown> | null;
};

type Chunk = {
  id: string;
  source_id: string;
  position: number;
  text: string;
  estimated_tokens: number | null;
  metadata_json: Record<string, unknown> | null;
};

async function authFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function SourceDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const [src, setSrc] = useState<Source | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      authFetch<Source>(`/api/v1/ingest/${id}`),
      authFetch<Chunk[]>(`/api/v1/ingest/${id}/chunks?limit=500`),
    ])
      .then(([s, c]) => {
        if (!cancelled) {
          setSrc(s);
          setChunks(c);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link href="/knowledge">
          <DkButton variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" /> Back to Knowledge Console
          </DkButton>
        </Link>
      </div>

      <DkPageHeader
        eyebrow="Knowledge · Source detail"
        title={loading ? "Loading…" : src?.name ?? src?.source_reference ?? "Source"}
        description={
          src
            ? `${src.source_type} · ${src.document_chunks_created} chunks · status: ${src.status}`
            : ""
        }
        actions={src ? <DkBadge tone="brand">{src.source_type}</DkBadge> : null}
      />

      {error ? (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <DkSkeleton key={i} className="h-16" />
          ))}
        </div>
      ) : chunks.length === 0 ? (
        <DkEmptyState
          icon={<Database className="h-6 w-6" />}
          title="No chunks yet"
          description="Either the ingestion is still running or the source produced no extractable text."
        />
      ) : (
        <div className="flex flex-col gap-2">
          {chunks.map((c) => (
            <DkCard key={c.id}>
              <DkCardContent className="py-3">
                <div className="flex items-center justify-between mb-1">
                  <DkBadge tone="neutral">chunk #{c.position}</DkBadge>
                  <span className="text-xs font-mono opacity-50">
                    {c.estimated_tokens ? `${c.estimated_tokens} tokens` : ""}
                  </span>
                </div>
                <div className="text-sm whitespace-pre-wrap leading-snug">
                  {c.text}
                </div>
              </DkCardContent>
            </DkCard>
          ))}
        </div>
      )}
    </div>
  );
}
