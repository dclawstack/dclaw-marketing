"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ExternalLink, Mail, UserPlus, Users } from "lucide-react";

import { getToken } from "@/lib/auth";

import {
  DkAvatar,
  DkBadge,
  DkBreadcrumb,
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
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
} from "@/components/dk";
import {
  AdminUser,
  OrgMembership,
  OrgRole,
  Organization,
  addOrgMember,
  adminListUsers,
  getOrg,
  listOrgMembers,
  removeOrgMember,
  updateOrgMemberRole,
} from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

const ROLES: { value: OrgRole; label: string; description: string }[] = [
  {
    value: "admin",
    label: "Admin",
    description: "Everything in the org — users, integrations, billing.",
  },
  {
    value: "manager",
    label: "Manager",
    description: "Supervises the Conductor; final approver; no user mgmt.",
  },
  {
    value: "creatives",
    label: "Creatives",
    description: "Supervises the Creatives Agent; owns brand kits.",
  },
  {
    value: "social_media_manager",
    label: "Social Media Manager",
    description: "Owns calendar; approves social posts + DM replies.",
  },
  {
    value: "seo_specialist",
    label: "SEO Specialist",
    description: "Owns blog pipeline; approves keyword + outline + drafts.",
  },
  {
    value: "paid_media_specialist",
    label: "Paid Media Specialist",
    description: "Owns ad creative + budget moves.",
  },
  {
    value: "reviewer",
    label: "Reviewer",
    description: "Approval-only — read + comment + approve / request changes.",
  },
  {
    value: "analyst",
    label: "Analyst",
    description: "Read-only across analytics; builds dashboards.",
  },
  {
    value: "viewer",
    label: "Viewer",
    description: "Read-only on assigned items.",
  },
  {
    value: "client",
    label: "Client",
    description: "External — portal-restricted read + approve (v0.2+).",
  },
];

const ROLE_LABEL: Record<OrgRole, string> = ROLES.reduce(
  (acc, r) => ({ ...acc, [r.value]: r.label }),
  {} as Record<OrgRole, string>,
);

export default function MembersPage() {
  const params = useParams<{ id: string }>();
  const { user: me } = useAuth();
  const orgId = params?.id ?? "";

  const [org, setOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrgMembership[]>([]);
  const [allUsers, setAllUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [addOpen, setAddOpen] = useState(false);
  const [pickUserId, setPickUserId] = useState("");
  const [pickRole, setPickRole] = useState<OrgRole>("viewer");
  const [adding, setAdding] = useState(false);

  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<OrgRole>("viewer");
  const [inviting, setInviting] = useState(false);
  const [inviteResult, setInviteResult] = useState<{
    email: string;
    user_created: boolean;
    temp_password: string | null;
  } | null>(null);

  const userMap = useMemo(
    () => new Map(allUsers.map((u) => [u.id, u])),
    [allUsers],
  );

  const refresh = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const [o, m, u] = await Promise.all([
        getOrg(orgId),
        listOrgMembers(orgId),
        me?.is_superuser ? adminListUsers() : Promise.resolve([]),
      ]);
      setOrg(o);
      setMembers(m);
      setAllUsers(u);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [orgId, me?.is_superuser]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const memberUserIds = new Set(members.map((m) => m.user_id));
  const addableUsers = allUsers.filter(
    (u) => u.is_active && !memberUserIds.has(u.id),
  );

  async function handleAdd() {
    if (!pickUserId) return;
    setAdding(true);
    setError(null);
    try {
      await addOrgMember(orgId, { user_id: pickUserId, role: pickRole });
      setAddOpen(false);
      setPickUserId("");
      setPickRole("viewer");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Add failed.");
    } finally {
      setAdding(false);
    }
  }

  async function handleInvite() {
    if (!inviteEmail.trim()) return;
    setInviting(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/orgs/${orgId}/invite`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: inviteEmail.trim(),
          full_name: inviteName.trim() || null,
          role: inviteRole,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `Invite failed (${res.status})`);
      }
      const data = await res.json();
      setInviteResult({
        email: inviteEmail.trim(),
        user_created: data.user_created,
        temp_password: data.temp_password,
      });
      setInviteEmail("");
      setInviteName("");
      setInviteRole("viewer");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed.");
    } finally {
      setInviting(false);
    }
  }

  async function handleRoleChange(m: OrgMembership, role: OrgRole) {
    try {
      await updateOrgMemberRole(orgId, m.id, role);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Update failed.");
    }
  }

  async function handleRemove(m: OrgMembership) {
    const u = userMap.get(m.user_id);
    const label = u ? u.full_name ?? u.email : m.user_id;
    if (!confirm(`Remove ${label} from this organization?`)) return;
    try {
      await removeOrgMember(orgId, m.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Remove failed.");
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          { label: org?.name ?? "…", href: orgId ? `/orgs/${orgId}` : "/orgs" },
          { label: "Members" },
        ]}
      />

      <DkPageHeader
        eyebrow="Organization · Identity"
        title="Members"
        description="Invite teammates and assign their supervision scope. Each role is a bundle of permissions; per-project overrides can layer on top."
        actions={
          me?.is_superuser ? (
            <div className="flex gap-2">
              <DkButton
                variant="secondary"
                onClick={() => {
                  setInviteOpen(true);
                  setInviteResult(null);
                }}
                disabled={loading}
              >
                <Mail className="h-4 w-4" />
                Invite by email
              </DkButton>
              <DkButton onClick={() => setAddOpen(true)} disabled={loading}>
                <UserPlus className="h-4 w-4" />
                Add Member
              </DkButton>
            </div>
          ) : null
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
        <DkSkeleton className="h-64" />
      ) : members.length === 0 ? (
        <DkEmptyState
          icon={<Users className="h-6 w-6" />}
          title="No members yet"
          description="Add yourself or a teammate to begin. Members get role-scoped access to this org's brand, knowledge, and projects."
          actions={
            me?.is_superuser ? (
              <DkButton onClick={() => setAddOpen(true)}>
                <UserPlus className="h-4 w-4" />
                Add the first member
              </DkButton>
            ) : null
          }
        />
      ) : (
        <DkCard>
          <DkCardContent className="p-0">
            <DkTable>
              <DkTableHeader>
                <DkTableRow>
                  <DkTableHead>Member</DkTableHead>
                  <DkTableHead>Status</DkTableHead>
                  <DkTableHead>Role</DkTableHead>
                  <DkTableHead className="text-right">Actions</DkTableHead>
                </DkTableRow>
              </DkTableHeader>
              <DkTableBody>
                {members.map((m) => {
                  const u = userMap.get(m.user_id);
                  const self = me?.id === m.user_id;
                  return (
                    <DkTableRow key={m.id}>
                      <DkTableCell>
                        <div className="flex items-center gap-3">
                          <DkAvatar
                            size="sm"
                            name={u?.full_name ?? u?.email ?? "?"}
                          />
                          <div className="flex flex-col">
                            <span className="font-medium text-ink">
                              {u?.full_name ?? u?.email ?? m.user_id.slice(0, 8)}
                              {self && (
                                <span className="ml-1.5 text-xs text-[var(--dk-fg-2)]">
                                  (you)
                                </span>
                              )}
                            </span>
                            {u?.full_name && (
                              <span className="text-xs text-[var(--dk-fg-2)] font-mono">
                                {u.email}
                              </span>
                            )}
                          </div>
                        </div>
                      </DkTableCell>
                      <DkTableCell>
                        {u?.is_active ? (
                          <DkBadge tone="success">active</DkBadge>
                        ) : (
                          <DkBadge tone="neutral">revoked</DkBadge>
                        )}
                      </DkTableCell>
                      <DkTableCell>
                        {me?.is_superuser ? (
                          <DkSelect
                            value={m.role}
                            onChange={(e) =>
                              handleRoleChange(m, e.target.value as OrgRole)
                            }
                            className="w-48"
                          >
                            {ROLES.map((r) => (
                              <option key={r.value} value={r.value}>
                                {r.label}
                              </option>
                            ))}
                          </DkSelect>
                        ) : (
                          <DkBadge tone="brand">{ROLE_LABEL[m.role]}</DkBadge>
                        )}
                      </DkTableCell>
                      <DkTableCell className="text-right">
                        {me?.is_superuser && !self && (
                          <DkButton
                            size="sm"
                            variant="danger"
                            onClick={() => handleRemove(m)}
                          >
                            Remove
                          </DkButton>
                        )}
                      </DkTableCell>
                    </DkTableRow>
                  );
                })}
              </DkTableBody>
            </DkTable>
          </DkCardContent>
        </DkCard>
      )}

      <DkDialog
        open={inviteOpen}
        onClose={() => !inviting && setInviteOpen(false)}
        size="md"
      >
        <DkDialogHeader
          title="Invite by email"
          description="Sends a membership invite. New users get a one-time temporary password to hand off securely."
          onClose={() => setInviteOpen(false)}
        />
        <DkDialogContent className="flex flex-col gap-4">
          {inviteResult ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-[var(--dk-fg-1)]">
                Invited <strong>{inviteResult.email}</strong>.{" "}
                {inviteResult.user_created
                  ? "Created a new user account."
                  : "Attached existing user to the organization."}
              </p>
              {inviteResult.temp_password && (
                <div className="rounded-md border border-[var(--dk-border)] bg-[var(--dk-purple-50)] p-3 text-sm">
                  <p className="mb-1 font-medium text-ink">
                    Temporary password (hand off out-of-band):
                  </p>
                  <code className="font-mono text-xs">
                    {inviteResult.temp_password}
                  </code>
                  <p className="mt-1.5 text-xs text-[var(--dk-fg-2)]">
                    They will be prompted to set a new password on first login.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="inv-email" required>
                  Email
                </DkLabel>
                <DkInput
                  id="inv-email"
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="teammate@example.com"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="inv-name">Full name (optional)</DkLabel>
                <DkInput
                  id="inv-name"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="inv-role" required>
                  Role
                </DkLabel>
                <DkSelect
                  id="inv-role"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as OrgRole)}
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </DkSelect>
                <p className="text-xs text-[var(--dk-fg-2)]">
                  {ROLES.find((r) => r.value === inviteRole)?.description}
                </p>
              </div>
            </>
          )}
        </DkDialogContent>
        <DkDialogFooter>
          <DkButton
            variant="secondary"
            onClick={() => setInviteOpen(false)}
            disabled={inviting}
          >
            {inviteResult ? "Close" : "Cancel"}
          </DkButton>
          {!inviteResult && (
            <DkButton
              onClick={handleInvite}
              disabled={!inviteEmail.trim() || inviting}
              loading={inviting}
            >
              Send invite
            </DkButton>
          )}
        </DkDialogFooter>
      </DkDialog>

      <DkDialog open={addOpen} onClose={() => setAddOpen(false)} size="md">
        <DkDialogHeader
          title="Add Member"
          description="Pick a user and assign their supervision scope. Need to create a new user first?"
          onClose={() => setAddOpen(false)}
        />
        <DkDialogContent className="flex flex-col gap-4">
          {addableUsers.length === 0 ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-[var(--dk-fg-1)]">
                Every active user is already a member of this organization.
              </p>
              <Link
                href="/admin/users"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-brand hover:underline"
              >
                Create a new user
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="pick-user" required>
                  User
                </DkLabel>
                <DkSelect
                  id="pick-user"
                  value={pickUserId}
                  onChange={(e) => setPickUserId(e.target.value)}
                >
                  <option value="">Select a user…</option>
                  {addableUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name ? `${u.full_name} — ${u.email}` : u.email}
                    </option>
                  ))}
                </DkSelect>
                <Link
                  href="/admin/users"
                  className="inline-flex items-center gap-1.5 text-xs text-brand hover:underline pt-1"
                >
                  Need to create a new user?
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>

              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="pick-role" required>
                  Role
                </DkLabel>
                <DkSelect
                  id="pick-role"
                  value={pickRole}
                  onChange={(e) => setPickRole(e.target.value as OrgRole)}
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </DkSelect>
                <p className="text-xs text-[var(--dk-fg-2)] leading-normal">
                  {ROLES.find((r) => r.value === pickRole)?.description}
                </p>
              </div>
            </>
          )}
        </DkDialogContent>
        <DkDialogFooter>
          <DkButton variant="secondary" onClick={() => setAddOpen(false)}>
            Cancel
          </DkButton>
          {addableUsers.length > 0 && (
            <DkButton
              onClick={handleAdd}
              disabled={!pickUserId || adding}
              loading={adding}
            >
              Add to Organization
            </DkButton>
          )}
        </DkDialogFooter>
      </DkDialog>
    </div>
  );
}
