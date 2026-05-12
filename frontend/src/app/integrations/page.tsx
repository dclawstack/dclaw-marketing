"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  ExternalLink,
  KeyRound,
  Plug,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";

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
} from "@/components/dk";
import {
  Connection,
  ConnectionStatus,
  IntegrationCatalogEntry,
  IntegrationCategory,
  createConnection,
  getIntegrationRegistry,
  healthCheckConnection,
  listConnections,
  revokeConnection,
} from "@/lib/api";
import { useOrg } from "@/contexts/org-context";
import { cn } from "@/lib/utils";

const CATEGORY_LABEL: Record<IntegrationCategory, string> = {
  social: "Social",
  generation: "AI · Generation",
  dam: "Design · DAM",
  hosting: "Hosting",
  crm: "CRM",
  analytics: "Analytics",
  cms: "CMS",
  email: "Email",
  ads: "Ads",
  productivity: "Productivity",
};

const CATEGORY_ORDER: IntegrationCategory[] = [
  "social",
  "generation",
  "crm",
  "email",
  "ads",
  "analytics",
  "cms",
  "dam",
  "hosting",
  "productivity",
];

const STATUS_TONE: Record<
  ConnectionStatus,
  "success" | "warning" | "neutral" | "danger"
> = {
  active: "success",
  reauth_required: "warning",
  revoked: "neutral",
  error: "danger",
};

export default function IntegrationsPage() {
  const { currentOrg } = useOrg();
  const [registry, setRegistry] = useState<IntegrationCatalogEntry[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [connectFor, setConnectFor] =
    useState<IntegrationCatalogEntry | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reg, cons] = await Promise.all([
        getIntegrationRegistry(),
        currentOrg
          ? listConnections(currentOrg.id)
          : Promise.resolve([] as Connection[]),
      ]);
      setRegistry(reg);
      setConnections(cons);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [currentOrg]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const byServer = useMemo(() => {
    const m = new Map<string, Connection[]>();
    for (const c of connections) {
      const arr = m.get(c.server_id) ?? [];
      arr.push(c);
      m.set(c.server_id, arr);
    }
    return m;
  }, [connections]);

  const grouped = useMemo(() => {
    const m = new Map<IntegrationCategory, IntegrationCatalogEntry[]>();
    for (const e of registry) {
      const arr = m.get(e.category as IntegrationCategory) ?? [];
      arr.push(e);
      m.set(e.category as IntegrationCategory, arr);
    }
    return m;
  }, [registry]);

  async function probe(conn: Connection) {
    if (!currentOrg) return;
    setBusy(conn.id);
    try {
      await healthCheckConnection(currentOrg.id, conn.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Health-check failed.");
    } finally {
      setBusy(null);
    }
  }

  async function revoke(conn: Connection) {
    if (!currentOrg) return;
    if (!confirm(`Revoke connection "${conn.name}" to ${conn.server_id}?`))
      return;
    setBusy(conn.id);
    try {
      await revokeConnection(currentOrg.id, conn.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Revoke failed.");
    } finally {
      setBusy(null);
    }
  }

  const connectedCount = connections.filter((c) => c.status === "active").length;

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Workspace · Theme D"
        title="Integrations"
        description="Every external system the agents can call. Each integration is an MCP server with a uniform tool surface. Secrets are encrypted at rest with Fernet keyed off a per-Org data key (Phase 6.x); raw tokens are never returned."
        actions={
          currentOrg && (
            <DkBadge tone="brand">
              {connectedCount} connected · {registry.length} available
            </DkBadge>
          )
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

      {!currentOrg && (
        <DkEmptyState
          icon={<Plug className="h-6 w-6" />}
          title="Pick an organization"
          description="Connections are org-scoped — use the switcher in the nav."
        />
      )}

      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <DkSkeleton key={i} className="h-32" />
          ))}
        </div>
      ) : (
        currentOrg &&
        CATEGORY_ORDER.map((cat) => {
          const entries = grouped.get(cat);
          if (!entries || entries.length === 0) return null;
          return (
            <section key={cat} className="flex flex-col gap-3">
              <h2 className="font-display text-lg font-semibold text-ink">
                {CATEGORY_LABEL[cat]}
                <span className="ml-2 text-sm font-normal text-[var(--dk-fg-2)]">
                  ({entries.length})
                </span>
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {entries.map((e) => {
                  const conns = byServer.get(e.server_id) ?? [];
                  const active = conns.filter(
                    (c) => c.status === "active",
                  ).length;
                  return (
                    <DkCard
                      key={e.server_id}
                      hover
                      className={cn(
                        "h-full flex flex-col",
                        active > 0 && "border-brand",
                      )}
                    >
                      <DkCardContent className="flex flex-col gap-3 py-4">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex flex-col">
                            <p className="font-semibold text-ink text-sm">
                              {e.name}
                            </p>
                            <p className="text-xs text-[var(--dk-fg-2)] font-mono">
                              {e.server_id}
                            </p>
                          </div>
                          {active > 0 ? (
                            <DkBadge tone="success">
                              <Check className="h-3 w-3" />
                              {active} connected
                            </DkBadge>
                          ) : (
                            <DkBadge tone="neutral">{e.auth}</DkBadge>
                          )}
                        </div>
                        <p className="text-xs text-[var(--dk-fg-1)] leading-relaxed line-clamp-2">
                          {e.description}
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {e.tools.slice(0, 3).map((t) => (
                            <span
                              key={t}
                              className="text-[10px] font-mono rounded-md bg-[var(--dk-gray-100)] px-1.5 py-0.5 text-[var(--dk-fg-2)]"
                            >
                              {t}
                            </span>
                          ))}
                          {e.tools.length > 3 && (
                            <span className="text-[10px] text-[var(--dk-fg-muted)]">
                              +{e.tools.length - 3} more
                            </span>
                          )}
                        </div>
                      </DkCardContent>

                      {/* per-connection rows when any exist */}
                      {conns.length > 0 && (
                        <div className="border-t border-[var(--dk-border)] px-4 py-2 flex flex-col gap-1.5">
                          {conns.map((c) => (
                            <div
                              key={c.id}
                              className="flex items-center justify-between gap-2 text-xs"
                            >
                              <span className="font-medium text-ink truncate">
                                {c.name}
                              </span>
                              <div className="flex items-center gap-1">
                                <DkBadge
                                  tone={STATUS_TONE[c.status]}
                                  className="text-[10px]"
                                >
                                  {c.status === "reauth_required" && (
                                    <AlertCircle className="h-2.5 w-2.5" />
                                  )}
                                  {c.status}
                                </DkBadge>
                                <button
                                  onClick={() => probe(c)}
                                  disabled={busy === c.id}
                                  aria-label="Health check"
                                  className="text-[var(--dk-fg-2)] hover:text-brand p-0.5 rounded disabled:opacity-50"
                                >
                                  <RefreshCw className="h-3 w-3" />
                                </button>
                                {c.status !== "revoked" && (
                                  <button
                                    onClick={() => revoke(c)}
                                    disabled={busy === c.id}
                                    aria-label="Revoke"
                                    className="text-[var(--dk-fg-2)] hover:text-[var(--dk-danger)] p-0.5 rounded disabled:opacity-50"
                                  >
                                    <Trash2 className="h-3 w-3" />
                                  </button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="px-4 pb-4 flex items-center gap-2">
                        <DkButton
                          size="sm"
                          variant={active > 0 ? "secondary" : "primary"}
                          onClick={() => setConnectFor(e)}
                          className="flex-1"
                        >
                          <Plus className="h-3.5 w-3.5" />
                          {active > 0 ? "Add Another" : "Connect"}
                        </DkButton>
                        <a
                          href={e.docs_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label="View docs"
                          className="rounded-md p-1.5 text-[var(--dk-fg-2)] hover:text-brand hover:bg-[var(--dk-bg-tint)] transition-colors duration-fast"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      </div>
                    </DkCard>
                  );
                })}
              </div>
            </section>
          );
        })
      )}

      {currentOrg && connectFor && (
        <ConnectDialog
          entry={connectFor}
          orgId={currentOrg.id}
          onClose={() => setConnectFor(null)}
          onCreated={() => {
            setConnectFor(null);
            void refresh();
          }}
        />
      )}
    </div>
  );
}

function ConnectDialog({
  entry,
  orgId,
  onClose,
  onCreated,
}: {
  entry: IntegrationCatalogEntry;
  orgId: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState(entry.name);
  const [secret, setSecret] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      await createConnection(orgId, {
        server_id: entry.server_id,
        name,
        secret: secret || undefined,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connect failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const authHint =
    entry.auth === "oauth2"
      ? "Paste an OAuth access token from the platform's developer portal. Real OAuth flow lands in a follow-up."
      : entry.auth === "pat"
      ? "Paste a Personal Access Token from your account settings."
      : entry.auth === "api_key"
      ? "Paste the API key from the platform's console."
      : "Paste your access credential. Stored encrypted at rest.";

  return (
    <DkDialog open={true} onClose={onClose} size="md">
      <DkDialogHeader
        title={`Connect ${entry.name}`}
        description={`${entry.description} Tools available: ${entry.tools.join(", ")}.`}
        onClose={onClose}
      />
      <DkDialogContent className="flex flex-col gap-4">
        <a
          href={entry.docs_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-brand hover:underline"
        >
          Open {entry.name} docs
          <ExternalLink className="h-3.5 w-3.5" />
        </a>

        <div className="flex flex-col gap-1.5">
          <DkLabel htmlFor="conn-name" required>
            Connection name
          </DkLabel>
          <DkInput
            id="conn-name"
            placeholder={`${entry.name} — primary`}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <p className="text-xs text-[var(--dk-fg-2)]">
            Use a label so multiple connections to the same platform stay
            distinct (e.g. "HubSpot — eu1", "HubSpot — us1").
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <DkLabel htmlFor="conn-secret" description={authHint}>
            <KeyRound className="inline h-3.5 w-3.5 mr-1 align-text-bottom" />
            {entry.auth === "oauth2"
              ? "Access token"
              : entry.auth === "pat"
              ? "PAT"
              : entry.auth === "api_key"
              ? "API key"
              : "Credential"}
          </DkLabel>
          <DkInput
            id="conn-secret"
            type="password"
            placeholder="••••••••"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
          />
        </div>

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
          disabled={!name || submitting}
        >
          Connect
        </DkButton>
      </DkDialogFooter>
    </DkDialog>
  );
}
