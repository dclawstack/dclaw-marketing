import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Bot,
  Calendar,
  Github,
  Inbox as InboxIcon,
  Layers,
  LibrarySquare,
  Mail,
  Megaphone,
  Network,
  Palette,
  Search,
  Sparkles,
  Target,
  Users,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import { DemoControls } from "@/components/landing/demo-controls";

interface Feature {
  icon: LucideIcon;
  title: string;
  body: string;
  href: string;
}

// Mirrors app-shell.tsx NAV_GROUPS — every card targets a real route.
const FEATURES_RUN: Feature[] = [
  {
    icon: Bot,
    title: "Conductor agent",
    body:
      "Hand a brief to the Conductor; it plans the work across the marketing agents and routes drafts to your Inbox for approval. You supervise — agents do the work.",
    href: "/conductor",
  },
  {
    icon: InboxIcon,
    title: "Approval Inbox",
    body:
      "Every agent action that needs a human lands here. Review variants, approve or reject, and keep autonomy on a leash with per-action trust modes.",
    href: "/inbox",
  },
  {
    icon: Target,
    title: "Campaigns",
    body:
      "Plan and track email, social, PPC, and content campaigns — budgets, schedules, status, and the leads and spend attributed to each one.",
    href: "/campaigns",
  },
  {
    icon: Users,
    title: "Leads & funnel",
    body:
      "A scored, enriched lead database with funnel stages (MQL → SQL → customer), activity timelines, notes, and UTM attribution captured at first touch.",
    href: "/leads",
  },
];

const FEATURES_CREATE: Feature[] = [
  {
    icon: Palette,
    title: "Creatives agent",
    body:
      "Generate on-brand copy and creative variants from your brand kit — palette, voice, do-say / don't-say lists, and personas all feed the prompt.",
    href: "/agents/creatives",
  },
  {
    icon: LibrarySquare,
    title: "Content library",
    body:
      "A central home for generated assets and approved content, ready to schedule, repurpose, or push out to your connected channels.",
    href: "/library",
  },
  {
    icon: Workflow,
    title: "Workflows",
    body:
      "Compose reusable, multi-step automations from workflow templates so recurring marketing motions run the same way every time.",
    href: "/workflows",
  },
  {
    icon: Calendar,
    title: "Content calendar",
    body:
      "See scheduled posts and campaign milestones on a single calendar so the whole team knows what ships and when.",
    href: "/calendar",
  },
];

const FEATURES_DISTRIBUTE: Feature[] = [
  {
    icon: Megaphone,
    title: "Channels",
    body:
      "Connect and publish to your social and marketing channels, with scheduled posts and per-account OAuth managed in one place.",
    href: "/channels",
  },
  {
    icon: Mail,
    title: "Email",
    body:
      "Send and sequence email through SendGrid, Postmark, or Resend, with delivery / open / click events streamed back in via webhooks.",
    href: "/email",
  },
  {
    icon: Layers,
    title: "Ads",
    body:
      "Manage paid-media creatives and campaigns alongside organic, so budget and performance live next to everything else.",
    href: "/ads",
  },
];

const FEATURES_MEASURE: Feature[] = [
  {
    icon: BarChart3,
    title: "Analytics",
    body:
      "Impressions, clicks, conversions, spend, and conversion rate rolled up per campaign — with per-campaign drill-down and a content performance heatmap.",
    href: "/analytics",
  },
  {
    icon: Search,
    title: "SEO agent",
    body:
      "Run the SEO pipeline to find opportunities and generate optimized content, with answer-engine (AEO) coverage for the new search surfaces.",
    href: "/agents/seo",
  },
  {
    icon: Network,
    title: "Knowledge base",
    body:
      "Ingest files, URLs, and transcripts into searchable memory. Agents ground their output in your real context instead of guessing.",
    href: "/knowledge",
  },
];

const STACK = [
  "Next.js 14",
  "Tailwind",
  "FastAPI",
  "SQLAlchemy 2.0",
  "Postgres 16",
  "Alembic",
  "FastAPI-Users",
  "OpenRouter",
  "Ollama",
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white text-ink">
      <TopNav />

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div
          className="absolute inset-0 -z-10 opacity-50"
          style={{
            backgroundImage:
              "radial-gradient(circle at 18% -10%, var(--dk-purple-100) 0%, transparent 42%), radial-gradient(circle at 82% 12%, var(--dk-purple-50) 0%, transparent 40%)",
          }}
        />
        <div className="mx-auto max-w-6xl px-6 pb-20 pt-20 lg:pt-28">
          <div className="inline-flex items-center gap-2 rounded-full border border-[var(--dk-border)] bg-white/80 px-3 py-1 text-xs font-semibold text-brand shadow-sm backdrop-blur">
            <Sparkles className="h-3 w-3" /> DClaw vertical SaaS · Marketing
          </div>
          <h1 className="mt-6 max-w-3xl text-5xl font-bold tracking-tight sm:text-6xl">
            The agent-driven marketing operating system.
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-[var(--dk-fg-1)]">
            DClaw Marketing runs the whole loop — plan, create, distribute,
            measure — with AI agents doing the work and you supervising. A
            Conductor that orchestrates campaigns, a Creatives agent grounded
            in your brand kit, an approval Inbox, scored leads, multi-channel
            distribution, and analytics that close the loop.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-white shadow hover:bg-[var(--dk-purple-800)]"
            >
              Open App <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#features"
              className="inline-flex items-center gap-2 rounded-lg border border-[var(--dk-border)] bg-white px-5 py-3 text-sm font-semibold text-[var(--dk-fg-1)] hover:bg-[var(--dk-gray-50)]"
            >
              Explore features
            </a>
          </div>

          <div className="mt-16 grid gap-4 sm:grid-cols-4">
            <Stat label="App routes" value="30+" />
            <Stat label="API endpoints" value="80+" />
            <Stat label="Backend tests" value="80" />
            <Stat label="Marketing agents" value="3" />
          </div>
        </div>
      </section>

      {/* DEMO CONTROLS — remove this block + the import to drop the demo feature */}
      <DemoControls />
      {/* END DEMO CONTROLS */}

      {/* ── Feature sections ─────────────────────────────────────────── */}
      <div id="features" />
      <FeatureBlock
        eyebrow="Run the work"
        title="Agents do the work. You supervise."
        items={FEATURES_RUN}
      />
      <FeatureBlock
        eyebrow="Create on-brand"
        title="Every asset grounded in your brand kit."
        items={FEATURES_CREATE}
        tinted
      />
      <FeatureBlock
        eyebrow="Distribute everywhere"
        title="One place to ship across every channel."
        items={FEATURES_DISTRIBUTE}
      />
      <FeatureBlock
        eyebrow="Measure & close the loop"
        title="Know what worked — then do more of it."
        items={FEATURES_MEASURE}
        tinted
      />

      {/* ── Stack ────────────────────────────────────────────────────── */}
      <section className="border-y border-[var(--dk-border)] bg-ink text-white">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="grid gap-12 lg:grid-cols-[1fr_2fr]">
            <div>
              <div className="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide">
                Stack
              </div>
              <h2 className="mt-3 text-3xl font-bold text-white">
                Built on boring infrastructure.
              </h2>
              <p className="mt-4 text-white/70">
                Next.js 14 App Router, FastAPI + Pydantic v2 + SQLAlchemy 2.0,
                Postgres 16, Alembic, FastAPI-Users JWT auth. AI calls route
                through OpenRouter with a local Ollama fallback.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              {STACK.map((t) => (
                <div
                  key={t}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 font-mono text-xs"
                >
                  {t}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h2 className="text-4xl font-bold tracking-tight">Ready to take a tour?</h2>
        <p className="mt-4 text-[var(--dk-fg-1)]">
          Seed the demo workspace above, then open the dashboard. Every screen
          reads from real endpoints — campaigns, leads, brand kit, and all.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg bg-brand px-6 py-3 text-sm font-semibold text-white shadow hover:bg-[var(--dk-purple-800)]"
          >
            Open App <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="https://github.com/dclawstack/dclaw-marketing"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--dk-border)] bg-white px-6 py-3 text-sm font-semibold text-[var(--dk-fg-1)] hover:bg-[var(--dk-gray-50)]"
          >
            <Github className="h-4 w-4" /> dclawstack/dclaw-marketing
          </a>
        </div>
      </section>

      <footer className="border-t border-[var(--dk-border)] bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-6 text-xs text-[var(--dk-fg-2)]">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand" />
            <span className="font-semibold text-ink">DClaw Marketing</span>
            <span>·</span>
            <span>part of the DClaw vertical SaaS stack</span>
          </div>
          <a
            href="https://github.com/dclawstack/dclaw-marketing"
            className="inline-flex items-center gap-1 hover:text-ink"
          >
            <Github className="h-3.5 w-3.5" /> dclawstack/dclaw-marketing
          </a>
        </div>
      </footer>
    </main>
  );
}

function TopNav() {
  return (
    <header className="sticky top-0 z-30 border-b border-[var(--dk-border)] bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <Link href="/" className="flex items-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/brand/logos/dclaw-icon-purple.svg"
            alt=""
            width={24}
            height={24}
            className="h-6 w-6"
          />
          <span className="font-display text-sm font-bold text-ink">
            DClaw <span className="text-brand">Marketing</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-1 text-xs font-medium md:flex">
          <a
            href="#features"
            className="rounded-md px-2.5 py-1 text-[var(--dk-fg-1)] hover:bg-[var(--dk-gray-50)] hover:text-ink"
          >
            Features
          </a>
          <Link
            href="/login"
            className="rounded-md px-2.5 py-1 text-[var(--dk-fg-1)] hover:bg-[var(--dk-gray-50)] hover:text-ink"
          >
            Sign in
          </Link>
        </nav>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1 rounded-md bg-brand px-3 py-1.5 text-xs font-semibold text-white hover:bg-[var(--dk-purple-800)]"
        >
          Open App <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </header>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--dk-border)] bg-white/80 p-4 backdrop-blur">
      <div className="font-display text-3xl font-bold text-brand">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-[var(--dk-fg-2)]">
        {label}
      </div>
    </div>
  );
}

function FeatureBlock({
  eyebrow,
  title,
  items,
  tinted = false,
}: {
  eyebrow: string;
  title: string;
  items: Feature[];
  tinted?: boolean;
}) {
  return (
    <section
      className={`border-t border-[var(--dk-border)] ${
        tinted ? "bg-[var(--dk-gray-50)]" : "bg-white"
      }`}
    >
      <div className="mx-auto max-w-6xl px-6 py-24">
        <div className="mb-12 max-w-2xl">
          <div className="inline-flex items-center gap-1 rounded-full bg-[var(--dk-purple-100)] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand">
            {eyebrow}
          </div>
          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            {title}
          </h2>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          {items.map((f) => {
            const Icon = f.icon;
            return (
              <Link
                key={f.title}
                href={f.href}
                className="group flex flex-col rounded-2xl border border-[var(--dk-border)] bg-white p-6 transition hover:-translate-y-0.5 hover:border-brand hover:shadow-lg"
              >
                <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--dk-purple-100)]">
                  <Icon className="h-5 w-5 text-brand" />
                </div>
                <h3 className="text-lg font-semibold">{f.title}</h3>
                <p className="mt-2 flex-1 text-sm text-[var(--dk-fg-1)]">
                  {f.body}
                </p>
                <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-brand group-hover:gap-2 transition-all">
                  Explore <ArrowRight className="h-3 w-3" />
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
