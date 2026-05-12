"use client";

import { useState } from "react";
import { Loader2, Plug, ShieldCheck } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
} from "@/components/dk";
import { createConnection } from "@/lib/api";
import { useOrg } from "@/contexts/org-context";

/**
 * D3 — Bring-your-own MCP server.
 *
 * The existing Connection model already supports an arbitrary server_id
 * + metadata_json.endpoint (the async client in mcp_client.py reads
 * exactly those two fields). This page is just a friendly wrapper:
 * paste a server_id + endpoint URL + bearer token → POST /connections.
 */
export default function ByoMcpPage() {
  const { currentOrg } = useOrg();
  const [serverId, setServerId] = useState("");
  const [name, setName] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [secret, setSecret] = useState("");
  const [scopes, setScopes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function save() {
    if (!currentOrg) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const created = await createConnection(currentOrg.id, {
        server_id: serverId.trim(),
        name: name.trim() || serverId.trim(),
        secret: secret || undefined,
        metadata_json: { endpoint: endpoint.trim(), is_byo: true },
        scopes: scopes
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setSuccess(
        `Saved connection ${created.id.slice(0, 8)}… You can now invoke it from the integrations page.`,
      );
      setServerId("");
      setEndpoint("");
      setSecret("");
      setScopes("");
      setName("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Theme D3 · Integrations"
        title="Bring-your-own MCP server"
        description="Wire up an MCP server that isn't in the built-in registry. The async client invokes tools at POST {endpoint}/tools/{tool_name}/invoke; this form just persists the endpoint + bearer secret behind a Connection row, Fernet-encrypted server-side."
        actions={<DkBadge tone="brand">SP3-15</DkBadge>}
      />

      {error ? (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      ) : null}
      {success ? (
        <div className="rounded-md border border-[var(--dk-success)] bg-[var(--dk-success-bg)] px-3 py-2 text-sm text-[var(--dk-success)]">
          <ShieldCheck className="h-4 w-4 inline-block mr-1" /> {success}
        </div>
      ) : null}

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Add custom MCP server</DkCardTitle>
          <DkCardDescription>
            Server ID is the slug your agents will refer to. Use lowercase
            snake_case (e.g. <code>internal_pricing</code>).
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <DkLabel>Server ID</DkLabel>
              <DkInput
                placeholder="internal_pricing"
                value={serverId}
                onChange={(e) => setServerId(e.target.value)}
              />
            </div>
            <div>
              <DkLabel>Display name (optional)</DkLabel>
              <DkInput
                placeholder="Internal pricing tool"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          </div>
          <div>
            <DkLabel>Endpoint URL</DkLabel>
            <DkInput
              placeholder="https://mcp.example.com"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
            />
          </div>
          <div>
            <DkLabel>Bearer token (optional)</DkLabel>
            <DkInput
              type="password"
              placeholder="sk-…"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
            />
          </div>
          <div>
            <DkLabel>Scopes (comma-separated, optional)</DkLabel>
            <DkInput
              placeholder="read, write"
              value={scopes}
              onChange={(e) => setScopes(e.target.value)}
            />
          </div>
          <div>
            <DkButton onClick={save} disabled={busy || !serverId.trim() || !endpoint.trim()}>
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plug className="h-4 w-4" />
              )}
              Save connection
            </DkButton>
          </div>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
