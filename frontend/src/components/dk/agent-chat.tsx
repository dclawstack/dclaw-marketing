"use client";

import * as React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  File as FileIcon,
  Folder,
  Image as ImageIcon,
  Loader2,
  Paperclip,
  Send,
  Sparkles,
  X,
} from "lucide-react";

import { DkAvatar, DkButton, DkCard, DkCardContent, DkSkeleton, DkTextarea } from "./index";
import {
  AgentKind,
  AgentMessage,
  AgentThread,
  Asset,
  createAgentThread,
  getAssetDownloadUrl,
  listAgentMessages,
  listAgentThreads,
  listAssets,
  postAgentMessage,
  uploadFileToAsset,
} from "@/lib/api";
import { useOrg } from "@/contexts/org-context";
import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";

interface Suggestion {
  label: string;
  prompt?: string;
  href?: string;
}

export interface DkAgentChatProps {
  /** Which agent kind to converse with — drives thread find-or-create. */
  kind: AgentKind;
  /** Placeholder + empty-state copy tailored to the agent role. */
  placeholder?: string;
  emptyTitle?: string;
  emptySubtitle?: string;
  /** Optional: max chat-area height. Default 60vh / 400px min. */
  className?: string;
}

const DEFAULT_BY_KIND: Record<
  AgentKind,
  { placeholder: string; emptyTitle: string; emptySubtitle: string }
> = {
  conductor: {
    placeholder: "Ask the Conductor anything — or drop files / paste images…",
    emptyTitle: "Conductor is ready.",
    emptySubtitle:
      "Start by typing a goal — the Conductor decomposes it into work for the role agents.",
  },
  smm: {
    placeholder: "Hand me a calendar / DM task…",
    emptyTitle: "SMM Agent is ready.",
    emptySubtitle:
      "Ask me to draft posts, schedule a thread, or reply to DMs in your brand voice.",
  },
  seo: {
    placeholder: "Hand me an SEO task…",
    emptyTitle: "SEO Specialist is ready.",
    emptySubtitle:
      "I can plan keyword pipelines, build topic clusters, and draft long-form posts.",
  },
  paid_media: {
    placeholder: "Hand me an ad task…",
    emptyTitle: "Paid Media Specialist is ready.",
    emptySubtitle:
      "I can draft ad creative, propose A/B splits, and rebalance budgets within your caps.",
  },
  analyst: {
    placeholder: "Ask for an analysis…",
    emptyTitle: "Analyst Agent is ready.",
    emptySubtitle:
      "I can produce daily rollups, detect anomalies, and draft your Monday-morning narrative.",
  },
  creatives: {
    placeholder: "Send the Creatives Agent a brief…",
    emptyTitle: "Creatives Agent is ready.",
    emptySubtitle: "Hand me a brief and I'll draft variants for your inbox.",
  },
  inbox: {
    placeholder: "Send the Inbox Agent a request…",
    emptyTitle: "Inbox Agent is ready.",
    emptySubtitle: "I draft replies to DMs in your brand voice.",
  },
};

/** Local placeholder for an in-flight upload — has a temp id until the
 *  server returns the real Asset. */
interface PendingUpload {
  tempId: string;
  file: File;
  previewUrl?: string;
  error?: string;
}

export function DkAgentChat({
  kind,
  placeholder,
  emptyTitle,
  emptySubtitle,
  className,
}: DkAgentChatProps) {
  const { currentOrg } = useOrg();
  const { user } = useAuth();
  const [thread, setThread] = useState<AgentThread | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Attachments (S5-CDR-B)
  const [attached, setAttached] = useState<Asset[]>([]);
  const [pending, setPending] = useState<PendingUpload[]>([]);
  const [assetMap, setAssetMap] = useState<Record<string, Asset>>({});
  const [dragOver, setDragOver] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const defaults = DEFAULT_BY_KIND[kind];

  const refresh = useCallback(async () => {
    if (!currentOrg) {
      setMessages([]);
      setThread(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const threads = await listAgentThreads(currentOrg.id);
      let t = threads.find((th) => th.kind === kind);
      if (!t) t = await createAgentThread(currentOrg.id, { kind });
      setThread(t);
      const [msgs, assets] = await Promise.all([
        listAgentMessages(currentOrg.id, t.id),
        listAssets(currentOrg.id).catch(() => [] as Asset[]),
      ]);
      setMessages(msgs);
      setAssetMap(Object.fromEntries(assets.map((a) => [a.id, a])));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [currentOrg, kind]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, pending.length, attached.length]);

  // ---- Upload pipeline -----------------------------------------------------
  const startUploads = useCallback(
    async (files: File[]) => {
      if (!currentOrg || files.length === 0) return;
      const newPending: PendingUpload[] = files.map((f) => ({
        tempId: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        file: f,
        previewUrl: f.type.startsWith("image/")
          ? URL.createObjectURL(f)
          : undefined,
      }));
      setPending((prev) => [...prev, ...newPending]);

      await Promise.all(
        newPending.map(async (p) => {
          try {
            const asset = await uploadFileToAsset(p.file, currentOrg.id);
            setAssetMap((m) => ({ ...m, [asset.id]: asset }));
            setAttached((prev) => [...prev, asset]);
          } catch (err) {
            setPending((prev) =>
              prev.map((q) =>
                q.tempId === p.tempId
                  ? { ...q, error: err instanceof Error ? err.message : "Upload failed" }
                  : q,
              ),
            );
            return;
          }
          // Successful upload — remove from pending.
          setPending((prev) => prev.filter((q) => q.tempId !== p.tempId));
        }),
      );
    },
    [currentOrg],
  );

  const removeAttached = useCallback((id: string) => {
    setAttached((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const removePending = useCallback((tempId: string) => {
    setPending((prev) => {
      const target = prev.find((p) => p.tempId === tempId);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((p) => p.tempId !== tempId);
    });
  }, []);

  // ---- Drag / paste handlers ----------------------------------------------
  const collectFilesFromDataTransfer = (dt: DataTransfer): File[] => {
    // Prefer `items` (supports folder traversal in webkit-dropdownEvent)
    if (dt.items && dt.items.length > 0) {
      const out: File[] = [];
      for (let i = 0; i < dt.items.length; i++) {
        const it = dt.items[i];
        if (it.kind === "file") {
          const f = it.getAsFile();
          if (f) out.push(f);
        }
      }
      if (out.length) return out;
    }
    return Array.from(dt.files || []);
  };

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const files = collectFilesFromDataTransfer(e.dataTransfer);
      void startUploads(files);
    },
    [startUploads],
  );

  const onPaste = useCallback(
    (e: React.ClipboardEvent) => {
      const files: File[] = [];
      for (const item of Array.from(e.clipboardData.items)) {
        if (item.kind === "file") {
          const f = item.getAsFile();
          if (f) files.push(f);
        }
      }
      if (files.length) {
        e.preventDefault();
        void startUploads(files);
      }
    },
    [startUploads],
  );

  // ---- Send ----------------------------------------------------------------
  async function send(promptOverride?: string) {
    const text = (promptOverride ?? input).trim();
    if ((!text && attached.length === 0) || !currentOrg || !thread) return;
    setSending(true);
    setError(null);
    try {
      const ids = attached.map((a) => a.id);
      const next = await postAgentMessage(
        currentOrg.id,
        thread.id,
        text || "(see attachments)",
        ids,
      );
      setMessages((prev) => [...prev, ...next]);
      setInput("");
      setAttached([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed.");
    } finally {
      setSending(false);
    }
  }

  const placeholderText = placeholder ?? defaults.placeholder;
  const isUploading = pending.some((p) => !p.error);
  const allAttachmentsForRender = useMemo(
    () => ({ attached, pending }),
    [attached, pending],
  );

  return (
    <div className="flex flex-col gap-3 max-w-3xl">
      {error && (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      )}

      <DkCard
        className={cn(
          "flex flex-col h-[60vh] min-h-[400px] relative",
          dragOver && "ring-2 ring-brand ring-offset-2",
          className,
        )}
        onDragOver={(e) => {
          e.preventDefault();
          if (!dragOver) setDragOver(true);
        }}
        onDragLeave={(e) => {
          // Avoid flicker on child elements
          if (e.currentTarget === e.target) setDragOver(false);
        }}
        onDrop={onDrop}
      >
        {dragOver && (
          <div
            className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-2xl bg-[var(--dk-purple-50)]/80 text-brand font-display text-lg font-semibold"
            aria-hidden="true"
          >
            Drop files or folders to attach
          </div>
        )}

        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-6 flex flex-col gap-4"
        >
          {loading ? (
            <DkSkeleton className="h-24" />
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center gap-4 py-12">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--dk-purple-50)] text-brand">
                <Sparkles className="h-6 w-6" />
              </div>
              <p className="font-display text-lg font-semibold text-ink">
                {emptyTitle ?? defaults.emptyTitle}
              </p>
              <p className="text-sm text-[var(--dk-fg-2)] max-w-md">
                {emptySubtitle ?? defaults.emptySubtitle}
              </p>
            </div>
          ) : (
            messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                assetMap={assetMap}
                userName={user?.full_name ?? user?.email ?? "you"}
                onSuggestionClick={(s) => {
                  if (s.prompt) void send(s.prompt);
                }}
              />
            ))
          )}
        </div>

        {/* Attachment strip — visible only when there's something to show */}
        {(allAttachmentsForRender.attached.length > 0 || pending.length > 0) && (
          <div className="border-t border-[var(--dk-border)] bg-[var(--dk-bg-tint)] px-3 py-2 flex flex-wrap gap-2">
            {pending.map((p) => (
              <PendingChip
                key={p.tempId}
                pending={p}
                onRemove={() => removePending(p.tempId)}
              />
            ))}
            {attached.map((a) => (
              <AttachmentChip
                key={a.id}
                asset={a}
                onRemove={() => removeAttached(a.id)}
              />
            ))}
          </div>
        )}

        <div className="border-t border-[var(--dk-border)] p-3 flex gap-2 bg-white">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              const files = e.target.files ? Array.from(e.target.files) : [];
              if (files.length) void startUploads(files);
              if (fileInputRef.current) fileInputRef.current.value = "";
            }}
          />
          <input
            ref={folderInputRef}
            type="file"
            multiple
            className="hidden"
            // @ts-expect-error — webkitdirectory is a non-standard but
            // widely supported attribute (Chrome / Edge / Safari).
            webkitdirectory=""
            directory=""
            onChange={(e) => {
              const files = e.target.files ? Array.from(e.target.files) : [];
              if (files.length) void startUploads(files);
              if (folderInputRef.current) folderInputRef.current.value = "";
            }}
          />

          <div className="flex flex-col gap-1 self-end">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="rounded-md p-2 text-[var(--dk-fg-2)] hover:bg-[var(--dk-gray-50)] hover:text-ink transition-colors"
              aria-label="Attach files"
              title="Attach files"
              disabled={sending}
            >
              <Paperclip className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => folderInputRef.current?.click()}
              className="rounded-md p-2 text-[var(--dk-fg-2)] hover:bg-[var(--dk-gray-50)] hover:text-ink transition-colors"
              aria-label="Attach folder"
              title="Attach folder"
              disabled={sending}
            >
              <Folder className="h-4 w-4" />
            </button>
          </div>

          <DkTextarea
            rows={2}
            placeholder={placeholderText}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPaste={onPaste}
            disabled={sending || loading}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                void send();
              }
            }}
            className="flex-1 resize-none"
          />
          <DkButton
            onClick={() => void send()}
            disabled={
              (!input.trim() && attached.length === 0)
              || sending
              || isUploading
            }
            loading={sending}
            aria-label="Send"
            className="self-end"
          >
            <Send className="h-4 w-4" />
            Send
          </DkButton>
        </div>
      </DkCard>

      <p className="text-xs text-[var(--dk-fg-2)] text-center">
        Press ⌘/Ctrl-Enter to send · drag-drop, paste, or use the paperclip / folder icons to attach.
      </p>
    </div>
  );
}

// ---- Attachment chips ------------------------------------------------------

function PendingChip({
  pending,
  onRemove,
}: {
  pending: PendingUpload;
  onRemove: () => void;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border bg-white px-2 py-1 text-xs",
        pending.error
          ? "border-[var(--dk-danger)] text-[var(--dk-danger)]"
          : "border-[var(--dk-border)] text-[var(--dk-fg-2)]",
      )}
      title={pending.error ?? `Uploading ${pending.file.name}`}
    >
      {pending.error ? (
        <span aria-hidden="true">⚠</span>
      ) : pending.previewUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={pending.previewUrl}
          alt=""
          className="h-6 w-6 rounded object-cover"
        />
      ) : (
        <Loader2 className="h-3 w-3 animate-spin" />
      )}
      <span className="max-w-[14rem] truncate">{pending.file.name}</span>
      <button
        type="button"
        onClick={onRemove}
        className="ml-1 text-[var(--dk-fg-2)] hover:text-ink"
        aria-label="Remove"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

function AttachmentChip({
  asset,
  onRemove,
}: {
  asset: Asset;
  onRemove: () => void;
}) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    if (asset.kind === "image") {
      void getAssetDownloadUrl(asset.id)
        .then((r) => {
          if (!cancelled) setPreviewUrl(r.presigned_get_url);
        })
        .catch(() => {
          /* swallow — chip falls back to icon */
        });
    }
    return () => {
      cancelled = true;
    };
  }, [asset.id, asset.kind]);
  return (
    <div
      className="flex items-center gap-2 rounded-md border border-[var(--dk-border)] bg-white px-2 py-1 text-xs text-[var(--dk-fg-1)]"
      title={asset.original_filename ?? asset.id}
    >
      {previewUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={previewUrl}
          alt=""
          className="h-6 w-6 rounded object-cover"
        />
      ) : asset.kind === "image" ? (
        <ImageIcon className="h-3 w-3" />
      ) : (
        <FileIcon className="h-3 w-3" />
      )}
      <span className="max-w-[14rem] truncate">
        {asset.original_filename ?? `${asset.kind} attachment`}
      </span>
      <button
        type="button"
        onClick={onRemove}
        className="ml-1 text-[var(--dk-fg-2)] hover:text-ink"
        aria-label="Remove"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

// ---- Message bubble --------------------------------------------------------

function MessageBubble({
  message,
  userName,
  assetMap,
  onSuggestionClick,
}: {
  message: AgentMessage;
  userName: string;
  assetMap: Record<string, Asset>;
  onSuggestionClick: (s: Suggestion) => void;
}) {
  const isUser = message.role === "user";
  const suggestions = (message.metadata_json?.suggestions ??
    []) as Suggestion[];
  const attachmentIds = message.attachment_asset_ids ?? [];

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div className="shrink-0">
        {isUser ? (
          <DkAvatar size="sm" name={userName} />
        ) : (
          <div className="flex h-8 w-8 items-center justify-center rounded-pill bg-brand text-white">
            <Sparkles className="h-4 w-4" />
          </div>
        )}
      </div>
      <div
        className={`flex flex-col gap-2 max-w-[80%] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        {attachmentIds.length > 0 && (
          <div
            className={`flex flex-wrap gap-2 ${
              isUser ? "justify-end" : "justify-start"
            }`}
          >
            {attachmentIds.map((id) => (
              <MessageAttachment key={id} assetId={id} asset={assetMap[id]} />
            ))}
          </div>
        )}

        <DkCard
          className={
            isUser ? "bg-brand border-brand" : "bg-[var(--dk-bg-tint)]"
          }
        >
          <DkCardContent className="px-4 py-2.5">
            <p
              className={`whitespace-pre-wrap text-sm leading-relaxed ${
                isUser ? "text-white" : "text-[var(--dk-fg-1)]"
              }`}
            >
              {message.content}
            </p>
          </DkCardContent>
        </DkCard>
        {suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {suggestions.map((s, i) =>
              s.href ? (
                <Link key={i} href={s.href}>
                  <DkButton size="sm" variant="secondary" withArrow>
                    {s.label}
                  </DkButton>
                </Link>
              ) : (
                <button
                  key={i}
                  type="button"
                  onClick={() => onSuggestionClick(s)}
                  className="inline-flex items-center gap-1.5 rounded-pill border border-[var(--dk-border-strong)] bg-white px-3 py-1.5 text-xs font-semibold text-ink hover:border-brand hover:text-brand transition-all duration-fast"
                >
                  {s.label}
                  <ArrowRight className="h-3 w-3" />
                </button>
              ),
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function MessageAttachment({
  assetId,
  asset,
}: {
  assetId: string;
  asset: Asset | undefined;
}) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    if (asset?.kind === "image") {
      void getAssetDownloadUrl(assetId)
        .then((r) => {
          if (!cancelled) setPreviewUrl(r.presigned_get_url);
        })
        .catch(() => {});
    }
    return () => {
      cancelled = true;
    };
  }, [assetId, asset?.kind]);

  if (asset?.kind === "image" && previewUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={previewUrl}
        alt={asset.original_filename ?? "image attachment"}
        className="h-32 w-32 rounded-lg object-cover border border-[var(--dk-border)]"
      />
    );
  }
  return (
    <div className="inline-flex items-center gap-2 rounded-md border border-[var(--dk-border)] bg-white px-2 py-1 text-xs text-[var(--dk-fg-1)]">
      {asset?.kind === "image" ? (
        <ImageIcon className="h-3 w-3" />
      ) : (
        <FileIcon className="h-3 w-3" />
      )}
      <span className="max-w-[14rem] truncate">
        {asset?.original_filename ?? "attachment"}
      </span>
    </div>
  );
}
