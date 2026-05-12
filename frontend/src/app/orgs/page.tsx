"use client";

import { useState } from "react";
import Link from "next/link";
import { Building2, Plus, Trash2 } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkDialog,
  DkDialogContent,
  DkDialogFooter,
  DkDialogHeader,
  DkEmptyState,
  DkInput,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { useAuth } from "@/contexts/auth-context";
import { useOrg } from "@/contexts/org-context";
import { Organization, deleteOrg } from "@/lib/api";

export default function OrgsListPage() {
  const { orgs, loading, error, refresh } = useOrg();
  const { user } = useAuth();

  const [pendingDelete, setPendingDelete] = useState<Organization | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const closeDialog = () => {
    if (deleting) return;
    setPendingDelete(null);
    setConfirmText("");
    setDeleteError(null);
  };

  const submitDelete = async () => {
    if (!pendingDelete) return;
    if (confirmText !== pendingDelete.name) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteOrg(pendingDelete.id);
      await refresh();
      setPendingDelete(null);
      setConfirmText("");
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : "Failed to delete organization.",
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Workspace"
        title="Organizations"
        description="Every brand kit, project, knowledge base, and connected social account is scoped to an Organization. Create as many as you need."
        actions={
          <Link href="/orgs/new">
            <DkButton>
              <Plus className="h-4 w-4" />
              New Organization
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
            <DkCard key={i}>
              <DkCardContent className="flex flex-col gap-3 py-6">
                <DkSkeleton className="h-5 w-2/3" />
                <DkSkeleton className="h-4 w-full" />
                <DkSkeleton className="h-4 w-4/5" />
              </DkCardContent>
            </DkCard>
          ))}
        </div>
      ) : orgs.length === 0 ? (
        <DkEmptyState
          icon={<Building2 className="h-6 w-6" />}
          title="No organizations yet"
          description="An organization is the top container for your brand kit, knowledge base, projects, and connected accounts. Start with one for the company you're working in."
          actions={
            <Link href="/orgs/new">
              <DkButton withArrow>Create Your First Organization</DkButton>
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {orgs.map((o) => (
            <div key={o.id} className="relative group">
              <Link href={`/orgs/${o.id}`} className="block">
                <DkCard hover className="h-full">
                  <DkCardContent className="flex flex-col gap-3 py-6">
                    <div className="flex items-start justify-between gap-3 pr-8">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--dk-purple-50)] text-brand">
                          <Building2 className="h-5 w-5" />
                        </div>
                        <div className="flex flex-col">
                          <h3 className="font-display text-lg font-semibold leading-snug text-ink group-hover:text-brand transition-colors duration-fast">
                            {o.name}
                          </h3>
                          <span className="text-xs font-mono text-[var(--dk-fg-2)]">
                            {o.slug}
                          </span>
                        </div>
                      </div>
                      {o.is_external && (
                        <DkBadge tone="info">external</DkBadge>
                      )}
                    </div>
                    {o.description && (
                      <p className="text-sm leading-relaxed text-[var(--dk-fg-1)] line-clamp-3">
                        {o.description}
                      </p>
                    )}
                  </DkCardContent>
                </DkCard>
              </Link>

              {user?.is_superuser && (
                <button
                  type="button"
                  aria-label={`Delete organization ${o.name}`}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setPendingDelete(o);
                    setConfirmText("");
                    setDeleteError(null);
                  }}
                  className="absolute top-3 right-3 rounded-pill p-2 text-[var(--dk-fg-2)] opacity-0 transition-opacity duration-fast hover:bg-[var(--dk-danger-bg)] hover:text-[var(--dk-danger)] focus-visible:opacity-100 group-hover:opacity-100"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <DkDialog open={pendingDelete !== null} onClose={closeDialog} size="md">
        {pendingDelete && (
          <>
            <DkDialogHeader
              title="Delete organization?"
              description={`This permanently removes “${pendingDelete.name}” and every project, brand kit, scheduled post, lead, knowledge chunk, and connected account inside it. This cannot be undone.`}
              onClose={closeDialog}
            />
            <DkDialogContent>
              <label className="flex flex-col gap-2 text-sm text-ink">
                Type the organization name{" "}
                <span className="font-mono font-semibold">
                  {pendingDelete.name}
                </span>{" "}
                to confirm.
                <DkInput
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder={pendingDelete.name}
                  autoFocus
                  disabled={deleting}
                />
              </label>
              {deleteError && (
                <p
                  role="alert"
                  className="mt-3 rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
                >
                  {deleteError}
                </p>
              )}
            </DkDialogContent>
            <DkDialogFooter>
              <DkButton
                variant="secondary"
                onClick={closeDialog}
                disabled={deleting}
              >
                Cancel
              </DkButton>
              <DkButton
                variant="danger"
                onClick={submitDelete}
                disabled={confirmText !== pendingDelete.name || deleting}
                loading={deleting}
              >
                Delete forever
              </DkButton>
            </DkDialogFooter>
          </>
        )}
      </DkDialog>
    </div>
  );
}
