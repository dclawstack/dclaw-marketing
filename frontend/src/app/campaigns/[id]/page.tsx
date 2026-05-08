"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  getCampaign,
  getLeads,
  getAnalyticsByCampaign,
  getAnalyticsSummary,
  CampaignDetail,
  Lead,
  AnalyticsEvent,
} from "@/lib/api";

const statusColors: Record<string, string> = {
  draft: "bg-slate-100 text-slate-800",
  scheduled: "bg-blue-100 text-blue-800",
  active: "bg-green-100 text-green-800",
  paused: "bg-yellow-100 text-yellow-800",
  completed: "bg-slate-100 text-slate-800",
};

const leadStatusColors: Record<string, string> = {
  new: "bg-slate-100 text-slate-800",
  contacted: "bg-blue-100 text-blue-800",
  qualified: "bg-green-100 text-green-800",
  converted: "bg-purple-100 text-purple-800",
  lost: "bg-red-100 text-red-800",
};

export default function CampaignDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [events, setEvents] = useState<AnalyticsEvent[]>([]);
  const [summary, setSummary] = useState<Record<string, { count: number; total_value: number }> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      getCampaign(id),
      getLeads(undefined, undefined, undefined, id),
      getAnalyticsByCampaign(id),
      getAnalyticsSummary(id),
    ])
      .then(([camp, leadsRes, eventsRes, sum]) => {
        setCampaign(camp);
        setLeads(leadsRes.items);
        setEvents(eventsRes.items);
        setSummary(sum);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-slate-500">Loading...</div>;
  if (error) return <div className="text-red-600">Error: {error}</div>;
  if (!campaign) return null;

  return (
    <div>
      <div className="mb-4">
        <Link href="/campaigns">
          <Button variant="ghost" size="sm">
            ← Back to Campaigns
          </Button>
        </Link>
      </div>
      <h1 className="mb-2 text-2xl font-bold">{campaign.name}</h1>
      <div className="mb-6 flex items-center gap-2">
        <Badge className={statusColors[campaign.status]}>{campaign.status}</Badge>
        <span className="text-sm text-slate-500 capitalize">{campaign.type}</span>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Leads</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{campaign.lead_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Conversions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{campaign.conversion_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Total Spend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${campaign.total_spend.toFixed(2)}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="leads">
        <TabsList>
          <TabsTrigger value="leads">Leads</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="leads" className="mt-4">
          <Card>
            <CardContent className="p-0">
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
                      <TableCell>{l.email}</TableCell>
                      <TableCell>
                        {l.first_name} {l.last_name}
                      </TableCell>
                      <TableCell>{l.company || "—"}</TableCell>
                      <TableCell>{l.source || "—"}</TableCell>
                      <TableCell>
                        <Badge className={leadStatusColors[l.status]}>{l.status}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="mt-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {summary &&
              Object.entries(summary).map(([type, data]) => (
                <Card key={type}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-slate-500 capitalize">
                      {type}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{data.count}</div>
                    <div className="text-sm text-slate-500">
                      Value: ${data.total_value.toFixed(2)}
                    </div>
                  </CardContent>
                </Card>
              ))}
            {!summary && <div className="text-slate-500">No analytics data</div>}
          </div>

          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Events</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Value</TableHead>
                    <TableHead>Recorded At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-slate-500">
                        No events found
                      </TableCell>
                    </TableRow>
                  )}
                  {events.map((e) => (
                    <TableRow key={e.id}>
                      <TableCell className="capitalize">{e.event_type}</TableCell>
                      <TableCell>${e.value.toFixed(2)}</TableCell>
                      <TableCell>{new Date(e.recorded_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
