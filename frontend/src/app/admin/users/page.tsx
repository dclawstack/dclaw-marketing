"use client";

import { useEffect, useState } from "react";
import { Copy, UserPlus } from "lucide-react";

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
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
} from "@/components/dk";
import {
  AdminUser,
  adminCreateUser,
  adminListUsers,
  adminResetUserPassword,
  adminRevokeUser,
} from "@/lib/api";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [creating, setCreating] = useState(false);
  const [tempPassword, setTempPassword] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      setUsers(await adminListUsers());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const response = await adminCreateUser({
        email,
        full_name: fullName || undefined,
        is_superuser: isAdmin,
      });
      setTempPassword(response.temp_password);
      setEmail("");
      setFullName("");
      setIsAdmin(false);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed.");
    } finally {
      setCreating(false);
    }
  }

  async function handleResetPassword(userId: string) {
    if (!confirm("Issue a new temporary password for this user?")) return;
    try {
      const res = await adminResetUserPassword(userId);
      setTempPassword(res.temp_password);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Reset failed.");
    }
  }

  async function handleRevoke(userId: string) {
    if (
      !confirm(
        "Revoke this user's access? They will no longer be able to log in.",
      )
    ) {
      return;
    }
    try {
      await adminRevokeUser(userId);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Revoke failed.");
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
                <DkTableHead>Status</DkTableHead>
                <DkTableHead>Role</DkTableHead>
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
                  <DkTableCell>{u.is_superuser ? "Admin" : "User"}</DkTableCell>
                  <DkTableCell className="text-right">
                    <div className="inline-flex items-center gap-2">
                      <DkButton
                        size="sm"
                        variant="secondary"
                        onClick={() => handleResetPassword(u.id)}
                      >
                        Reset Password
                      </DkButton>
                      {u.is_active && (
                        <DkButton
                          size="sm"
                          variant="danger"
                          onClick={() => handleRevoke(u.id)}
                        >
                          Revoke
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
              <label className="flex items-center gap-2.5 cursor-pointer">
                <DkCheckbox
                  checked={isAdmin}
                  onChange={(e) => setIsAdmin(e.target.checked)}
                />
                <span className="text-sm text-ink">
                  Make admin (can create other users)
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
    </div>
  );
}
