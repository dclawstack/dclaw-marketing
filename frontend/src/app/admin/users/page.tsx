"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

  // Create-user form state
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
    if (!confirm("Revoke this user's access? They will no longer be able to log in.")) {
      return;
    }
    try {
      await adminRevokeUser(userId);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Revoke failed.");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Users</h1>
          <p className="text-sm text-muted-foreground">
            Admin-only. Create users; share the generated temp password.
            Users reset on first login.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>Create user</Button>
        <Dialog
          open={createOpen}
          onOpenChange={(o) => {
            setCreateOpen(o);
            if (!o) setTempPassword(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create user</DialogTitle>
            </DialogHeader>
            {tempPassword ? (
              <div className="space-y-3">
                <p className="text-sm">
                  Share this temp password with the user. They&apos;ll be
                  asked to change it on first login. This is shown ONCE —
                  copy it now.
                </p>
                <div className="rounded-md border bg-muted px-3 py-2 font-mono text-sm">
                  {tempPassword}
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    navigator.clipboard.writeText(tempPassword);
                  }}
                >
                  Copy to clipboard
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="user@company.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="full_name">Full name (optional)</Label>
                  <Input
                    id="full_name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={isAdmin}
                    onChange={(e) => setIsAdmin(e.target.checked)}
                  />
                  Make admin (can create other users)
                </label>
                {error && (
                  <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    {error}
                  </div>
                )}
                <Button
                  onClick={handleCreate}
                  disabled={!email || creating}
                  className="w-full"
                >
                  {creating ? "Creating…" : "Create user & generate temp password"}
                </Button>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All users</CardTitle>
          <CardDescription>{loading ? "Loading…" : `${users.length} total`}</CardDescription>
        </CardHeader>
        <CardContent>
          {error && !createOpen && (
            <div className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-mono text-sm">{u.email}</TableCell>
                  <TableCell>{u.full_name ?? "—"}</TableCell>
                  <TableCell>
                    {u.is_active ? (
                      <Badge variant="default">active</Badge>
                    ) : (
                      <Badge variant="secondary">revoked</Badge>
                    )}
                    {u.password_reset_required && (
                      <Badge variant="outline" className="ml-2">
                        reset pending
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>{u.is_superuser ? "Admin" : "User"}</TableCell>
                  <TableCell className="space-x-2 text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleResetPassword(u.id)}
                    >
                      Reset password
                    </Button>
                    {u.is_active && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleRevoke(u.id)}
                      >
                        Revoke
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
