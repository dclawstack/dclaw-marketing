"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  Heart,
  KeyRound,
  Link2,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";

import {
  DkAvatar,
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
  DkSelect,
  DkSkeleton,
} from "@/components/dk";
import {
  SocialAccount,
  SocialAccountStatus,
  SocialPlatform,
  createSocialAccount,
  healthCheckSocialAccount,
  listSocialAccounts,
  revokeSocialAccount,
  setSocialAccountDefault,
} from "@/lib/api";
import { useOrg } from "@/contexts/org-context";
import { cn } from "@/lib/utils";

const PLATFORMS: { value: SocialPlatform; label: string }[] = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "x", label: "X / Twitter" },
  { value: "instagram", label: "Instagram" },
  { value: "threads", label: "Threads" },
  { value: "bluesky", label: "Bluesky" },
  { value: "facebook", label: "Facebook" },
  { value: "youtube", label: "YouTube" },
  { value: "tiktok", label: "TikTok" },
  { value: "newsletter", label: "Newsletter" },
  { value: "blog", label: "Blog" },
  { value: "reddit", label: "Reddit" },
  { value: "pinterest", label: "Pinterest" },
  { value: "mastodon", label: "Mastodon" },
  { value: "snapchat", label: "Snapchat" },
  { value: "telegram", label: "Telegram" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "discord", label: "Discord" },
  { value: "quora", label: "Quora" },
  { value: "medium", label: "Medium" },
  { value: "substack", label: "Substack" },
  { value: "beehiiv", label: "Beehiiv" },
  { value: "ghost", label: "Ghost" },
  { value: "wordpress", label: "WordPress" },
  { value: "webflow", label: "Webflow" },
  { value: "spotify_podcasters", label: "Spotify for Podcasters" },
];

const STATUS_TONE: Record<
  SocialAccountStatus,
  "success" | "warning" | "neutral"
> = {
  active: "success",
  reauth_required: "warning",
  revoked: "neutral",
};

export default function ChannelsPage() {
  const { currentOrg } = useOrg();
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const refresh = useCallback(async () => {
    if (!currentOrg) {
      setAccounts([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setAccounts(await listSocialAccounts(currentOrg.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [currentOrg]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function setDefault(a: SocialAccount) {
    if (!currentOrg) return;
    setBusy(a.id);
    try {
      await setSocialAccountDefault(currentOrg.id, a.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Set-default failed.");
    } finally {
      setBusy(null);
    }
  }

  async function probe(a: SocialAccount) {
    if (!currentOrg) return;
    setBusy(a.id);
    try {
      await healthCheckSocialAccount(currentOrg.id, a.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Health-check failed.");
    } finally {
      setBusy(null);
    }
  }

  async function revoke(a: SocialAccount) {
    if (!currentOrg) return;
    if (!confirm(`Revoke ${a.platform} account ${a.handle}?`)) return;
    setBusy(a.id);
    try {
      await revokeSocialAccount(currentOrg.id, a.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Revoke failed.");
    } finally {
      setBusy(null);
    }
  }

  const byPlatform = useMemo(() => {
    const m = new Map<SocialPlatform, SocialAccount[]>();
    for (const a of accounts) {
      const arr = m.get(a.platform) ?? [];
      arr.push(a);
      m.set(a.platform, arr);
    }
    return m;
  }, [accounts]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow={currentOrg ? `Workspace · ${currentOrg.name}` : "Workspace"}
        title="Connected Channels"
        description="Every social account, newsletter, and CMS endpoint we publish through. Multi-account per platform is supported (e.g. two LinkedIn pages). Designate a default per platform that the calendar dispatcher picks when no override is set."
        actions={
          <DkButton onClick={() => setCreateOpen(true)} disabled={!currentOrg}>
            <Plus className="h-4 w-4" />
            Connect Account
          </DkButton>
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
          icon={<Link2 className="h-6 w-6" />}
          title="Pick an organization"
          description="Channels are org-scoped — use the switcher in the nav to choose one."
        />
      ) : loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <DkSkeleton key={i} className="h-32" />
          ))}
        </div>
      ) : accounts.length === 0 ? (
        <DkEmptyState
          icon={<Link2 className="h-6 w-6" />}
          title="No channels connected yet"
          description="Connect at least one to start scheduling posts. Phase 5 ships manual-add (paste an access token) first; per-platform OAuth flows land in follow-ups."
          actions={
            <DkButton onClick={() => setCreateOpen(true)} withArrow>
              Connect Your First Channel
            </DkButton>
          }
        />
      ) : (
        <div className="flex flex-col gap-6">
          {Array.from(byPlatform.entries()).map(([platform, list]) => {
            const label =
              PLATFORMS.find((p) => p.value === platform)?.label ?? platform;
            return (
              <div key={platform} className="flex flex-col gap-3">
                <h2 className="font-display text-lg font-semibold text-ink capitalize">
                  {label}
                  <span className="ml-2 text-sm font-normal text-[var(--dk-fg-2)]">
                    ({list.length} account{list.length === 1 ? "" : "s"})
                  </span>
                </h2>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {list.map((a) => (
                    <DkCard
                      key={a.id}
                      hover
                      className={cn(
                        "h-full flex flex-col",
                        a.status === "revoked" && "opacity-60",
                      )}
                    >
                      <DkCardContent className="flex flex-col gap-3 py-4">
                        <div className="flex items-center gap-3">
                          <DkAvatar
                            size="md"
                            name={a.display_name ?? a.handle}
                            src={a.avatar_url ?? undefined}
                          />
                          <div className="flex flex-col flex-1 min-w-0">
                            <p
                              className="font-medium text-ink truncate"
                              title={a.display_name ?? a.handle}
                            >
                              {a.display_name ?? a.handle}
                            </p>
                            <p className="text-xs text-[var(--dk-fg-2)] font-mono truncate">
                              {a.handle}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center flex-wrap gap-1.5">
                          <DkBadge tone={STATUS_TONE[a.status]}>
                            {a.status === "reauth_required" && (
                              <AlertCircle className="h-3 w-3" />
                            )}
                            {a.status}
                          </DkBadge>
                          {a.is_default_for_platform && (
                            <DkBadge tone="brand">
                              <Check className="h-3 w-3" />
                              default
                            </DkBadge>
                          )}
                          {a.has_token ? (
                            <DkBadge tone="info">token</DkBadge>
                          ) : (
                            <DkBadge tone="warning">no token</DkBadge>
                          )}
                        </div>
                        {a.last_error_message && (
                          <p className="text-xs text-[var(--dk-danger)] line-clamp-2">
                            {a.last_error_message}
                          </p>
                        )}
                      </DkCardContent>
                      <div className="px-4 pb-4 flex items-center gap-1.5 flex-wrap">
                        {!a.is_default_for_platform &&
                          a.status === "active" && (
                            <DkButton
                              size="sm"
                              variant="secondary"
                              onClick={() => setDefault(a)}
                              loading={busy === a.id}
                            >
                              Set Default
                            </DkButton>
                          )}
                        <DkButton
                          size="sm"
                          variant="ghost"
                          onClick={() => probe(a)}
                          loading={busy === a.id}
                          aria-label="Health check"
                          className="px-2"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                        </DkButton>
                        {a.status !== "revoked" && (
                          <DkButton
                            size="sm"
                            variant="ghost"
                            onClick={() => revoke(a)}
                            loading={busy === a.id}
                            aria-label="Revoke"
                            className="px-2 text-[var(--dk-danger)] hover:text-[var(--dk-danger)]"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </DkButton>
                        )}
                      </div>
                    </DkCard>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {currentOrg && (
        <ConnectDialog
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false);
            void refresh();
          }}
          orgId={currentOrg.id}
        />
      )}
    </div>
  );
}

function ConnectDialog({
  open,
  onClose,
  onCreated,
  orgId,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  orgId: string;
}) {
  const [platform, setPlatform] = useState<SocialPlatform>("linkedin");
  const [handle, setHandle] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [token, setToken] = useState("");
  const [setDefault, setSetDefault] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      await createSocialAccount(orgId, {
        platform,
        handle: handle.startsWith("@") ? handle : `@${handle}`,
        display_name: displayName || undefined,
        interim_access_token: token || undefined,
        is_default_for_platform: setDefault,
      });
      onCreated();
      setHandle("");
      setDisplayName("");
      setToken("");
      setSetDefault(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connect failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <DkDialog open={open} onClose={onClose} size="md">
      <DkDialogHeader
        title="Connect Channel"
        description="Manual connection (Phase 5). Paste an access token from the platform's developer console. Per-platform OAuth flows land in follow-up PRs — once those ship, this form falls back to a Connect via OAuth button per platform."
        onClose={onClose}
      />
      <DkDialogContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <DkLabel htmlFor="platform" required>
            Platform
          </DkLabel>
          <DkSelect
            id="platform"
            value={platform}
            onChange={(e) => setPlatform(e.target.value as SocialPlatform)}
          >
            {PLATFORMS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </DkSelect>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <DkLabel htmlFor="handle" required>
              Handle
            </DkLabel>
            <DkInput
              id="handle"
              placeholder="@acme_official"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <DkLabel htmlFor="dn">Display name</DkLabel>
            <DkInput
              id="dn"
              placeholder="Acme Inc — Official"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <DkLabel
            htmlFor="token"
            description="Stored in the database; will be migrated to encrypted Connection rows in Phase 6 (MCP secret store)."
          >
            <KeyRound className="inline h-3.5 w-3.5 mr-1 align-text-bottom" />
            Access token (optional)
          </DkLabel>
          <DkInput
            id="token"
            type="password"
            placeholder="••••••••"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-2.5 cursor-pointer pt-1">
          <input
            type="checkbox"
            checked={setDefault}
            onChange={(e) => setSetDefault(e.target.checked)}
            className="accent-[var(--dk-purple-700)]"
          />
          <span className="text-sm text-ink">
            <Heart className="inline h-3.5 w-3.5 mr-1 align-text-bottom text-brand" />
            Set as default for this platform
          </span>
        </label>
        {error && (
          <div
            role="alert"
            className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
          >
            {error}
          </div>
        )}
      </DkDialogContent>
      <DkDialogFooter>
        <DkButton variant="secondary" onClick={onClose}>
          Cancel
        </DkButton>
        <DkButton
          onClick={handleSubmit}
          loading={submitting}
          disabled={!handle || submitting}
        >
          Connect
        </DkButton>
      </DkDialogFooter>
    </DkDialog>
  );
}
