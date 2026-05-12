"use client";

import * as React from "react";
import { ArrowRight, Sparkles, Plus, Search, Trash2, FileText, ListChecks, BookOpen } from "lucide-react";

import {
  DkAvatar,
  DkBadge,
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardFooter,
  DkCardHeader,
  DkCardTitle,
  DkCheckbox,
  DkChip,
  DkDialog,
  DkDialogContent,
  DkDialogFooter,
  DkDialogHeader,
  DkEmptyState,
  DkEyebrow,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkProgress,
  DkRadio,
  DkRadioGroup,
  DkSelect,
  DkSidebar,
  DkSkeleton,
  DkSlider,
  DkSwitch,
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
  DkTabs,
  DkTabsContent,
  DkTabsList,
  DkTabsTrigger,
  DkTextarea,
  DkToastProvider,
  useDkToast,
} from "@/components/dk";
import { useAuth } from "@/contexts/auth-context";

/**
 * /admin/design — admin-only reference page rendering every <Dk*> variant.
 *
 * Eyeball-compare against the design's preview cards in
 * `design/source/project/preview/*.html` to confirm the live React
 * components match the design vocabulary (palette / radius / shadow /
 * spacing / focus rings / hover states).
 *
 * Hidden from the main nav — accessed by typing the URL directly. Only
 * superusers can render the contents; everyone else gets a forbidden
 * notice.
 */
export default function DesignReferencePage() {
  const { user } = useAuth();
  if (!user) {
    return <div className="py-12 text-center text-fg-2">Loading…</div>;
  }
  if (!user.is_superuser) {
    return (
      <div className="py-12 max-w-md mx-auto">
        <DkEmptyState
          title="Forbidden"
          description="The design reference page is admin-only."
        />
      </div>
    );
  }
  return (
    <DkToastProvider>
      <DesignSurface />
    </DkToastProvider>
  );
}

function DesignSurface() {
  return (
    <div className="flex flex-col gap-12 pb-12">
      <DkPageHeader
        eyebrow="Internal · Design Reference"
        title="Component Library"
        description="Every Dk primitive at every variant. Eyeball against the source preview cards to keep the implementation honest."
        actions={
          <>
            <DkButton variant="secondary">Open Preview HTML</DkButton>
            <DkButton withArrow>View Brand Guidelines</DkButton>
          </>
        }
      />

      <Section title="Eyebrows" eyebrow="Type">
        <DkEyebrow>Section eyebrow</DkEyebrow>
      </Section>

      <Section title="Buttons" eyebrow="Components">
        <div className="flex flex-wrap items-center gap-3">
          <DkButton>Primary</DkButton>
          <DkButton variant="secondary">Secondary</DkButton>
          <DkButton variant="ghost" withArrow>Ghost</DkButton>
          <DkButton variant="danger">Danger</DkButton>
          <DkButton variant="ink">Ink</DkButton>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <DkButton size="sm">Small</DkButton>
          <DkButton size="md">Medium</DkButton>
          <DkButton size="lg">Large</DkButton>
          <DkButton size="icon" aria-label="Plus"><Plus className="h-4 w-4" /></DkButton>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <DkButton loading>Loading…</DkButton>
          <DkButton withArrow>Continue</DkButton>
          <DkButton disabled>Disabled</DkButton>
        </div>
      </Section>

      <Section title="Cards" eyebrow="Surfaces">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <DkCard hover>
            <DkCardHeader>
              <DkChip tone="brand">Featured</DkChip>
              <DkCardTitle>Card with hover lift</DkCardTitle>
              <DkCardDescription>Hover me — translateY -3px + shadow-md + brand border tint.</DkCardDescription>
            </DkCardHeader>
            <DkCardContent>Body text uses fg-1 (gray-700) at md size with relaxed line-height.</DkCardContent>
            <DkCardFooter>
              <DkButton variant="ghost" withArrow>Learn more</DkButton>
            </DkCardFooter>
          </DkCard>

          <DkCard tinted>
            <DkCardHeader>
              <DkCardTitle>Tinted card</DkCardTitle>
              <DkCardDescription>Background purple-50 for soft section breaks.</DkCardDescription>
            </DkCardHeader>
            <DkCardContent>The hero halo uses this same tint.</DkCardContent>
          </DkCard>

          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Static card</DkCardTitle>
              <DkCardDescription>No hover effect, no tint. Default surface.</DkCardDescription>
            </DkCardHeader>
            <DkCardContent>Use this when the card is read-only / non-interactive.</DkCardContent>
          </DkCard>
        </div>
      </Section>

      <Section title="Chips & Badges" eyebrow="Status">
        <div className="flex flex-wrap items-center gap-2">
          <DkChip tone="brand">Brand</DkChip>
          <DkChip tone="neutral">Neutral</DkChip>
          <DkChip tone="success">Success</DkChip>
          <DkChip tone="warning">Warning</DkChip>
          <DkChip tone="danger">Danger</DkChip>
          <DkChip tone="info">Info</DkChip>
          <DkChip tone="outline">Outline</DkChip>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <DkBadge tone="brand">brand</DkBadge>
          <DkBadge tone="neutral">neutral</DkBadge>
          <DkBadge tone="success">success</DkBadge>
          <DkBadge tone="warning">warning</DkBadge>
          <DkBadge tone="danger">danger</DkBadge>
          <DkBadge tone="info">info</DkBadge>
          <DkBadge tone="outline">outline</DkBadge>
        </div>
      </Section>

      <Section title="Avatars" eyebrow="Identity">
        <div className="flex items-end gap-4">
          <DkAvatar size="sm" name="Ada Lovelace" />
          <DkAvatar size="md" name="Grace Hopper" />
          <DkAvatar size="lg" name="Margaret Hamilton" />
          <DkAvatar size="md" name="Anonymous" />
        </div>
      </Section>

      <Section title="Skeletons" eyebrow="Loading">
        <div className="flex flex-col gap-2 max-w-md">
          <DkSkeleton className="h-4 w-3/4" />
          <DkSkeleton className="h-4 w-full" />
          <DkSkeleton className="h-4 w-1/2" />
        </div>
      </Section>

      <Section title="Progress" eyebrow="Feedback">
        <div className="flex flex-col gap-3 max-w-md">
          <DkProgress value={25} tone="brand" showLabel />
          <DkProgress value={67} tone="success" showLabel />
          <DkProgress value={82} tone="warning" showLabel />
          <DkProgress value={95} tone="danger" showLabel />
        </div>
      </Section>

      <FormPlayground />

      <DialogPlayground />

      <Section title="Tabs" eyebrow="Navigation">
        <DkTabs defaultValue="overview" className="max-w-2xl">
          <DkTabsList>
            <DkTabsTrigger value="overview">Overview</DkTabsTrigger>
            <DkTabsTrigger value="members">Members</DkTabsTrigger>
            <DkTabsTrigger value="settings">Settings</DkTabsTrigger>
          </DkTabsList>
          <DkTabsContent value="overview" className="pt-2 text-md text-fg-1">
            Overview tab content. Use the tab list as a section navigator inside detail pages.
          </DkTabsContent>
          <DkTabsContent value="members" className="pt-2 text-md text-fg-1">
            Members tab content.
          </DkTabsContent>
          <DkTabsContent value="settings" className="pt-2 text-md text-fg-1">
            Settings tab content.
          </DkTabsContent>
        </DkTabs>
      </Section>

      <Section title="Tables" eyebrow="Data">
        <DkTable>
          <DkTableHeader>
            <DkTableRow>
              <DkTableHead>Name</DkTableHead>
              <DkTableHead>Role</DkTableHead>
              <DkTableHead>Status</DkTableHead>
              <DkTableHead className="text-right">Last activity</DkTableHead>
            </DkTableRow>
          </DkTableHeader>
          <DkTableBody>
            <DkTableRow>
              <DkTableCell className="font-medium">Ada Lovelace</DkTableCell>
              <DkTableCell>Admin</DkTableCell>
              <DkTableCell><DkBadge tone="success">active</DkBadge></DkTableCell>
              <DkTableCell className="text-right text-fg-2">2 min ago</DkTableCell>
            </DkTableRow>
            <DkTableRow>
              <DkTableCell className="font-medium">Grace Hopper</DkTableCell>
              <DkTableCell>Creatives</DkTableCell>
              <DkTableCell><DkBadge tone="warning">pending</DkBadge></DkTableCell>
              <DkTableCell className="text-right text-fg-2">1 h ago</DkTableCell>
            </DkTableRow>
            <DkTableRow>
              <DkTableCell className="font-medium">Margaret Hamilton</DkTableCell>
              <DkTableCell>Reviewer</DkTableCell>
              <DkTableCell><DkBadge tone="neutral">invited</DkBadge></DkTableCell>
              <DkTableCell className="text-right text-fg-2">yesterday</DkTableCell>
            </DkTableRow>
          </DkTableBody>
        </DkTable>
      </Section>

      <Section title="Breadcrumbs" eyebrow="Navigation">
        <DkBreadcrumb
          items={[
            { label: "Acme Inc", href: "/orgs/acme" },
            { label: "Projects", href: "/orgs/acme/projects" },
            { label: "Q2 Launch" },
          ]}
        />
      </Section>

      <Section title="Empty states" eyebrow="Zero data">
        <div className="grid gap-4 lg:grid-cols-2">
          <DkEmptyState
            icon={<FileText className="h-6 w-6" />}
            title="No briefs yet"
            description="Start by creating a brief that anchors the campaign's objective, voice, and target persona."
            actions={<DkButton withArrow>New brief</DkButton>}
          />
          <DkEmptyState
            icon={<ListChecks className="h-6 w-6" />}
            title="Inbox is clear"
            description="No approvals pending. New agent runs will surface here for review."
          />
        </div>
      </Section>

      <SidebarPreview />

      <ToastPlayground />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------

function Section({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4 scroll-mt-24" id={title.toLowerCase().replace(/\s+/g, "-")}>
      <div className="flex flex-col gap-1">
        {eyebrow && <DkEyebrow>{eyebrow}</DkEyebrow>}
        <h2 className="font-display text-2xl font-bold leading-snug tracking-snug text-ink">
          {title}
        </h2>
      </div>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Form playground
// ---------------------------------------------------------------------------

function FormPlayground() {
  const [text, setText] = React.useState("");
  const [textarea, setTextarea] = React.useState("");
  const [select, setSelect] = React.useState("admin");
  const [sw, setSw] = React.useState(true);
  const [check, setCheck] = React.useState(true);
  const [radio, setRadio] = React.useState("autopilot");
  const [slider, setSlider] = React.useState(40);

  return (
    <Section title="Forms" eyebrow="Inputs">
      <div className="grid gap-6 md:grid-cols-2 max-w-3xl">
        <div className="flex flex-col gap-1.5">
          <DkLabel htmlFor="design-email" required description="We use this for login + audit-log attribution.">
            Email
          </DkLabel>
          <DkInput
            id="design-email"
            placeholder="you@company.com"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <DkLabel htmlFor="design-search">Search</DkLabel>
          <div className="relative">
            <DkInput id="design-search" placeholder="Search briefs, assets, leads…" className="pl-9" />
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-fg-muted" />
          </div>
        </div>

        <div className="flex flex-col gap-1.5 md:col-span-2">
          <DkLabel htmlFor="design-brief">Campaign brief</DkLabel>
          <DkTextarea
            id="design-brief"
            rows={4}
            placeholder="Describe the campaign in one paragraph…"
            value={textarea}
            onChange={(e) => setTextarea(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <DkLabel htmlFor="design-role">Role</DkLabel>
          <DkSelect id="design-role" value={select} onChange={(e) => setSelect(e.target.value)}>
            <option value="admin">Admin</option>
            <option value="manager">Manager</option>
            <option value="creatives">Creatives</option>
            <option value="reviewer">Reviewer</option>
          </DkSelect>
        </div>

        <div className="flex flex-col gap-1.5">
          <DkLabel>Invalid input</DkLabel>
          <DkInput invalid defaultValue="not an email" />
          <p className="text-xs text-danger">That doesn't look like an email address.</p>
        </div>

        <div className="flex items-center justify-between rounded-md border border-[var(--dk-border-strong)] p-4 md:col-span-2">
          <div className="flex flex-col">
            <p className="text-sm font-semibold text-ink">Autopilot for internal drafts</p>
            <p className="text-xs text-fg-2">Agents act immediately; logged in audit trail.</p>
          </div>
          <DkSwitch checked={sw} onChange={() => setSw(!sw)} />
        </div>

        <label className="flex items-center gap-2.5 cursor-pointer">
          <DkCheckbox checked={check} onChange={() => setCheck(!check)} />
          <span className="text-sm text-ink">Send approval emails for outbound posts</span>
        </label>

        <div className="flex flex-col gap-2">
          <DkLabel>Trust mode</DkLabel>
          <DkRadioGroup orientation="vertical">
            {(["autopilot", "soft", "hard"] as const).map((m) => (
              <label key={m} className="flex items-center gap-2.5 cursor-pointer">
                <DkRadio
                  name="trust"
                  value={m}
                  checked={radio === m}
                  onChange={() => setRadio(m)}
                />
                <span className="text-sm text-ink capitalize">{m}-gate</span>
              </label>
            ))}
          </DkRadioGroup>
        </div>

        <div className="flex flex-col gap-2 md:col-span-2">
          <DkLabel description="Default monthly cap for paid media spend.">Monthly budget cap</DkLabel>
          <DkSlider
            value={slider}
            onChange={(e) => setSlider(Number(e.target.value))}
            min={0}
            max={100}
            showValue
          />
        </div>
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Dialog playground
// ---------------------------------------------------------------------------

function DialogPlayground() {
  const [open, setOpen] = React.useState<"sm" | "md" | "lg" | "xl" | null>(null);
  return (
    <Section title="Dialogs" eyebrow="Modals">
      <div className="flex flex-wrap gap-3">
        {(["sm", "md", "lg", "xl"] as const).map((s) => (
          <DkButton key={s} variant="secondary" onClick={() => setOpen(s)}>
            Open {s.toUpperCase()}
          </DkButton>
        ))}
      </div>
      <DkDialog open={open !== null} onClose={() => setOpen(null)} size={open ?? "md"}>
        <DkDialogHeader
          title="Delete this campaign?"
          description="The campaign and its associated drafts, assets, and analytics events will be permanently removed. This cannot be undone."
          onClose={() => setOpen(null)}
        />
        <DkDialogContent>
          <p className="text-md text-fg-1">
            If a colleague has bookmarked specific assets from this campaign, those links will break. Consider archiving the campaign instead.
          </p>
        </DkDialogContent>
        <DkDialogFooter>
          <DkButton variant="secondary" onClick={() => setOpen(null)}>Cancel</DkButton>
          <DkButton variant="danger">
            <Trash2 className="h-4 w-4" />
            Delete campaign
          </DkButton>
        </DkDialogFooter>
      </DkDialog>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Sidebar preview
// ---------------------------------------------------------------------------

function SidebarPreview() {
  return (
    <Section title="Sidebar" eyebrow="Navigation">
      <div className="rounded-2xl border border-[var(--dk-border)] overflow-hidden bg-white max-w-3xl">
        <div className="flex">
          <DkSidebar
            groups={[
              {
                label: "Workspace",
                items: [
                  { label: "Dashboard", href: "/admin/design#sidebar", icon: <Sparkles className="h-4 w-4" /> },
                  { label: "Library", href: "/admin/design/library", icon: <BookOpen className="h-4 w-4" /> },
                ],
              },
              {
                label: "Coming v0.2",
                items: [
                  { label: "Calendar", href: "/admin/design/calendar", icon: <FileText className="h-4 w-4" />, disabled: true, badge: <DkBadge tone="brand">soon</DkBadge> },
                ],
              },
            ]}
          />
          <div className="flex-1 p-6 text-fg-1 text-md">
            Side nav content area. Use this layout for org/project detail pages.
          </div>
        </div>
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Toast playground
// ---------------------------------------------------------------------------

function ToastPlayground() {
  const toast = useDkToast();
  return (
    <Section title="Toasts" eyebrow="Feedback">
      <div className="flex flex-wrap gap-3">
        <DkButton variant="secondary" onClick={() => toast.push({ tone: "success", title: "Approved", description: "Variant queued for publishing." })}>Success</DkButton>
        <DkButton variant="secondary" onClick={() => toast.push({ tone: "info", title: "Job started", description: "Ingesting 4 files into the knowledge graph." })}>Info</DkButton>
        <DkButton variant="secondary" onClick={() => toast.push({ tone: "warning", title: "Heads up", description: "Daily LLM budget at 80%." })}>Warning</DkButton>
        <DkButton variant="secondary" onClick={() => toast.push({ tone: "danger", title: "Failed", description: "Could not reach the LinkedIn API." })}>Danger</DkButton>
      </div>
    </Section>
  );
}
