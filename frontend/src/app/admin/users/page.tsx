"use client";

import { useEffect, useState } from "react";
import { Building2, Copy, Trash2, UserPlus } from "lucide-react";

import { getToken } from "@/lib/auth";

import { useAuth } from "@/contexts/auth-context";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkCheckbox,
  DkDialog,
  DkDialogContent,
  DkDialogFooter,
  DkDialogHeader,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
} from "@/components/dk";
import {
  AdminUser,
  OrgRole,
  Organization,
  adminCreateUser,
  adminDeleteUser,
  adminListUsers,
  adminResetUserPassword,
  addOrgMember,
  createOrg,
  listOrgs,
  listOrgMembers,
  removeOrgMember,
  updateOrgMemberRole,
} from "@/lib/api";

interface UserMembership {
  org_id: string;
  org_slug: string;
  org_name: string;
  role: OrgRole;
}

const ROLE_OPTIONS: OrgRole[] = [
  "admin",
  "manager",
  "creatives",
  "social_media_manager",
  "seo_specialist",
  "paid_media_specialist",
  "reviewer",
  "analyst",
  "viewer",
  "client",
];

const BOOTSTRAP_ADMIN_EMAIL = "admin@dclaw.io";

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");

  // Organization(s) section — multi-row.
  type OrgMode = "none" | "assign";
  const [orgMode, setOrgMode] = useState<OrgMode>("none");
  // Each row: { rowId, org_id (empty = unset), role }
  interface OrgRow { rowId: string; org_id: string; role: OrgRole }
  const [orgRows, setOrgRows] = useState<OrgRow[]>([
    { rowId: crypto.randomUUID(), org_id: "", role: "viewer" },
  ]);

  // New-org popup
  const [newOrgOpen, setNewOrgOpen] = useState(false);
  const [newOrgRowId, setNewOrgRowId] = useState<string | null>(null);
  const [newOrgName, setNewOrgName] = useState("");
  const [newOrgDesc, setNewOrgDesc] = useState("");
  const [newOrgExternal, setNewOrgExternal] = useState(false);
  const [newOrgBusy, setNewOrgBusy] = useState(false);

  // Per-user memberships indexed by user id, populated on list load.
  const [memberships, setMemberships] = useState<Record<string, UserMembership[]>>({});
  // All orgs, for the manage-orgs dialog.
  const [allOrgs, setAllOrgs] = useState<Organization[]>([]);
  // Which user's manage-orgs dialog is open (null = closed).
  const [managingUser, setManagingUser] = useState<AdminUser | null>(null);
  const [managingBusy, setManagingBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  // Separate state for the Reset-Password flow so the result has its own
  // dialog (the createOpen dialog is gated on createOpen=true).
  const [resetPwTemp, setResetPwTemp] = useState<string | null>(null);

  const [pendingDelete, setPendingDelete] = useState<AdminUser | null>(null);
  const [confirmEmail, setConfirmEmail] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function loadMembershipsFor(userId: string): Promise<UserMembership[]> {
    const r = await fetch(`/api/v1/admin/users/${userId}/memberships`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!r.ok) return [];
    return (await r.json()) as UserMembership[];
  }

  async function refresh() {
    setLoading(true);
    try {
      const us = await adminListUsers();
      setUsers(us);
      // Hydrate memberships in parallel — best effort.
      const all = await Promise.all(
        us.map(async (u) => [u.id, await loadMembershipsFor(u.id)] as const),
      );
      setMemberships(Object.fromEntries(all));
      // Also fetch all orgs for the manage-orgs dialog.
      try {
        setAllOrgs(await listOrgs());
      } catch {
        // If user lacks visibility into all orgs (e.g., org-admin), they'll
        // see only the orgs they belong to via /orgs anyway.
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function addToOrg(user: AdminUser, orgId: string, role: OrgRole) {
    setManagingBusy(true);
    try {
      await addOrgMember(orgId, { user_id: user.id, role });
      setMemberships({
        ...memberships,
        [user.id]: await loadMembershipsFor(user.id),
      });
    } finally {
      setManagingBusy(false);
    }
  }

  async function changeRoleInOrg(
    user: AdminUser,
    orgId: string,
    role: OrgRole,
  ) {
    // Need the membership id for the existing /orgs/{org_id}/memberships/{id} PATCH.
    const members = await listOrgMembers(orgId);
    const m = members.find((x) => x.user_id === user.id);
    if (!m) return;
    setManagingBusy(true);
    try {
      await updateOrgMemberRole(orgId, m.id, role);
      setMemberships({
        ...memberships,
        [user.id]: await loadMembershipsFor(user.id),
      });
    } finally {
      setManagingBusy(false);
    }
  }

  async function removeFromOrg(user: AdminUser, orgId: string) {
    const members = await listOrgMembers(orgId);
    const m = members.find((x) => x.user_id === user.id);
    if (!m) return;
    setManagingBusy(true);
    try {
      await removeOrgMember(orgId, m.id);
      setMemberships({
        ...memberships,
        [user.id]: await loadMembershipsFor(user.id),
      });
    } finally {
      setManagingBusy(false);
    }
  }

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const orgsPayload =
        orgMode === "assign"
          ? orgRows
              .filter((r) => r.org_id)
              .map((r) => ({ org_id: r.org_id, role: r.role }))
          : [];

      const res = await fetch("/api/v1/admin/users/with-org", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          full_name: fullName || undefined,
          orgs: orgsPayload,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `Create failed (${res.status})`);
      }
      const data = await res.json();
      setTempPassword(data.temp_password);
      setEmail("");
      setFullName("");
      setOrgMode("none");
      setOrgRows([
        { rowId: crypto.randomUUID(), org_id: "", role: "viewer" },
      ]);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed.");
    } finally {
      setCreating(false);
    }
  }

  async function handleCreateNewOrg() {
    if (!newOrgName.trim() || !newOrgRowId) return;
    setNewOrgBusy(true);
    try {
      const created = await createOrg({
        name: newOrgName.trim(),
        description: newOrgDesc.trim() || undefined,
        is_external: newOrgExternal,
      });
      // Refresh org list and auto-select the new one in the row.
      const orgs = await listOrgs();
      setAllOrgs(orgs);
      setOrgRows((rows) =>
        rows.map((r) =>
          r.rowId === newOrgRowId ? { ...r, org_id: created.id } : r,
        ),
      );
      setNewOrgOpen(false);
      setNewOrgName("");
      setNewOrgDesc("");
      setNewOrgExternal(false);
      setNewOrgRowId(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Org create failed.");
    } finally {
      setNewOrgBusy(false);
    }
  }

  async function handleResetPassword(userId: string) {
    if (!confirm("Issue a new temporary password for this user?")) return;
    try {
      const res = await adminResetUserPassword(userId);
      setResetPwTemp(res.temp_password);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Reset failed.");
    }
  }

  function openDelete(u: AdminUser) {
    setPendingDelete(u);
    setConfirmEmail("");
    setDeleteError(null);
  }

  function closeDelete() {
    if (deleting) return;
    setPendingDelete(null);
    setConfirmEmail("");
    setDeleteError(null);
  }

  async function submitDelete() {
    if (!pendingDelete) return;
    if (confirmEmail !== pendingDelete.email) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await adminDeleteUser(pendingDelete.id);
      await refresh();
      setPendingDelete(null);
      setConfirmEmail("");
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setDeleting(false);
    }
  }

  function closeCreate() {
    setCreateOpen(false);
    setTempPassword(null);
    setError(null);
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Admin"
        title="Users"
        description="Admin-only. Create users — share the generated temp password — users reset on first login."
        actions={
          <DkButton onClick={() => setCreateOpen(true)}>
            <UserPlus className="h-4 w-4" />
            Create User
          </DkButton>
        }
      />

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>All Users</DkCardTitle>
          <DkCardDescription>
            {loading ? "Loading…" : `${users.length} total`}
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="px-0 pt-0">
          {error && !createOpen && (
            <div
              role="alert"
              className="mx-6 mb-4 rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
            >
              {error}
            </div>
          )}
          <DkTable>
            <DkTableHeader>
              <DkTableRow>
                <DkTableHead>Email</DkTableHead>
                <DkTableHead>Name</DkTableHead>
                <DkTableHead>Slug</DkTableHead>
                <DkTableHead>Status</DkTableHead>
                <DkTableHead>Role</DkTableHead>
                <DkTableHead>Orgs</DkTableHead>
                <DkTableHead className="text-right">Actions</DkTableHead>
              </DkTableRow>
            </DkTableHeader>
            <DkTableBody>
              {users.map((u) => (
                <DkTableRow key={u.id}>
                  <DkTableCell className="font-mono text-sm">
                    {u.email}
                  </DkTableCell>
                  <DkTableCell>{u.full_name ?? "—"}</DkTableCell>
                  <DkTableCell className="font-mono text-xs text-[var(--dk-fg-2)]">
                    {u.slug ?? "—"}
                  </DkTableCell>
                  <DkTableCell>
                    <div className="flex items-center gap-2">
                      {u.is_active ? (
                        <DkBadge tone="success">active</DkBadge>
                      ) : (
                        <DkBadge tone="neutral">revoked</DkBadge>
                      )}
                      {u.password_reset_required && (
                        <DkBadge tone="warning">reset pending</DkBadge>
                      )}
                    </div>
                  </DkTableCell>
                  <DkTableCell>
                    {u.is_superuser ? "Superadmin" : "User"}
                  </DkTableCell>
                  <DkTableCell>
                    <div className="flex flex-wrap gap-1">
                      {(memberships[u.id] ?? []).map((m) => (
                        <DkBadge key={m.org_id} tone="brand">
                          {m.org_slug}:{m.role}
                        </DkBadge>
                      ))}
                      {(memberships[u.id] ?? []).length === 0 && (
                        <span className="text-xs text-[var(--dk-fg-2)]">
                          none
                        </span>
                      )}
                    </div>
                  </DkTableCell>
                  <DkTableCell className="text-right">
                    <div className="inline-flex items-center gap-2">
                      <DkButton
                        size="sm"
                        variant="secondary"
                        onClick={() => setManagingUser(u)}
                      >
                        <Building2 className="h-4 w-4" />
                        Orgs
                      </DkButton>
                      <DkButton
                        size="sm"
                        variant="secondary"
                        onClick={() => handleResetPassword(u.id)}
                      >
                        Reset Password
                      </DkButton>
                      {u.email !== BOOTSTRAP_ADMIN_EMAIL &&
                        u.id !== currentUser?.id && (
                          <DkButton
                            size="sm"
                            variant="danger"
                            onClick={() => openDelete(u)}
                            aria-label={`Delete user ${u.email}`}
                          >
                            <Trash2 className="h-4 w-4" />
                            Delete
                          </DkButton>
                        )}
                    </div>
                  </DkTableCell>
                </DkTableRow>
              ))}
            </DkTableBody>
          </DkTable>
        </DkCardContent>
      </DkCard>

      <DkDialog open={createOpen} onClose={closeCreate} size="md">
        <DkDialogHeader
          title={tempPassword ? "Temp Password Issued" : "Create User"}
          description={
            tempPassword
              ? "Copy this now — it's shown once. The user must reset it on first login."
              : "Generates a one-shot temporary password the user replaces on first login."
          }
          onClose={closeCreate}
        />
        <DkDialogContent>
          {tempPassword ? (
            <div className="flex flex-col gap-3">
              <div className="rounded-md border border-[var(--dk-border-strong)] bg-[var(--dk-bg-muted)] px-3 py-3 font-mono text-md text-ink break-all">
                {tempPassword}
              </div>
              <DkButton
                variant="secondary"
                onClick={() => {
                  navigator.clipboard.writeText(tempPassword);
                }}
              >
                <Copy className="h-4 w-4" />
                Copy to Clipboard
              </DkButton>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="email" required>
                  Email
                </DkLabel>
                <DkInput
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@company.com"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="full_name">Full name (optional)</DkLabel>
                <DkInput
                  id="full_name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
              {/* Organization(s) — multi-row */}
              <div className="flex flex-col gap-3 rounded-md border border-[var(--dk-border)] p-3 bg-[var(--dk-gray-50)]">
                <DkLabel>Organization(s)</DkLabel>
                <div className="flex flex-col gap-2">
                  <label className="flex items-center gap-2 cursor-pointer text-sm">
                    <input
                      type="radio"
                      name="orgmode"
                      checked={orgMode === "none"}
                      onChange={() => setOrgMode("none")}
                    />
                    <span>No org — assign later</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-sm">
                    <input
                      type="radio"
                      name="orgmode"
                      checked={orgMode === "assign"}
                      onChange={() => setOrgMode("assign")}
                    />
                    <span>Assign to org(s)</span>
                  </label>
                </div>

                {orgMode === "assign" && (
                  <div className="flex flex-col gap-2 pt-1">
                    {orgRows.map((row, idx) => (
                      <div
                        key={row.rowId}
                        className="flex items-center gap-2"
                      >
                        <DkSelect
                          value={row.org_id}
                          onChange={(e) => {
                            const v = e.target.value;
                            if (v === "__new__") {
                              setNewOrgRowId(row.rowId);
                              setNewOrgOpen(true);
                              return;
                            }
                            setOrgRows((rs) =>
                              rs.map((r) =>
                                r.rowId === row.rowId
                                  ? { ...r, org_id: v }
                                  : r,
                              ),
                            );
                          }}
                          className="flex-1"
                        >
                          <option value="">Select an org…</option>
                          <option value="__new__">+ Create new org…</option>
                          <option disabled>──────────</option>
                          {allOrgs.map((o) => (
                            <option key={o.id} value={o.id}>
                              {o.name} — {o.slug}
                            </option>
                          ))}
                        </DkSelect>
                        <DkSelect
                          value={row.role}
                          onChange={(e) =>
                            setOrgRows((rs) =>
                              rs.map((r) =>
                                r.rowId === row.rowId
                                  ? { ...r, role: e.target.value as OrgRole }
                                  : r,
                              ),
                            )
                          }
                          className="w-40"
                        >
                          {ROLE_OPTIONS.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </DkSelect>
                        {orgRows.length > 1 && (
                          <button
                            type="button"
                            aria-label="Remove org row"
                            onClick={() =>
                              setOrgRows((rs) =>
                                rs.filter((r) => r.rowId !== row.rowId),
                              )
                            }
                            className="rounded p-1 text-[var(--dk-fg-2)] hover:bg-[var(--dk-danger-bg)] hover:text-[var(--dk-danger)] transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    ))}
                    <DkButton
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        setOrgRows((rs) => [
                          ...rs,
                          {
                            rowId: crypto.randomUUID(),
                            org_id: "",
                            role: "viewer",
                          },
                        ])
                      }
                    >
                      + Add another org
                    </DkButton>
                  </div>
                )}
              </div>

              {error && (
                <div
                  role="alert"
                  className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
                >
                  {error}
                </div>
              )}
            </div>
          )}
        </DkDialogContent>
        {!tempPassword && (
          <DkDialogFooter>
            <DkButton variant="secondary" onClick={closeCreate}>
              Cancel
            </DkButton>
            <DkButton
              onClick={handleCreate}
              disabled={!email || creating}
              loading={creating}
            >
              Create User
            </DkButton>
          </DkDialogFooter>
        )}
      </DkDialog>

      <DkDialog
        open={pendingDelete !== null}
        onClose={closeDelete}
        size="md"
      >
        {pendingDelete && (
          <>
            <DkDialogHeader
              title="Delete user?"
              description={`This permanently removes ${pendingDelete.email} from the platform. They will no longer be able to log in. References to this user in audit history are kept (set to NULL). This cannot be undone.`}
              onClose={closeDelete}
            />
            <DkDialogContent>
              <DkLabel htmlFor="confirm-email">
                Type the user's email{" "}
                <span className="font-mono">{pendingDelete.email}</span> to
                confirm.
              </DkLabel>
              <DkInput
                id="confirm-email"
                value={confirmEmail}
                onChange={(e) => setConfirmEmail(e.target.value)}
                placeholder={pendingDelete.email}
                autoFocus
                disabled={deleting}
                className="mt-2"
              />
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
                onClick={closeDelete}
                disabled={deleting}
              >
                Cancel
              </DkButton>
              <DkButton
                variant="danger"
                onClick={submitDelete}
                disabled={confirmEmail !== pendingDelete.email || deleting}
                loading={deleting}
              >
                Delete forever
              </DkButton>
            </DkDialogFooter>
          </>
        )}
      </DkDialog>

      {/* Manage orgs dialog — assign / change role / remove a user from any org */}
      <DkDialog
        open={managingUser !== null}
        onClose={() => !managingBusy && setManagingUser(null)}
        size="lg"
      >
        <DkDialogHeader
          title={managingUser ? `Org memberships — ${managingUser.email}` : ""}
          description="Add the user to one or more orgs, change their role per-org, or remove them. Superadmins are implicit admins of every org and don't need explicit memberships."
          onClose={() => setManagingUser(null)}
        />
        <DkDialogContent>
          {managingUser?.is_superuser && (
            <div className="mb-3 rounded-md border border-[var(--dk-border)] bg-[var(--dk-purple-50)] px-3 py-2 text-sm text-ink">
              <strong>Superadmin</strong> — implicit admin of every org. Membership
              controls are locked; their role is fixed to <em>superadmin</em>.
            </div>
          )}
          {managingUser && !managingUser.is_superuser && (
            <div className="flex flex-col gap-2">
              {allOrgs.map((org) => {
                const userMs = memberships[managingUser.id] ?? [];
                const existing = userMs.find((m) => m.org_id === org.id);
                return (
                  <div
                    key={org.id}
                    className="flex items-center justify-between gap-3 rounded-md border border-[var(--dk-border)] px-3 py-2"
                  >
                    <div className="flex flex-col">
                      <span className="text-sm font-medium">{org.name}</span>
                      <span className="text-xs font-mono text-[var(--dk-fg-2)]">
                        {org.slug}
                      </span>
                    </div>
                    {existing ? (
                      <div className="flex items-center gap-2">
                        <DkSelect
                          value={existing.role}
                          disabled={managingBusy}
                          onChange={(e) =>
                            changeRoleInOrg(
                              managingUser,
                              org.id,
                              e.target.value as OrgRole,
                            )
                          }
                          className="w-44"
                        >
                          {ROLE_OPTIONS.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </DkSelect>
                        <DkButton
                          size="sm"
                          variant="danger"
                          disabled={managingBusy}
                          onClick={() =>
                            removeFromOrg(managingUser, org.id)
                          }
                        >
                          Remove
                        </DkButton>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <DkSelect
                          defaultValue="viewer"
                          disabled={managingBusy}
                          id={`role-${org.id}`}
                          className="w-44"
                        >
                          {ROLE_OPTIONS.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </DkSelect>
                        <DkButton
                          size="sm"
                          disabled={managingBusy}
                          onClick={() => {
                            const sel = document.getElementById(
                              `role-${org.id}`,
                            ) as HTMLSelectElement | null;
                            const role = (sel?.value ?? "viewer") as OrgRole;
                            addToOrg(managingUser, org.id, role);
                          }}
                        >
                          Add
                        </DkButton>
                      </div>
                    )}
                  </div>
                );
              })}
              {allOrgs.length === 0 && (
                <p className="text-sm text-[var(--dk-fg-2)]">
                  No orgs visible. Create an org first.
                </p>
              )}
            </div>
          )}
        </DkDialogContent>
        <DkDialogFooter>
          <DkButton
            variant="secondary"
            onClick={() => setManagingUser(null)}
            disabled={managingBusy}
          >
            Close
          </DkButton>
        </DkDialogFooter>
      </DkDialog>

      {/* New-org popup launched from the org dropdown */}
      <DkDialog
        open={newOrgOpen}
        onClose={() => !newOrgBusy && setNewOrgOpen(false)}
        size="md"
      >
        <DkDialogHeader
          title="Create organization"
          description="Slug is auto-generated as o-{first4(name)}-{random6hex}."
          onClose={() => setNewOrgOpen(false)}
        />
        <DkDialogContent className="flex flex-col gap-3">
          <div>
            <DkLabel htmlFor="no-name" required>
              Name
            </DkLabel>
            <DkInput
              id="no-name"
              value={newOrgName}
              onChange={(e) => setNewOrgName(e.target.value)}
              placeholder="Acme Inc."
            />
          </div>
          <div>
            <DkLabel htmlFor="no-desc">Description</DkLabel>
            <DkInput
              id="no-desc"
              value={newOrgDesc}
              onChange={(e) => setNewOrgDesc(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer text-sm">
            <DkCheckbox
              checked={newOrgExternal}
              onChange={(e) => setNewOrgExternal(e.target.checked)}
            />
            <span>External / client organization</span>
          </label>
        </DkDialogContent>
        <DkDialogFooter>
          <DkButton
            variant="secondary"
            onClick={() => setNewOrgOpen(false)}
            disabled={newOrgBusy}
          >
            Cancel
          </DkButton>
          <DkButton
            onClick={handleCreateNewOrg}
            disabled={!newOrgName.trim() || newOrgBusy}
            loading={newOrgBusy}
          >
            Create
          </DkButton>
        </DkDialogFooter>
      </DkDialog>

      {/* Reset-password result dialog — surfaces the one-shot temp password
          after a successful /admin/users/{id}/reset-password call. */}
      <DkDialog
        open={resetPwTemp !== null}
        onClose={() => setResetPwTemp(null)}
        size="sm"
      >
        <DkDialogHeader
          title="Temp Password Issued"
          description="Copy this now — it's shown once. The user must reset it on first login."
          onClose={() => setResetPwTemp(null)}
        />
        <DkDialogContent>
          {resetPwTemp && (
            <div className="flex flex-col gap-3">
              <div className="rounded-md border border-[var(--dk-border-strong)] bg-[var(--dk-bg-muted)] px-3 py-3 font-mono text-md text-ink break-all">
                {resetPwTemp}
              </div>
              <DkButton
                variant="secondary"
                onClick={() =>
                  navigator.clipboard.writeText(resetPwTemp ?? "")
                }
              >
                <Copy className="h-4 w-4" />
                Copy to Clipboard
              </DkButton>
            </div>
          )}
        </DkDialogContent>
        <DkDialogFooter>
          <DkButton onClick={() => setResetPwTemp(null)}>Done</DkButton>
        </DkDialogFooter>
      </DkDialog>
    </div>
  );
}
