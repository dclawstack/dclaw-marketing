"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getLeads, Lead, LeadStatus } from "@/lib/api";

const statusColors: Record<LeadStatus, string> = {
  new: "bg-slate-100 text-slate-800",
  contacted: "bg-blue-100 text-blue-800",
  qualified: "bg-green-100 text-green-800",
  converted: "bg-purple-100 text-purple-800",
  lost: "bg-red-100 text-red-800",
};

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "">("");

  useEffect(() => {
    setLoading(true);
    getLeads(search || undefined, sourceFilter || undefined, statusFilter || undefined)
      .then((res) => setLeads(res.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [search, sourceFilter, statusFilter]);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Leads</h1>
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64"
            />
            <Input
              placeholder="Source"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="w-48"
            />
            <Select
              value={statusFilter}
              onValueChange={(v) => setStatusFilter(v as LeadStatus)}
              className="w-48"
            >
              <option value="">All Statuses</option>
              <option value="new">New</option>
              <option value="contacted">Contacted</option>
              <option value="qualified">Qualified</option>
              <option value="converted">Converted</option>
              <option value="lost">Lost</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardContent className="p-0">
          {loading ? (
            <div className="p-4 text-slate-500">Loading...</div>
          ) : error ? (
            <div className="p-4 text-red-600">Error: {error}</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leads.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-slate-500">
                      No leads found
                    </TableCell>
                  </TableRow>
                )}
                {leads.map((l) => (
                  <TableRow key={l.id}>
                    <TableCell className="font-medium">{l.email}</TableCell>
                    <TableCell>
                      {l.first_name} {l.last_name}
                    </TableCell>
                    <TableCell>{l.company || "—"}</TableCell>
                    <TableCell>{l.source || "—"}</TableCell>
                    <TableCell>
                      <Badge className={statusColors[l.status]}>{l.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
