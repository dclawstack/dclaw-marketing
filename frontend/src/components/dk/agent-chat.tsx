"use client";

import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, Send, Sparkles } from "lucide-react";

import { DkAvatar, DkButton, DkCard, DkCardContent, DkSkeleton, DkTextarea } from "./index";
import {
  AgentKind,
  AgentMessage,
  AgentThread,
  createAgentThread,
  listAgentMessages,
  listAgentThreads,
  postAgentMessage,
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
    placeholder: "Ask the Conductor anything…",
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
  const scrollRef = useRef<HTMLDivElement>(null);

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
      setMessages(await listAgentMessages(currentOrg.id, t.id));
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
  }, [messages]);

  async function send(promptOverride?: string) {
    const text = (promptOverride ?? input).trim();
    if (!text || !currentOrg || !thread) return;
    setSending(true);
    setError(null);
    try {
      const next = await postAgentMessage(currentOrg.id, thread.id, text);
      setMessages((prev) => [...prev, ...next]);
      setInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed.");
    } finally {
      setSending(false);
    }
  }

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

      <DkCard className={cn("flex flex-col h-[60vh] min-h-[400px]", className)}>
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
                userName={user?.full_name ?? user?.email ?? "you"}
                onSuggestionClick={(s) => {
                  if (s.prompt) void send(s.prompt);
                }}
              />
            ))
          )}
        </div>
        <div className="border-t border-[var(--dk-border)] p-3 flex gap-2 bg-white">
          <DkTextarea
            rows={2}
            placeholder={placeholder ?? defaults.placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
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
            disabled={!input.trim() || sending}
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
        Press ⌘/Ctrl-Enter to send.
      </p>
    </div>
  );
}

function MessageBubble({
  message,
  userName,
  onSuggestionClick,
}: {
  message: AgentMessage;
  userName: string;
  onSuggestionClick: (s: Suggestion) => void;
}) {
  const isUser = message.role === "user";
  const suggestions = (message.metadata_json?.suggestions ??
    []) as Suggestion[];

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
