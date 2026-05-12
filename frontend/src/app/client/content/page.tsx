"use client";

import { useEffect, useState } from "react";
import { Image as ImageIcon } from "lucide-react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkEmptyState,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

interface Asset {
  id: string;
  kind: string;
  filename: string | null;
  mime_type: string | null;
  preview_url: string | null;
  created_at: string;
}

export default function ClientContentPage() {
  const { currentOrg } = useOrg();
  const [rows, setRows] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentOrg) return;
    setLoading(true);
    fetch(`/api/v1/assets?organization_id=${currentOrg.id}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((j: Asset[]) =>
        setRows(
          (Array.isArray(j) ? j : []).sort(
            (a, b) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime(),
          ),
        ),
      )
      .finally(() => setLoading(false));
  }, [currentOrg]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Client Portal"
        title="Approved content"
        description="Every image, video, and asset your agency has produced and you've signed off on. Re-share or download."
      />
      {loading ? (
        <DkSkeleton className="h-32 w-full" />
      ) : rows.length === 0 ? (
        <DkEmptyState
          icon={<ImageIcon className="h-6 w-6" />}
          title="No assets yet"
          description="When your agency uploads approved content, it'll appear in this gallery."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {rows.map((a) => (
            <DkCard key={a.id}>
              <div className="aspect-square bg-[var(--dk-gray-50)] flex items-center justify-center overflow-hidden rounded-t-2xl">
                {a.preview_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={a.preview_url}
                    alt={a.filename ?? "asset"}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <ImageIcon className="h-8 w-8 text-[var(--dk-fg-2)]" />
                )}
              </div>
              <DkCardContent className="flex flex-col gap-1 py-3">
                <p className="text-sm font-medium text-ink truncate">
                  {a.filename ?? a.id.slice(0, 8)}
                </p>
                <div className="flex items-center justify-between text-xs text-[var(--dk-fg-2)]">
                  <DkBadge tone="info">{a.kind}</DkBadge>
                  <span>{new Date(a.created_at).toLocaleDateString()}</span>
                </div>
              </DkCardContent>
            </DkCard>
          ))}
        </div>
      )}
    </div>
  );
}
