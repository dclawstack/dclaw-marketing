import {
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Workflow,
  Network,
  Users,
  BarChart3,
  Server,
  GitBranch,
  Layers,
  Cpu,
  Eye,
  Lock,
  Calendar,
  Mail,
  Megaphone,
  Bot,
  Image as ImageIcon,
  Search,
  Database,
  Activity,
  CheckCircle2,
  ChevronRight,
} from "lucide-react";

function XIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

function Github({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56v-2c-3.2.7-3.87-1.36-3.87-1.36-.52-1.33-1.27-1.68-1.27-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.69 1.25 3.35.96.1-.75.4-1.25.72-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.18 1.18.92-.26 1.91-.39 2.89-.39.98 0 1.97.13 2.89.39 2.21-1.49 3.18-1.18 3.18-1.18.62 1.58.23 2.75.11 3.04.73.81 1.18 1.84 1.18 3.1 0 4.42-2.7 5.39-5.27 5.68.42.36.78 1.06.78 2.14v3.17c0 .31.21.68.8.56C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5z" />
    </svg>
  );
}

function Linkedin({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.86-3.04-1.86 0-2.14 1.45-2.14 2.95v5.66H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.86 3.38-1.86 3.61 0 4.27 2.38 4.27 5.48v6.27zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .78 0 1.73v20.54C0 23.22.79 24 1.77 24h20.45c.99 0 1.78-.78 1.78-1.73V1.73C24 .78 23.21 0 22.22 0z" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Section components                                                 */
/* ------------------------------------------------------------------ */

function NavBar() {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-white/70 border-b border-[var(--dk-border)]">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="#top" className="flex items-center gap-2.5">
          <img
            src="/brand/logos/dclaw-icon-purple.svg"
            alt=""
            width={36}
            height={36}
            className="w-9 h-9"
          />
          <span className="text-xl tracking-tight" style={{ letterSpacing: "-0.02em" }}>
            <span className="font-extrabold text-[var(--dk-ink)]">DClaw</span>
            <span className="hidden sm:inline font-medium text-[var(--dk-purple-700)] ml-1.5">
              Marketing
            </span>
          </span>
        </a>
        <nav className="hidden md:flex items-center gap-7 text-sm font-medium text-[var(--dk-fg-2)]">
          <a href="#features" className="hover:text-[var(--dk-purple-800)] transition">Features</a>
          <a href="#agents" className="hover:text-[var(--dk-purple-800)] transition">Agents</a>
          <a href="#integrations" className="hover:text-[var(--dk-purple-800)] transition">Integrations</a>
          <a href="#governance" className="hover:text-[var(--dk-purple-800)] transition">Governance</a>
          <a href="#deploy" className="hover:text-[var(--dk-purple-800)] transition">Deploy</a>
        </nav>
        <div className="flex items-center gap-2.5">
          <a
            href="https://github.com/dclawstack/dclaw-marketing"
            className="hidden sm:flex items-center gap-1.5 text-sm font-medium text-[var(--dk-fg-2)] hover:text-[var(--dk-purple-800)] transition"
          >
            <Github className="w-4 h-4" /> GitHub
          </a>
          <a
            href="#cta"
            className="inline-flex items-center gap-1.5 text-sm font-semibold rounded-full bg-[var(--dk-purple-700)] text-white px-4 py-2 hover:bg-[var(--dk-purple-800)] transition shadow-sm"
          >
            Get a demo <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section
      id="top"
      className="relative overflow-hidden text-white"
      style={{
        background:
          "radial-gradient(circle at 88% 12%, var(--dk-purple-500) 0%, var(--dk-purple-700) 32%, var(--dk-purple-900) 80%)",
      }}
    >
      <div className="dk-grain absolute inset-0 pointer-events-none" />
      <div className="relative max-w-7xl mx-auto px-6 pt-24 pb-32 lg:pt-32 lg:pb-40">
        <div className="dk-fade-in">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 border border-white/20 backdrop-blur-sm px-3.5 py-1.5 text-xs font-semibold tracking-wider uppercase mb-7">
            <Sparkles className="w-3.5 h-3.5" /> v1.1.2 · Agents go live
          </div>
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold leading-[1.04] tracking-tight max-w-4xl">
            An agent-driven marketing operating system.
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-white/80 max-w-2xl leading-relaxed">
            Set the brand once. Ingest your context. A fleet of specialist AI agents
            runs the operation. You supervise from a single station — and approve
            every outbound action.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <a
              href="#cta"
              className="inline-flex items-center gap-2 rounded-full bg-white text-[var(--dk-purple-900)] px-6 py-3 font-semibold hover:bg-[var(--dk-purple-50)] transition shadow-lg"
            >
              Book a demo <ArrowRight className="w-4 h-4" />
            </a>
            <a
              href="#features"
              className="inline-flex items-center gap-2 rounded-full bg-white/10 border border-white/30 backdrop-blur-sm text-white px-6 py-3 font-semibold hover:bg-white/20 transition"
            >
              See the capabilities <ChevronRight className="w-4 h-4" />
            </a>
          </div>

          <div className="mt-14 grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-3xl">
            {[
              { v: "8", l: "Role agents" },
              { v: "13", l: "Publishing channels" },
              { v: "26", l: "AI provider types" },
              { v: "14", l: "MCP integrations" },
            ].map((s) => (
              <div key={s.l} className="border-l-2 border-white/30 pl-4">
                <div className="text-3xl font-bold tracking-tight">{s.v}</div>
                <div className="text-xs uppercase tracking-wider text-white/60 mt-1">{s.l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <svg
        className="absolute bottom-0 left-0 right-0 w-full h-12"
        viewBox="0 0 1440 48"
        preserveAspectRatio="none"
        aria-hidden
      >
        <path d="M0 48 L0 24 Q720 -24 1440 24 L1440 48 Z" fill="white" />
      </svg>
    </section>
  );
}

function LogoStrip() {
  const logos = [
    "HubSpot", "Salesforce", "Slack", "Stripe", "Notion",
    "GA4", "Mixpanel", "Webflow", "WordPress", "Ahrefs",
  ];
  return (
    <section className="bg-white border-b border-[var(--dk-border)]">
      <div className="max-w-7xl mx-auto px-6 py-10">
        <p className="text-center text-xs uppercase tracking-[0.2em] text-[var(--dk-fg-3)] mb-6">
          Plugs into the tools you already run
        </p>
        <div className="flex flex-wrap justify-center items-center gap-x-10 gap-y-4">
          {logos.map((l) => (
            <span
              key={l}
              className="text-[var(--dk-fg-3)] font-semibold text-base tracking-tight grayscale opacity-70 hover:opacity-100 transition"
            >
              {l}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

interface FeatureGroup {
  eyebrow: string;
  title: string;
  description: string;
  features: { icon: React.ComponentType<{ className?: string }>; title: string; body: string }[];
}

const groups: FeatureGroup[] = [
  {
    eyebrow: "Foundation",
    title: "Multi-tenant from day one.",
    description:
      "An Organization → Project → Campaign → Asset hierarchy with ten role scopes, two-tier admin model, encrypted credentials, full audit. Built for agencies and operators who can't afford to start over later.",
    features: [
      {
        icon: Users,
        title: "10 supervision scopes",
        body: "Admin, Manager, Creatives, SMM, SEO, Paid Media, Reviewer, Analyst, Viewer, Client. Each role sees only what it should — and acts only where you let it.",
      },
      {
        icon: Lock,
        title: "Per-org encrypted secrets",
        body: "Fernet master key held out-of-band by the operator. Every tenant's social tokens, ad keys, and MCP credentials sit encrypted at rest with a per-org data key.",
      },
      {
        icon: ShieldCheck,
        title: "Approval Inbox · 4-eye rule",
        body: "Every outbound action waits for human consent. Sensitive classes require two distinct approvers. Full reasoning trace attached to every request.",
      },
      {
        icon: GitBranch,
        title: "Audit & reasoning replay",
        body: "Append-only audit log. Per-agent-run reasoning trace replay surfaces exactly which model was called, with what tools, in what order.",
      },
    ],
  },
  {
    eyebrow: "Content pipeline",
    title: "From brief to launch — in one flow.",
    description:
      "Brand kit in. Brief in. Variants, hooks, headlines, repurposed clips, scheduled posts, and a published landing page out — without leaving the supervised loop.",
    features: [
      {
        icon: Sparkles,
        title: "Creatives Agent",
        body: "Brief in, N variants out: text plus image. Brand-voice linted against your don't-say list and refined automatically before reaching the inbox.",
      },
      {
        icon: ImageIcon,
        title: "Brand Kit & Voice",
        body: "Versioned palette, fonts, voice sliders, do/don't-say lists, audience personas. Injected into every agent prompt so every output sounds like you.",
      },
      {
        icon: Workflow,
        title: "Repurposing Engine",
        body: "One asset becomes a thread, a carousel, a clip, a newsletter snippet. Channel-aware, format-aware, length-aware.",
      },
      {
        icon: Layers,
        title: "Variants A/B + Hooks Lab",
        body: "Generate competing variants. Run them against your audience. Promote the winner — soon automatically via the auto-optimizer bandit.",
      },
    ],
  },
  {
    eyebrow: "Publishing",
    title: "Every channel. One scheduler.",
    description:
      "Thirteen channel adapters live today, plus email sequences, drip flows, and paid-media drafts. Approve once; agents fire on cadence.",
    features: [
      {
        icon: Calendar,
        title: "Calendar & Scheduler",
        body: "Per-project calendar, drag-and-drop scheduling, conflict detection, recurring posts, time-zone aware.",
      },
      {
        icon: Megaphone,
        title: "13 social channels",
        body: "X, LinkedIn, Instagram, Facebook, YouTube, TikTok, Threads, Substack, Bluesky, Reddit, Pinterest, Discord, Mastodon — all wired through OAuth 2.0.",
      },
      {
        icon: Mail,
        title: "Email sequences",
        body: "Resend, Postmark, or SendGrid. Drip flows with delay and branch conditions, tracking, unsubscribe, GDPR-aware.",
      },
      {
        icon: BarChart3,
        title: "Ads publisher",
        body: "Meta, LinkedIn, and Google Ads paused-campaign drafts. A human always approves the launch — no campaign goes live without you.",
      },
    ],
  },
];

function FeatureGroupBlock({ group }: { group: FeatureGroup }) {
  return (
    <div className="mb-24">
      <div className="max-w-3xl mb-12">
        <div className="inline-block text-xs font-bold uppercase tracking-[0.18em] text-[var(--dk-purple-700)] bg-[var(--dk-purple-100)] px-3 py-1 rounded-full mb-4">
          {group.eyebrow}
        </div>
        <h3 className="text-4xl sm:text-5xl font-bold leading-tight tracking-tight text-[var(--dk-ink)]">
          {group.title}
        </h3>
        <p className="mt-4 text-lg text-[var(--dk-fg-2)] leading-relaxed">
          {group.description}
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {group.features.map((f) => {
          const Icon = f.icon;
          return (
            <div
              key={f.title}
              className="group rounded-2xl border border-[var(--dk-border)] bg-white p-6 hover:border-[var(--dk-purple-300)] hover:shadow-lg hover:shadow-[var(--dk-purple-100)]/50 transition"
            >
              <div className="w-11 h-11 rounded-xl bg-[var(--dk-purple-100)] text-[var(--dk-purple-700)] flex items-center justify-center mb-4 group-hover:bg-[var(--dk-purple-700)] group-hover:text-white transition">
                <Icon className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-[var(--dk-ink)] text-lg tracking-tight">{f.title}</h4>
              <p className="mt-1.5 text-[var(--dk-fg-2)] text-[15px] leading-relaxed">{f.body}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Features() {
  return (
    <section id="features" className="bg-white py-24 sm:py-32">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-20">
          <div className="inline-block text-xs font-bold uppercase tracking-[0.18em] text-[var(--dk-purple-700)] bg-[var(--dk-purple-100)] px-3 py-1 rounded-full mb-4">
            What it does
          </div>
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-tight">
            A full marketing function,{" "}
            <span className="text-[var(--dk-purple-700)]">supervised by you</span>.
          </h2>
          <p className="mt-5 text-lg text-[var(--dk-fg-2)] leading-relaxed">
            Three layers: a hardened foundation, a content pipeline that turns briefs
            into launches, and a publisher that reaches every channel — with you in the
            loop on every external action.
          </p>
        </div>
        {groups.map((g) => (
          <FeatureGroupBlock key={g.title} group={g} />
        ))}
      </div>
    </section>
  );
}

function AgentsSection() {
  const agents = [
    { name: "Conductor", role: "Multi-agent orchestrator. Decomposes briefs. Routes work.", color: "from-violet-500 to-fuchsia-500" },
    { name: "Creatives", role: "Brief → text + image variants. Brand-voice linted.", color: "from-pink-500 to-rose-500" },
    { name: "SMM", role: "Schedules and adapts content per channel & cadence.", color: "from-amber-500 to-orange-500" },
    { name: "SEO", role: "Keyword pipeline. Internal links. Ranking-delta tracker.", color: "from-emerald-500 to-teal-500" },
    { name: "Paid Media", role: "Drafts ad sets across Meta / LinkedIn / Google.", color: "from-blue-500 to-cyan-500" },
    { name: "Analyst", role: "3σ anomaly detection. Monday-morning narrative reports.", color: "from-indigo-500 to-violet-500" },
    { name: "Inbox", role: "Triages incoming threads + automation triggers.", color: "from-slate-500 to-zinc-500" },
    { name: "Reviewer", role: "Sign-off gate for 4-eye-rule approvals.", color: "from-purple-500 to-violet-500" },
  ];
  return (
    <section id="agents" className="bg-[var(--dk-bg-tint)] py-24 sm:py-32 border-y border-[var(--dk-border)]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-block text-xs font-bold uppercase tracking-[0.18em] text-[var(--dk-purple-700)] bg-[var(--dk-purple-100)] px-3 py-1 rounded-full mb-4">
            Agent fleet
          </div>
          <h2 className="text-4xl sm:text-5xl font-bold tracking-tight leading-tight">
            Eight specialists, one Conductor.
          </h2>
          <p className="mt-5 text-lg text-[var(--dk-fg-2)] leading-relaxed">
            Each role-agent has a curated system prompt, its own model assignments, its
            own trust posture, and its own audit trail. The Conductor decomposes a brief
            and routes work across the fleet.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {agents.map((a) => (
            <div
              key={a.name}
              className="rounded-2xl bg-white border border-[var(--dk-border)] p-5 hover:shadow-md hover:-translate-y-0.5 transition"
            >
              <div
                className={`w-10 h-10 rounded-xl bg-gradient-to-br ${a.color} flex items-center justify-center text-white mb-4 shadow-sm`}
              >
                <Bot className="w-5 h-5" />
              </div>
              <div className="font-bold text-[var(--dk-ink)] tracking-tight">{a.name}</div>
              <p className="mt-1 text-sm text-[var(--dk-fg-2)] leading-relaxed">{a.role}</p>
            </div>
          ))}
        </div>

        <div className="mt-16 grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="rounded-2xl bg-white border border-[var(--dk-border)] p-7">
            <Cpu className="w-7 h-7 text-[var(--dk-purple-700)]" />
            <h4 className="mt-4 font-bold text-lg tracking-tight">Model Registry</h4>
            <p className="mt-1.5 text-[var(--dk-fg-2)] text-[15px] leading-relaxed">
              26 provider types. Auto-discovery + capability heuristic. Health-check beat
              every five minutes. Free-tier filter and pricing-aware selection.
            </p>
          </div>
          <div className="rounded-2xl bg-white border border-[var(--dk-border)] p-7">
            <GitBranch className="w-7 h-7 text-[var(--dk-purple-700)]" />
            <h4 className="mt-4 font-bold text-lg tracking-tight">Resolver chain</h4>
            <p className="mt-1.5 text-[var(--dk-fg-2)] text-[15px] leading-relaxed">
              user → org → pool → env → stub. Every agent call follows this precedence
              so individual operators can override organization defaults.
            </p>
          </div>
          <div className="rounded-2xl bg-white border border-[var(--dk-border)] p-7">
            <Activity className="w-7 h-7 text-[var(--dk-purple-700)]" />
            <h4 className="mt-4 font-bold text-lg tracking-tight">Cost ledger</h4>
            <p className="mt-1.5 text-[var(--dk-fg-2)] text-[15px] leading-relaxed">
              Every model call is logged with token counts, latency, and USD cost.
              Per-run cost cap evaluator refuses runs that would blow your retainer.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function IntegrationsSection() {
  const categories = [
    { name: "CRM", items: ["HubSpot", "Salesforce", "Pipedrive", "Attio"] },
    { name: "Analytics", items: ["GA4", "Mixpanel", "PostHog"] },
    { name: "Productivity", items: ["Slack", "Notion", "Google Drive", "Discord"] },
    { name: "SEO", items: ["Ahrefs"] },
    { name: "CMS", items: ["Webflow", "WordPress", "Ghost"] },
    { name: "Payments", items: ["Stripe", "QuickBooks"] },
    { name: "Generation", items: ["Replicate", "Runway", "Suno", "ElevenLabs", "Cartesia", "Deepgram", "fal.ai"] },
    { name: "AI Providers", items: ["Anthropic", "OpenAI", "Gemini", "Bedrock", "Mistral", "Groq", "OpenRouter", "Ollama"] },
  ];
  return (
    <section id="integrations" className="bg-white py-24 sm:py-32">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-block text-xs font-bold uppercase tracking-[0.18em] text-[var(--dk-purple-700)] bg-[var(--dk-purple-100)] px-3 py-1 rounded-full mb-4">
            MCP Integration Hub
          </div>
          <h2 className="text-4xl sm:text-5xl font-bold tracking-tight leading-tight">
            One adapter spec.{" "}
            <span className="text-[var(--dk-purple-700)]">Every external surface.</span>
          </h2>
          <p className="mt-5 text-lg text-[var(--dk-fg-2)] leading-relaxed">
            Every integration plugs in as an MCP server. Agents read and write through one
            consistent permissioned layer — and operators bring their own MCPs via the
            marketplace.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {categories.map((c) => (
            <div
              key={c.name}
              className="rounded-2xl bg-[var(--dk-bg-tint)] border border-[var(--dk-border)] p-5"
            >
              <div className="flex items-center gap-2 mb-3">
                <Network className="w-4 h-4 text-[var(--dk-purple-700)]" />
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--dk-purple-800)]">
                  {c.name}
                </span>
              </div>
              <ul className="space-y-1.5">
                {c.items.map((i) => (
                  <li key={i} className="text-sm text-[var(--dk-fg-1)] font-medium flex items-center gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-[var(--dk-purple-400)]" /> {i}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="mt-10 text-center text-sm text-[var(--dk-fg-3)]">
          Plus BYO MCP marketplace · Webhook hub · OAuth 2.0 for every social channel
        </p>
      </div>
    </section>
  );
}

function LeadAudienceSection() {
  const blocks = [
    {
      icon: Users,
      title: "Lead 2.0",
      body: "Identity, enrichment, scoring, lifecycle stage (new → mql → sql → customer). Two-way CRM sync with HubSpot, Salesforce, Pipedrive, Attio.",
    },
    {
      icon: Database,
      title: "Segment builder",
      body: "AND/OR filter DSL. Nightly materializer. Sync segments back to ad-platform custom audiences automatically.",
    },
    {
      icon: BarChart3,
      title: "Attribution",
      body: "First-touch, last-touch, time-decay. Sankey view of the actual customer journey. Closed-loop revenue back to campaign.",
    },
    {
      icon: Search,
      title: "AEO scoring",
      body: "Answer Engine Optimisation: score every piece of content for visibility in LLM-driven answer engines. Fix suggestions included.",
    },
  ];
  return (
    <section className="bg-[var(--dk-bg-tint)] py-24 sm:py-32 border-y border-[var(--dk-border)]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-block text-xs font-bold uppercase tracking-[0.18em] text-[var(--dk-purple-700)] bg-[var(--dk-purple-100)] px-3 py-1 rounded-full mb-4">
            Audience &amp; revenue
          </div>
          <h2 className="text-4xl sm:text-5xl font-bold tracking-tight leading-tight">
            Close the loop on every dollar.
          </h2>
          <p className="mt-5 text-lg text-[var(--dk-fg-2)] leading-relaxed">
            Identify visitors. Score leads. Segment with a real DSL. Attribute revenue
            back to the campaign that earned it. And see what your content actually looks
            like to LLM-driven answer engines.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {blocks.map((b) => {
            const Icon = b.icon;
            return (
              <div
                key={b.title}
                className="rounded-2xl bg-white border border-[var(--dk-border)] p-7"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--dk-purple-600)] to-[var(--dk-purple-800)] text-white flex items-center justify-center shrink-0">
                    <Icon className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="font-bold text-lg tracking-tight">{b.title}</h4>
                    <p className="mt-1.5 text-[var(--dk-fg-2)] text-[15px] leading-relaxed">{b.body}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function GovernanceSection() {
  const points = [
    { icon: Eye, t: "Reasoning trace replay", b: "See every tool call an agent made. In order. With token counts and cost." },
    { icon: ShieldCheck, t: "Trust mode per action", b: "Hard-gate, soft-gate, or auto — set per action class, per org." },
    { icon: CheckCircle2, t: "4-eye sign-off", b: "Two distinct approvers required for sensitive classes. Configurable." },
    { icon: Lock, t: "Quota & cost caps", b: "Sliding-window quotas. Circuit breaker. Per-org monthly retainer budgets." },
  ];
  return (
    <section id="governance" className="bg-white py-24 sm:py-32">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="inline-block text-xs font-bold uppercase tracking-[0.18em] text-[var(--dk-purple-700)] bg-[var(--dk-purple-100)] px-3 py-1 rounded-full mb-4">
              Governance
            </div>
            <h2 className="text-4xl sm:text-5xl font-bold tracking-tight leading-tight">
              Built so a human always says yes — or no.
            </h2>
            <p className="mt-5 text-lg text-[var(--dk-fg-2)] leading-relaxed">
              Autonomy on tap, but never bypassed. Every external action clears the
              Approval Inbox before it fires. Every model call lands in an append-only
              ledger. Every agent reasoning thread can be replayed turn by turn.
            </p>
            <div className="mt-7 flex flex-wrap gap-2">
              {["GDPR-aware", "SOC2-ready", "Per-tenant encryption", "Audit-exportable"].map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[var(--dk-purple-100)] text-[var(--dk-purple-800)] text-xs font-semibold px-3 py-1.5"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> {t}
                </span>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {points.map((p) => {
              const Icon = p.icon;
              return (
                <div
                  key={p.t}
                  className="rounded-2xl border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] p-5"
                >
                  <Icon className="w-7 h-7 text-[var(--dk-purple-700)]" />
                  <div className="mt-3 font-bold tracking-tight">{p.t}</div>
                  <p className="mt-1 text-sm text-[var(--dk-fg-2)] leading-relaxed">{p.b}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

function DeploySection() {
  return (
    <section id="deploy" className="bg-[var(--dk-bg-tint)] py-24 sm:py-32 border-y border-[var(--dk-border)]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <div className="inline-block text-xs font-bold uppercase tracking-[0.18em] text-[var(--dk-purple-700)] bg-[var(--dk-purple-100)] px-3 py-1 rounded-full mb-4">
            Deploy
          </div>
          <h2 className="text-4xl sm:text-5xl font-bold tracking-tight leading-tight">
            Self-hosted. No data egress.
          </h2>
          <p className="mt-5 text-lg text-[var(--dk-fg-2)] leading-relaxed">
            Ship the platform as a Helm chart plus container images. Install on any
            Kubernetes cluster. Your data — and your customers' data — never leaves your
            perimeter.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            { icon: Server, t: "Helm + container images", b: "Helm chart at helm/ in the monorepo. GHCR-published images for backend and frontend." },
            { icon: Database, t: "Postgres + Redis + S3", b: "pgvector-equipped Postgres for relational + KG. Redis as cache and Celery broker. Any S3-compatible store for objects." },
            { icon: Activity, t: "Observability included", b: "OpenTelemetry traces. Grafana dashboards. Sentry tags on exceptions. Dependency-health endpoint out of the box." },
          ].map((b) => {
            const Icon = b.icon;
            return (
              <div key={b.t} className="rounded-2xl bg-white border border-[var(--dk-border)] p-7">
                <Icon className="w-8 h-8 text-[var(--dk-purple-700)]" />
                <h4 className="mt-4 font-bold text-lg tracking-tight">{b.t}</h4>
                <p className="mt-1.5 text-[var(--dk-fg-2)] text-[15px] leading-relaxed">{b.b}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section
      id="cta"
      className="relative overflow-hidden text-white"
      style={{
        background:
          "radial-gradient(circle at 12% 88%, var(--dk-purple-500) 0%, var(--dk-purple-700) 32%, var(--dk-purple-900) 80%)",
      }}
    >
      <div className="dk-grain absolute inset-0 pointer-events-none" />
      <div className="relative max-w-5xl mx-auto px-6 py-24 sm:py-32 text-center">
        <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-tight max-w-3xl mx-auto">
          A full marketing function — without losing the keys to the kingdom.
        </h2>
        <p className="mt-6 text-lg sm:text-xl text-white/80 max-w-2xl mx-auto leading-relaxed">
          Book a 30-minute demo. Bring a real brief. We&apos;ll show you a campaign go from
          PRD to scheduled launch, with you approving every step.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <a
            href="mailto:hello@dclaw.io?subject=DClaw%20Marketing%20demo"
            className="inline-flex items-center gap-2 rounded-full bg-white text-[var(--dk-purple-900)] px-7 py-3.5 font-semibold hover:bg-[var(--dk-purple-50)] transition shadow-xl"
          >
            Book a demo <ArrowRight className="w-4 h-4" />
          </a>
          <a
            href="https://github.com/dclawstack/dclaw-marketing"
            className="inline-flex items-center gap-2 rounded-full bg-white/10 border border-white/30 backdrop-blur-sm text-white px-7 py-3.5 font-semibold hover:bg-white/20 transition"
          >
            <Github className="w-4 h-4" /> See it on GitHub
          </a>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="bg-[var(--dk-purple-900)] text-white/70">
      <div className="max-w-7xl mx-auto px-6 py-14">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2.5">
              <img
                src="/brand/logos/dclaw-icon-white.svg"
                alt=""
                width={36}
                height={36}
                className="w-9 h-9"
              />
              <span className="font-bold text-white text-lg tracking-tight">DClaw Marketing</span>
            </div>
            <p className="mt-4 text-sm leading-relaxed max-w-md">
              An agent-driven marketing operating system. Self-hosted, MCP-first, with a
              human-in-the-loop on every outbound action. Built for operators who refuse
              to give up control to ship faster.
            </p>
          </div>
          <div>
            <h5 className="text-xs uppercase tracking-wider text-white font-bold mb-3">Product</h5>
            <ul className="space-y-2 text-sm">
              <li><a href="#features" className="hover:text-white transition">Features</a></li>
              <li><a href="#agents" className="hover:text-white transition">Agents</a></li>
              <li><a href="#integrations" className="hover:text-white transition">Integrations</a></li>
              <li><a href="#deploy" className="hover:text-white transition">Deploy</a></li>
            </ul>
          </div>
          <div>
            <h5 className="text-xs uppercase tracking-wider text-white font-bold mb-3">Connect</h5>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="https://github.com/dclawstack/dclaw-marketing" className="hover:text-white transition inline-flex items-center gap-1.5">
                  <Github className="w-3.5 h-3.5" /> GitHub
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition inline-flex items-center gap-1.5">
                  <Linkedin className="w-3.5 h-3.5" /> LinkedIn
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition inline-flex items-center gap-1.5">
                  <XIcon className="w-3.5 h-3.5" /> X / Twitter
                </a>
              </li>
              <li>
                <a href="mailto:hello@dclaw.io" className="hover:text-white transition inline-flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5" /> hello@dclaw.io
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="mt-12 pt-6 border-t border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-xs">
          <div>© 2026 DClaw Marketing — All rights reserved.</div>
          <div className="text-white/50">Self-hosted · MCP-first · v1.1.2</div>
        </div>
      </div>
    </footer>
  );
}

export default function HomePage() {
  return (
    <main className="flex-1">
      <NavBar />
      <Hero />
      <LogoStrip />
      <Features />
      <AgentsSection />
      <IntegrationsSection />
      <LeadAudienceSection />
      <GovernanceSection />
      <DeploySection />
      <CTASection />
      <Footer />
    </main>
  );
}
