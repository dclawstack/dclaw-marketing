# DKube Design System

A design system extracted from **dkube.io** — the marketing site for DKube, an enterprise Private AI company.

## What DKube does

DKube (a product of **One Convergence**) designs and delivers **secure Private AI solutions** for enterprises across on-prem, private cloud, and hybrid environments. The brand emphasises three pillars: **Private AI · Enterprise Trust · Scalable Delivery**, and a **12-week** "experimentation to production" delivery commitment.

### Products & surfaces represented
- **Marketing site** (`dkube.io`) — Webflow-built, the single visual source for this design system.
- **Platforms** referenced (no public UI surfaces inspected): `DKubeX` (GenAI ModelOps) and `DKube` (MLOps).
- **AI Blueprints** as solution templates: `QueriLynx` (multi-agent data exploration), `Virtual Teaching Assistant`, `DocMind` (document intelligence).
- **Audience:** enterprise CIOs / heads of AI / platform engineering. Logos shown include VMware, Cisco, Fungible, Altos Labs, Apollo, TIAA, StackPath.

### Sources
- Marketing site: <https://dkube.io>
- Brand-supplied logo set (purple wordmark, white wordmark, purple icon, white icon) provided directly by the team.
- Product docs (linked, not used as visual reference): <https://docs.dkube.io>

> No codebase, Figma file, or slide template was attached for this build. All tokens were derived from the public marketing site and brand-mark SVG. **Anywhere a value is implied rather than confirmed it is flagged below.**

---

## Index

| File | What's in it |
|---|---|
| `README.md` | This document — overview, content + visual foundations, iconography, manifest |
| `BRAND_GUIDELINES.md` | Full brand guidelines — voice, logo, color, type, imagery, motion, legal |
| `SKILL.md` | Agent SKill front-matter for Claude Code / skill-based use |
| `colors_and_type.css` | Color, type, spacing, radius, shadow, motion tokens + semantic classes |
| `assets/` | Brand mark, customer logos, marketing imagery, navigational icons |
| `preview/` | Small HTML cards rendered into the project's Design System tab |
| `ui_kits/marketing-site/` | React recreation of dkube.io's marketing surfaces |
| `slides/` | Fifteen master slide layouts (incl. four architecture-diagram masters) + `SLIDE_GUIDE.md` + `arch-diagrams.css` |

---

## CONTENT FUNDAMENTALS

DKube speaks to **enterprise buyers who value control, compliance, and outcomes** over hype. Copy is confident, plain-spoken, and lightly aspirational — never clever, never casual.

### Voice & tone
- **Authoritative, calm, outcome-led.** Sentences are short and load-bearing.
- **No marketing slang, no exclamation marks.** No "unleash," no "supercharge," no "🚀."
- **Pronouns:** "we" for DKube, "you / your enterprise" for the reader. First-person plural shows up in commitments ("Our 12-Weeks Commitment").
- **Tense:** active present. ("DKube **helps** enterprises design, deploy, and scale…")

### Casing
- **Title Case** for section headings, page titles, button labels, product names: *"How Enterprises Operationalize AI. Confidently."*, *"Built by Engineers Who Understand Enterprise AI"*.
- **Sentence case** for descriptive subcopy and FAQ answers.
- Product names are exact-case: **DKube**, **DKubeX**, **QueriLynx**, **DocMind** — never `Dkube` or `dkubex`.
- Eyebrow labels above sections are short, **Title Case** category words: *Videos · Partners · News & Events*.

### Recurring phrases / vocabulary
- *Private AI · Enterprise-grade · Production-ready · Audit & Compliance Ready*
- *Govern Your AI Expense and Data Residency*
- *Discover · Explore · Watch Video · Read White Paper · Talk to Us*
- *Blueprints · Platforms · Case Studies · Resources*
- *Secure, private, on-prem, hybrid, governed, sovereign*

### Punctuation & rhythm
- **Em dashes** for hard pivots: *"…across on-prem, private cloud, and hybrid environments – without compromising control, compliance, or ownership."*
- **Period-stop one-liners** as headlines: *"Built by Engineers Who Understand Enterprise AI."* / *"How Enterprises Operationalize AI. Confidently."*
- Oxford commas, US spelling.

### Emoji & decoration
- **No emoji anywhere.** This is enterprise B2B. Don't add them.
- No exclamation marks. No ALL-CAPS shouting (eyebrows are the only uppercase moment).
- No "AI-generated voice" tells (no "Imagine if…", no "In today's world…").

### CTAs
- Primary CTA: **Talk to Us** / **Contact Us** — paired with a small ↗ arrow icon.
- Tertiary CTA: **Explore** with a right-arrow `→`.
- Resource CTAs: **Watch Video**, **Read White Paper**, **Read Case Study**.

---

## VISUAL FOUNDATIONS

DKube's visual identity is **enterprise-grade minimalism with one distinctive purple**. It reads as serious, not playful; quiet, not loud. The brand restrains itself: one accent color, one strong display weight, one shape vocabulary (rounded rectangles + capsule pills).

### Color
- **Primary:** `#7660A8` purple (the dark face of the cube logo). Used for links, primary CTAs, eyebrow text, and accent fills.
- **Secondary:** `#9384BD` light purple (the bright face of the cube). Used for soft backgrounds, gradient blends, decorative accents.
- **Surface:** `#FFFFFF` page; `#F8F8FA` muted; `#F8F6FB` faintly purple-tinted hero washes.
- **Ink:** `#0F0F12` near-black for headlines, `#404049` for body, `#7A7A85` for meta.
- **Imagery tone:** warm, photographic, daylight. Construction sites, classrooms, document close-ups, lab benches. **No icy blues, no synthetic gradients, no AI-slop renders.**

### Typography
- **Single family: Poppins** (Google Fonts) for both display and body. Confirmed by the brand team.
- Heavy weights `700–800` for hero/section heads; `500` for UI labels, `600` for buttons, `400` for body.
- **Hierarchy is built with weight + size**, never italic, never colored body text. Headlines are `-0.025em` tracked tight, body is loose `1.65` line height.

### Backgrounds
- Predominantly **flat white** with the occasional **soft purple tint** (`--dk-purple-50`).
- Hero sections layer photographic imagery behind a darkened scrim with white type.
- **No repeating patterns, no textures, no grain, no hand-drawn illustrations.**
- Subtle one-color gradients sometimes appear inside cards (purple-700 → purple-500), never on the page background.

### Borders & corners
- **Borders:** 1px hairlines in `--dk-gray-200`. Used sparingly — to outline form fields and cards on light surfaces.
- **Corner radii:** the design uses two registers — `16px` for cards / blueprint tiles, and a full **999px pill** for buttons and tag chips. No sharp 0px corners anywhere except imagery edges in some compositions.

### Cards
- White surface, 1px border (`--dk-border`), `16–24px` radius, **soft shadow** (`--dk-shadow-sm`) that lifts to `--dk-shadow-md` on hover.
- A category eyebrow row of small purple chips sits above the title.
- Image-led cards bleed photography to the top edge with the radius preserved.

### Shadows
- Soft, very low-opacity, neutral (no colored shadows except brand CTAs).
- `--dk-shadow-md` (`0 8px 20px rgba(15,15,18,0.08)`) is the default elevation; `--dk-shadow-brand` adds a faint purple cast under primary buttons on hover.

### Hover & press
- **Buttons:** background darkens one step (`brand` → `brand-hover` → `brand-press`); arrow icon nudges `+2px / -2px` (translateX & Y).
- **Links:** color stays, an underline animates in from left.
- **Cards:** lift 2–4px, shadow grows from `sm` to `md`, border tints slightly toward purple.
- **Press:** scale `0.98`, transition `120ms`.

### Animation
- Restrained. Marketing motion is **fade + 12px translate-Y** on scroll-in.
- Looping marquee for the customer-logo strip.
- **Easing:** `cubic-bezier(0.22, 1, 0.36, 1)` (out-quart). No bounces, no overshoots.
- **Durations:** `150ms` micro-interactions, `240ms` standard, `420ms` larger entrances.

### Transparency & blur
- Used **only** on the sticky top nav (white `rgba(255,255,255,0.85)` + `backdrop-filter: blur(12px)`) and on hero image scrims.
- No glassmorphism panels in product/marketing surfaces.

### Layout
- Max content width **`1280px`**, gutters `24px` on desktop / `16px` mobile.
- 12-column implicit grid; section spacing `96–128px` desktop.
- Sticky header (~72px), fixed-position scroll-to-top button bottom-right is the only persistent fixed element.

---

## ICONOGRAPHY

- **No built-in icon font.** Icons on dkube.io are **individually authored SVGs** delivered through Webflow's CDN; weights are inconsistent (some 1.5px stroke, some filled).
- **Real assets copied into `assets/`:**
  - `arrow-top-right.png` / `arrow-icon.svg` — directional arrows used on every CTA
  - `round-arrow-right.svg` — circular arrow on case-study cards
  - `menu-icon.svg`, close-cross
  - `icon-magic.svg`, `icon-trust.svg`, `icon-scalable.svg` — the three-pillar feature row
  - `icon-call.svg`, `icon-sms.svg`, `icon-marker.webp` — footer contact glyphs
  - `si-linkedin.svg`, `si-twitter.svg`, `si-insta.svg` — social icons
- **For new product UI surfaces** (where the marketing site has no precedent): use **Lucide** via CDN — its 1.5px stroke matches the brand's directional arrows. Substitution is flagged. `<script src="https://unpkg.com/lucide@latest"></script>` then `<i data-lucide="arrow-up-right"></i>`.
- **Emoji:** never. **Unicode glyphs as icons:** never. **Hand-rolled SVGs:** only for primitives (chevrons, arrows) when copying isn't possible.
- Logos for customers (VMware, Cisco, Fungible, Altos Labs) are stored as `assets/logo-*.svg` and rendered desaturated/monochrome in the trust strip.

---

## Caveats & open questions
1. **Product UI is out of scope** by user direction — this system covers the marketing site and slide masters only.
2. **Slide masters** were derived from three source decks (DKubeX 2.0 Introduction, DKube Executive Overview, DKubeX 2.0 Architecture Diagrams) — see `slides/SLIDE_GUIDE.md` for full reference.
3. **Chart styling** for data viz (bar / line / donut) is not yet covered by a dedicated master.
