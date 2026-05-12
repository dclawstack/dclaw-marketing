"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FileText, Plus, Trash2 } from "lucide-react";

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
  DkLabel,
  DkPageHeader,
  DkSkeleton,
  DkTextarea,
} from "@/components/dk";
import { getToken } from "@/lib/auth";

interface LandingPage {
  id: string;
  slug: string;
  title: string;
  body_html: string;
  published: boolean;
  created_at: string;
  updated_at: string;
}

export default function OrgLandingPagesPage() {
  const params = useParams<{ id: string }>();
  const orgId = params?.id ?? "";

  const [pages, setPages] = useState<LandingPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState<LandingPage | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [bodyHtml, setBodyHtml] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!orgId) return;
    setLoading(true);
    const r = await fetch(`/api/v1/orgs/${orgId}/pages`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    setPages(r.ok ? await r.json() : []);
    setLoading(false);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  function startCreate() {
    setSlug("");
    setTitle("");
    setBodyHtml("<h1>Headline</h1>\n<p>Subhead copy goes here.</p>");
    setCreateOpen(true);
  }

  function startEdit(p: LandingPage) {
    setSlug(p.slug);
    setTitle(p.title);
    setBodyHtml(p.body_html);
    setEditor(p);
  }

  async function save() {
    setBusy(true);
    try {
      if (editor) {
        await fetch(`/api/v1/orgs/${orgId}/pages/${editor.id}`, {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${getToken()}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ slug, title, body_html: bodyHtml }),
        });
        setEditor(null);
      } else {
        await fetch(`/api/v1/orgs/${orgId}/pages`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getToken()}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            slug,
            title,
            body_html: bodyHtml,
            published: false,
          }),
        });
        setCreateOpen(false);
      }
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function togglePublish(p: LandingPage) {
    await fetch(`/api/v1/orgs/${orgId}/pages/${p.id}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${getToken()}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ published: !p.published }),
    });
    await load();
  }

  async function remove(p: LandingPage) {
    if (!confirm(`Delete page "${p.title}"?`)) return;
    await fetch(`/api/v1/orgs/${orgId}/pages/${p.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    await load();
  }

  const open = createOpen || editor !== null;

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Theme H1"
        title="Landing pages"
        description="Minimal HTML-body landing pages tied to this organization. Public render is a follow-up."
        actions={
          <DkButton onClick={startCreate}>
            <Plus className="h-4 w-4" />
            New page
          </DkButton>
        }
      />

      {loading ? (
        <DkSkeleton className="h-24 w-full" />
      ) : pages.length === 0 ? (
        <DkEmptyState
          icon={<FileText className="h-6 w-6" />}
          title="No landing pages yet"
          description="Start with a launch page, a thank-you page, or a webinar registration form."
          actions={<DkButton onClick={startCreate}>Create the first page</DkButton>}
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {pages.map((p) => (
            <DkCard key={p.id}>
              <DkCardContent className="flex flex-col gap-2 py-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold leading-tight">
                      {p.title}
                    </p>
                    <p className="font-mono text-xs text-[var(--dk-fg-2)]">
                      /p/{p.slug}
                    </p>
                  </div>
                  <DkBadge tone={p.published ? "success" : "neutral"}>
                    {p.published ? "published" : "draft"}
                  </DkBadge>
                </div>
                <div className="flex items-center gap-1.5 pt-2">
                  <DkButton
                    size="sm"
                    variant="secondary"
                    onClick={() => startEdit(p)}
                  >
                    Edit
                  </DkButton>
                  <DkButton
                    size="sm"
                    variant="secondary"
                    onClick={() => togglePublish(p)}
                  >
                    {p.published ? "Unpublish" : "Publish"}
                  </DkButton>
                  <button
                    type="button"
                    onClick={() => remove(p)}
                    className="ml-auto rounded p-1.5 text-[var(--dk-fg-2)] hover:bg-[var(--dk-danger-bg)] hover:text-[var(--dk-danger)]"
                    aria-label="Delete page"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </DkCardContent>
            </DkCard>
          ))}
        </div>
      )}

      <DkDialog
        open={open}
        onClose={() => {
          if (!busy) {
            setEditor(null);
            setCreateOpen(false);
          }
        }}
        size="xl"
      >
        <DkDialogHeader
          title={editor ? "Edit page" : "New page"}
          onClose={() => {
            setEditor(null);
            setCreateOpen(false);
          }}
        />
        <DkDialogContent className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <DkLabel htmlFor="lp-slug" required>
                Slug
              </DkLabel>
              <DkInput
                id="lp-slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="launch-special"
              />
            </div>
            <div>
              <DkLabel htmlFor="lp-title" required>
                Title
              </DkLabel>
              <DkInput
                id="lp-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
          </div>
          <div>
            <DkLabel htmlFor="lp-body">HTML body</DkLabel>
            <DkTextarea
              id="lp-body"
              value={bodyHtml}
              onChange={(e) => setBodyHtml(e.target.value)}
              rows={14}
              className="font-mono text-xs"
            />
          </div>
          <div className="rounded-md border border-[var(--dk-border)] bg-white p-4 max-h-[260px] overflow-auto">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--dk-fg-2)] pb-2">
              Preview
            </p>
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: bodyHtml }}
            />
          </div>
        </DkDialogContent>
        <DkDialogFooter>
          <DkButton
            variant="secondary"
            onClick={() => {
              setEditor(null);
              setCreateOpen(false);
            }}
            disabled={busy}
          >
            Cancel
          </DkButton>
          <DkButton onClick={save} disabled={!slug || !title || busy}>
            Save
          </DkButton>
        </DkDialogFooter>
      </DkDialog>
    </div>
  );
}
