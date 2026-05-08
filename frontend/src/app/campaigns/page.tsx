"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getCampaigns, Campaign, CampaignStatus, CampaignType } from "@/lib/api";

const statusColors: Record<CampaignStatus, string> = {
  draft: "bg-slate-100 text-slate-800",
  scheduled: "bg-blue-100 text-blue-800",
  active: "bg-green-100 text-green-800",
  paused: "bg-yellow-100 text-yellow-800",
  completed: "bg-slate-100 text-slate-800",
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | "">("");
  const [typeFilter, setTypeFilter] = useState<CampaignType | "">("");

  useEffect(() => {
    setLoading(true);
    getCampaigns(statusFilter || undefined, typeFilter || undefined)
      .then((res) => setCampaigns(res.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [statusFilter, typeFilter]);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Campaigns</h1>
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Select
              value={statusFilter}
              onValueChange={(v) => setStatusFilter(v as CampaignStatus)}
              className="w-48"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="scheduled">Scheduled</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
            </Select>
            <Select
              value={typeFilter}
              onValueChange={(v) => setTypeFilter(v as CampaignType)}
              className="w-48"
            >
              <option value="">All Types</option>
              <option value="email">Email</option>
              <option value="social">Social</option>
              <option value="ppc">PPC</option>
              <option value="content">Content</option>
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
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Budget</TableHead>
                  <TableHead>Start</TableHead>
                  <TableHead>End</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {campaigns.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-slate-500">
                      No campaigns found
                    </TableCell>
                  </TableRow>
                )}
                {campaigns.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.name}</TableCell>
                    <TableCell className="capitalize">{c.type}</TableCell>
                    <TableCell>
                      <Badge className={statusColors[c.status]}>{c.status}</Badge>
                    </TableCell>
                    <TableCell>{c.budget ? `$${c.budget.toFixed(2)}` : "—"}</TableCell>
                    <TableCell>{c.start_date || "—"}</TableCell>
                    <TableCell>{c.end_date || "—"}</TableCell>
                    <TableCell>
                      <Link href={`/campaigns/${c.id}`}>
                        <Button size="sm" variant="outline">
                          View
                        </Button>
                      </Link>
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
