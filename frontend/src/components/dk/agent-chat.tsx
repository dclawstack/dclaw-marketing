"use client";

import * as React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Brain,
  Check,
  ChevronDown,
  ChevronRight,
  File as FileIcon,
  Folder,
  Image as ImageIcon,
  Loader2,
  Paperclip,
  Send,
  Sparkles,
  Square,
  Wrench,
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
  streamAgentMessage,
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

  // Streaming state (S5-CDR-D)
  const [streamingText, setStreamingText] = useState("");
  const [streamingThinking, setStreamingThinking] = useState("");
  const [streamingTools, setStreamingTools] = useState<
    { id: string; name: string; input: Record<string, unknown>; result?: Record<string, unknown> }[]
  >([]);
  const [thinkingEnabled, setThinkingEnabled] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Persist thinking-mode preference per browser (server-side persistence
  // is a follow-up — see plan). Read once on mount.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.localStorage.getItem("dclaw:conductor:thinking");
    if (saved === "1") setThinkingEnabled(true);
  }, []);
  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      "dclaw:conductor:thinking",
      thinkingEnabled ? "1" : "0",
    );
  }, [thinkingEnabled]);

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

  // ---- Send (streaming) ----------------------------------------------------
  async function send(promptOverride?: string) {
    const text = (promptOverride ?? input).trim();
    if ((!text && attached.length === 0) || !currentOrg || !thread) return;
    setSending(true);
    setError(null);
    setStreamingText("");
    setStreamingThinking("");
    setStreamingTools([]);

    const optimisticUserContent = text || "(see attachments)";
    const optimisticAttachmentIds = attached.map((a) => a.id);

    // Build & render an optimistic user bubble while waiting for the
    // first server event with the persisted id.
    const optimisticId = `optimistic-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: optimisticId,
        thread_id: thread.id,
        role: "user",
        agent_kind: null,
        content: optimisticUserContent,
        tool_name: null,
        tool_arguments: null,
        tool_result: null,
        attachment_asset_ids: optimisticAttachmentIds.length
          ? optimisticAttachmentIds
          : null,
        metadata_json: null,
        approval_request_id: null,
        created_at: new Date().toISOString(),
      },
    ]);
    setInput("");
    setAttached([]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamAgentMessage(currentOrg.id, thread.id, optimisticUserContent, {
        attachmentAssetIds: optimisticAttachmentIds.length
          ? optimisticAttachmentIds
          : undefined,
        thinkingBudgetTokens: thinkingEnabled ? 4_000 : undefined,
        signal: controller.signal,
        onEvent: (ev) => {
          switch (ev.event) {
            case "user_msg_persisted": {
              const persistedId = ev.data.id;
              setMessages((prev) =>
                prev.map((m) => (m.id === optimisticId ? { ...m, id: persistedId } : m)),
              );
              break;
            }
            case "text_delta":
              setStreamingText((s) => s + ev.data.text);
              break;
            case "thinking_delta":
              setStreamingThinking((s) => s + ev.data.text);
              break;
            case "tool_call_start":
              setStreamingTools((prev) => [
                ...prev,
                {
                  id: ev.data.tool_use_id,
                  name: ev.data.name,
                  input: ev.data.input,
                },
              ]);
              break;
            case "tool_call_result":
              setStreamingTools((prev) =>
                prev.map((t) =>
                  t.id === ev.data.tool_use_id ? { ...t, result: ev.data.result } : t,
                ),
              );
              break;
            case "agent_msg_start":
              // For multi-iteration runs, the next iteration begins —
              // we keep accumulating text/tools into the same UI block.
              break;
            case "error":
              setError(ev.data.error || "Stream error");
              break;
            case "done":
              // Stream complete — pull final canonical rows from server
              // so historical refresh stays consistent (especially for
              // attachment_asset_ids and tool_arguments/results).
              break;
          }
        },
      });
      // Stream closed cleanly — refresh from server to fold in the
      // persisted rows and drop the optimistic streaming state.
      await refresh();
      setStreamingText("");
      setStreamingThinking("");
      setStreamingTools([]);
    } catch (err) {
      if ((err as { name?: string }).name === "AbortError") {
        setError("Stopped.");
      } else {
        setError(err instanceof Error ? err.message : "Stream failed.");
      }
      // Optimistic message stays — refresh to reconcile with server
      // (the user_msg is persisted before streaming begins, so it's
      // still there even after abort).
      await refresh().catch(() => {});
      setStreamingText("");
      setStreamingThinking("");
      setStreamingTools([]);
    } finally {
      abortRef.current = null;
      setSending(false);
    }
  }

  function stopStreaming() {
    abortRef.current?.abort();
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
            <>
              {messages.map((m) =>
                m.role === "tool" ? (
                  <ToolCallCard key={m.id} message={m} />
                ) : (
                  <MessageBubble
                    key={m.id}
                    message={m}
                    assetMap={assetMap}
                    userName={user?.full_name ?? user?.email ?? "you"}
                    onSuggestionClick={(s) => {
                      if (s.prompt) void send(s.prompt);
                    }}
                  />
                ),
              )}
              {/* Streaming-in-flight render (S5-CDR-D) */}
              {sending && (streamingText || streamingThinking || streamingTools.length > 0) && (
                <StreamingPreview
                  text={streamingText}
                  thinking={streamingThinking}
                  tools={streamingTools}
                />
              )}
            </>
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
            <button
              type="button"
              onClick={() => setThinkingEnabled((v) => !v)}
              className={cn(
                "rounded-md p-2 transition-colors",
                thinkingEnabled
                  ? "bg-[var(--dk-purple-50)] text-brand"
                  : "text-[var(--dk-fg-2)] hover:bg-[var(--dk-gray-50)] hover:text-ink",
              )}
              aria-label="Extended thinking"
              aria-pressed={thinkingEnabled}
              title={`Extended thinking: ${thinkingEnabled ? "on" : "off"}`}
              disabled={sending}
            >
              <Brain className="h-4 w-4" />
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
          {sending ? (
            <DkButton
              onClick={stopStreaming}
              aria-label="Stop generation"
              className="self-end"
              variant="secondary"
            >
              <Square className="h-4 w-4" />
              Stop
            </DkButton>
          ) : (
            <DkButton
              onClick={() => void send()}
              disabled={
                (!input.trim() && attached.length === 0) || isUploading
              }
              aria-label="Send"
              className="self-end"
            >
              <Send className="h-4 w-4" />
              Send
            </DkButton>
          )}
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
  const thinking =
    !isUser && typeof message.metadata_json?.thinking === "string"
      ? (message.metadata_json.thinking as string)
      : "";

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

        {thinking && <ThinkingBlock text={thinking} />}

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

// ---- Streaming preview (in-flight rendering, S5-CDR-D) --------------------

function StreamingPreview({
  text,
  thinking,
  tools,
}: {
  text: string;
  thinking: string;
  tools: { id: string; name: string; input: Record<string, unknown>; result?: Record<string, unknown> }[];
}) {
  return (
    <div className="flex gap-3 flex-row">
      <div className="shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-pill bg-brand text-white">
          <Sparkles className="h-4 w-4" />
        </div>
      </div>
      <div className="flex flex-col gap-2 max-w-[80%] items-start w-full">
        {thinking && <ThinkingBlock text={thinking} />}
        {tools.map((t) => (
          <div
            key={t.id}
            className="flex items-center gap-2 rounded-md border border-[var(--dk-border)] bg-white px-3 py-2 w-full"
          >
            {t.result ? (
              <Check className="h-3 w-3 text-[var(--dk-success,#16a34a)]" />
            ) : (
              <Loader2 className="h-3 w-3 animate-spin text-[var(--dk-fg-2)]" />
            )}
            <Wrench className="h-3 w-3 text-brand" />
            <span className="font-mono text-xs font-semibold text-ink">{t.name}</span>
            <span className="text-xs text-[var(--dk-fg-2)] truncate">
              {t.result ? toolResultSummary(t.result) : "running…"}
            </span>
          </div>
        ))}
        {(text || (!thinking && tools.length === 0)) && (
          <DkCard className="bg-[var(--dk-bg-tint)]">
            <DkCardContent className="px-4 py-2.5">
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--dk-fg-1)]">
                {text}
                <span className="inline-block w-1.5 h-3.5 align-[-2px] ml-0.5 bg-brand animate-pulse" />
              </p>
            </DkCardContent>
          </DkCard>
        )}
      </div>
    </div>
  );
}

function ThinkingBlock({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-md border border-dashed border-[var(--dk-border)] bg-[var(--dk-bg-tint)] w-full">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 text-xs text-[var(--dk-fg-2)] hover:text-ink w-full text-left"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <Brain className="h-3 w-3" />
        <span className="font-semibold">Thinking…</span>
        {!open && (
          <span className="truncate text-[var(--dk-fg-muted)]">
            {text.slice(0, 80)}
            {text.length > 80 ? "…" : ""}
          </span>
        )}
      </button>
      {open && (
        <pre className="px-3 pb-3 text-xs whitespace-pre-wrap break-words font-sans text-[var(--dk-fg-2)] max-h-64 overflow-y-auto">
          {text}
        </pre>
      )}
    </div>
  );
}

// ---- Tool-call card -------------------------------------------------------

function ToolCallCard({ message }: { message: AgentMessage }) {
  const [open, setOpen] = useState(false);
  const result = (message.tool_result ?? {}) as Record<string, unknown>;
  const args = (message.tool_arguments ?? {}) as Record<string, unknown>;
  const ok = result.ok !== false;
  const action = result.action as string | undefined;
  const route = result.route as string | undefined;
  return (
    <div className="flex gap-3">
      <div className="shrink-0">
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-pill text-white",
            ok ? "bg-[var(--dk-success,#16a34a)]" : "bg-[var(--dk-danger,#dc2626)]",
          )}
          aria-label={ok ? "Tool succeeded" : "Tool failed"}
        >
          {ok ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
        </div>
      </div>
      <div className="flex-1 max-w-[80%]">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2 rounded-md border border-[var(--dk-border)] bg-white px-3 py-2 text-left w-full hover:border-brand transition-colors"
        >
          {open ? (
            <ChevronDown className="h-3 w-3 text-[var(--dk-fg-2)]" />
          ) : (
            <ChevronRight className="h-3 w-3 text-[var(--dk-fg-2)]" />
          )}
          <Wrench className="h-3 w-3 text-brand" />
          <span className="font-mono text-xs font-semibold text-ink">
            {message.tool_name || "(unknown tool)"}
          </span>
          <span className="text-xs text-[var(--dk-fg-2)] ml-1 truncate">
            {ok ? toolResultSummary(result) : `failed: ${result.error ?? "unknown error"}`}
          </span>
          {action === "navigate" && route && (
            <Link
              href={route}
              onClick={(e) => e.stopPropagation()}
              className="ml-auto inline-flex items-center gap-1 rounded-pill border border-brand px-2 py-0.5 text-xs font-semibold text-brand hover:bg-[var(--dk-purple-50)]"
            >
              Open {route}
              <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </button>
        {open && (
          <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div className="rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] p-2">
              <div className="text-xs font-semibold text-[var(--dk-fg-2)] mb-1">Args</div>
              <pre className="text-xs overflow-x-auto whitespace-pre-wrap break-words font-mono">
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
            <div className="rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] p-2">
              <div className="text-xs font-semibold text-[var(--dk-fg-2)] mb-1">Result</div>
              <pre className="text-xs overflow-x-auto whitespace-pre-wrap break-words font-mono">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function toolResultSummary(result: Record<string, unknown>): string {
  if (typeof result.message === "string") return result.message;
  if (typeof result.count === "number") return `${result.count} item(s)`;
  if (result.queued_for_approval) return "queued for approval";
  if (result.queued) return "queued";
  if (result.action === "navigate" && typeof result.route === "string") {
    return `navigate → ${result.route}`;
  }
  if (result.ok) return "ok";
  return "";
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
