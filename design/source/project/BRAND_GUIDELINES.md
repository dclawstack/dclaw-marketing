# DKube Brand Guidelines

A working brand book for DKube — a wholly-owned subsidiary and DBA brand of **One Convergence, Inc.** Sources: dkube.io home page, dkube.io/about-us, and the DocMind blog post. Voice samples and boilerplate are quoted verbatim from those pages.

---

## Design System Overview

DKube (a product of **One Convergence**) designs and delivers **secure Private AI solutions** for enterprises across on-prem, private cloud, and hybrid environments. The brand emphasises three pillars: **Private AI · Enterprise Trust · Scalable Delivery**, and a **12-week** "experimentation to production" delivery commitment.

### Products & surfaces

- **Marketing site** (`dkube.io`) — Webflow-built, the single visual source for this design system.
- **Platforms** referenced: `DKubeX` (GenAI ModelOps) and `DKube` (MLOps).
- **AI Blueprints:** `QueriLynx` (multi-agent data exploration), `Virtual Teaching Assistant`, `DocMind` (document intelligence).
- **Audience:** enterprise CIOs / heads of AI / platform engineering. Logos shown include VMware, Cisco, Fungible, Altos Labs, Apollo, TIAA, StackPath.

> No codebase, Figma file, or slide template was attached for this build. All tokens were derived from the public marketing site and brand-mark SVG. Anywhere a value is implied rather than confirmed it is flagged in the relevant section below.

### File index

| File | What's in it |
|---|---|
| `BRAND_GUIDELINES.md` | This document — full brand book (voice, logo, color, type, imagery, motion, legal) |
| `SKILL.md` | Claude Code skill front-matter |
| `colors_and_type.css` | Color, type, spacing, radius, shadow, motion tokens + semantic classes |
| `assets/` | Brand mark, customer logos, marketing imagery, navigational icons |
| `preview/` | Small HTML cards rendered into the project's Design System tab |
| `ui_kits/marketing-site/` | React recreation of dkube.io's marketing surfaces |
| `slides/` | Fifteen master slide layouts + `SLIDE_GUIDE.md` + `arch-diagrams.css` |

### Iconography

- **No built-in icon font.** Icons on dkube.io are individually authored SVGs; weights are inconsistent (some 1.5px stroke, some filled).
- **Real assets copied into `assets/`:** `arrow-top-right.png`, `arrow-icon.svg`, `round-arrow-right.svg`, `menu-icon.svg`, `icon-magic.svg`, `icon-trust.svg`, `icon-scalable.svg`, `icon-call.svg`, `icon-sms.svg`, `icon-marker.webp`, social icons (`si-linkedin.svg`, `si-twitter.svg`, `si-insta.svg`).
- **For new product UI surfaces:** use **Lucide** — its 1.5px stroke matches the brand's directional arrows. `<script src="https://unpkg.com/lucide@latest"></script>`.
- **Never:** emoji, unicode glyphs as icons, or hand-rolled SVGs except for simple primitives.

### Caveats

1. **Product UI is out of scope** by user direction — this system covers the marketing site and slide masters only.
2. **Slide masters** were derived from three source decks (DKubeX 2.0 Introduction, DKube Executive Overview, DKubeX 2.0 Architecture Diagrams) — see `slides/SLIDE_GUIDE.md` for full reference.
3. **Chart styling** for data viz is not yet covered by a dedicated master.

---

## 1 · Company

DKube is an enterprise AI platform company that helps organizations design, deploy, and operate **Private AI** systems across on-premises, private cloud, and hybrid environments. The brand is built around enabling enterprises to take AI **from experimentation to production** — securely, compliantly, and at scale.

- **Legal entity:** One Convergence, Inc. (San Francisco Bay Area)
- **Brand name:** DKube · **Always written exactly as "DKube"** — never "Dkube," "DKUBE," or "D-Kube."
- **Product names (exact case):** DKube, DKubeX, QueriLynx, DocMind, Virtual Teaching Assistant.
- **Tagline (footer-standard):** *"Designing and delivering secure Private AI solutions for enterprises."*
- **Headquarters:** 99 Almaden Blvd #600, San Jose, CA 95113 · +1 408 430 2503
- **AI Excellence Centre:** KRB Towers, Madhapur, Hyderabad 500081, India · +91 40 4821 4999
- **Contact:** info@dkube.io
- **Socials:** LinkedIn `/company/dkube-ai/` · X `@DKube_AI` · Instagram `@dkube_ai`
- **Copyright line:** ©2026 One Convergence. All Rights Reserved.

---

## 2 · Brand Pillars

Three pillars carry every page, deck, and post:

| Pillar | What it means |
|---|---|
| **Integrity** | Privacy first. Data, governance, and ownership stay with the customer by default. |
| **Diversity** | Enterprise-forward. Solutions account for every stakeholder — innovation balanced with reliability and operability. |
| **Innovation** | Open-source first. Best-in-class open ecosystems integrated into enterprise-ready solutions. |

Boilerplate framings used across the site:
- **Mission line:** *"Security. Scalability. Privacy."*
- **Values line:** *"Private. Secure. All in Your Control."*
- **Outcome line:** *"From experimentation to enterprise-grade, production-ready AI in weeks."*

---

## 3 · Voice & Tone

### 3.1 · Principles
1. **Outcome-led, not hype-led.** Lead with what the enterprise gets, not what the technology is.
2. **Plain English, technical precision.** Use the right words (governance, residency, residency, hybrid, on-prem) without dressing them up.
3. **Calm confidence.** No exclamation marks. No "supercharge." No "🚀."
4. **Specific over general.** "12 weeks," "80 engineers," "on-premises and hybrid environments" — concrete numbers and surfaces beat abstractions.
5. **First-person plural.** "We" for DKube; "you / your enterprise" for the reader.

### 3.2 · Voice samples (verbatim)

> "DKube enables global enterprises to move AI from experimentation to production by designing and delivering secure, scalable AI solutions across on-premises and hybrid environments – helping teams focus on building next-generation AI systems that solve complex, real-world problems."

> "Built by engineers with deep experience in infrastructure, security, and AI systems, DKube addresses one of the hardest challenges enterprises face today: operationalizing AI without compromising data ownership, governance, or performance."

> "From user-defined document header configuration to automated processing, color-coded document splits, and cross-document field comparison, DKube DocMind empowers teams to process high-volume loan documentation faster while maintaining accuracy and control."

These three paragraphs are the **canonical voice reference** — match their cadence, sentence length, and vocabulary when generating new copy.

### 3.3 · Casing
- **Title Case** for headings, page titles, button labels, product names: *"Building Enterprise AI You Can Trust"*, *"How Enterprises Operationalize AI. Confidently."*
- **Sentence case** for descriptive subcopy and FAQ answers.
- Short Title-Case eyebrow labels above sections: *Videos · Partners · Use Cases · Knowledge Hub*.

### 3.4 · Punctuation rhythm
- **Em dashes** for hard pivots: *"…across on-premises and hybrid environments – without compromising control, compliance, or ownership."*
- **Period-stop one-liners** as headlines: *"Built by Engineers Who Understand Enterprise AI."* / *"Integrity. Diversity. Innovation."*
- **Oxford commas. US spelling. No exclamation marks.**

### 3.5 · Vocabulary

| Use | Avoid |
|---|---|
| Private AI · Enterprise AI · Generative AI · MLOps · GenAI ModelOps | "Cutting-edge AI" · "Next-gen AI" (without specifics) |
| On-premises · Private cloud · Hybrid · Sovereign · Air-gapped | "The cloud" (too vague) |
| Governance · Compliance · Audit-ready · Data residency · Data ownership | "Bulletproof" · "Iron-clad" |
| Production-ready · Operationalize · Deploy · Operate · At scale | "Unleash" · "Supercharge" · "Revolutionize" |
| Secure by default · Privacy first | "Zero trust" (without context) |
| 12-week delivery · Discovery → MVP → Pilot → Refinement → Deployment | "Lightning-fast" · "Instant" |

### 3.6 · CTA library

| Tier | Label |
|---|---|
| **Primary** | Talk to Us · Talk to DKube · Contact Us |
| **Secondary** | Explore · Learn More · Our 12-Weeks Commitment |
| **Resource** | Watch Video · Read White Paper · Read Case Study |
| **Section enter** | Discover · Visit `<partner>` |

---

## 4 · Logo

DKube ships in **four official lockups** (in `assets/`):

| File | Use |
|---|---|
| `dkube-logo-purple.svg` | Primary wordmark — light backgrounds (white, `--dk-gray-50`, `--dk-purple-50`) |
| `dkube-logo-white.svg` | Reverse wordmark — dark backgrounds, photo scrims, brand-colored fields |
| `dkube-icon-purple.svg` | App icon / favicon / avatar — light surfaces |
| `dkube-icon-white.svg` | App icon — dark surfaces |

### 4.1 · Construction
The mark is a three-face cube — **dark face `#7660A8`**, **light face `#9384BD`**, **plinth `#D6D6D6`** — paired with the wordmark "Dkube" set in Poppins ExtraBold and capped by the trademark glyphs (T·M).

### 4.2 · Rules
- **Aspect ratio is locked.** Always scale uniformly. Never stretch, squash, or distort.
- **Use the supplied SVG.** Do not redraw, recolor, re-letter, or re-kern the wordmark.
- **Clear space:** keep a margin equal to the height of the cube's top face on all sides.
- **Minimum size:** 24px tall for the icon, 96px wide for the wordmark in digital; 8mm tall / 25mm wide in print.
- **On photography:** use `dkube-logo-white.svg` over a dark scrim (≥50% black at the logo position). Never place the purple wordmark on a busy or low-contrast photo.
- **Co-branding:** when paired with a partner logo, separate by a 1px `--dk-border` divider and match optical height — not pixel height. DKube sits left for partner-of pages, right for "delivered with" attributions.
- **Don't:** add shadows, glows, outlines, gradients, or animation to the mark. Don't fill the cube faces with imagery.

---

## 5 · Color

### 5.1 · Primary
| Token | Hex | Use |
|---|---|---|
| `--dk-purple-700` (Brand) | `#7660A8` | Primary CTAs, links, eyebrows, accents, dark cube face |
| `--dk-purple-500` | `#9384BD` | Light cube face, gradient pairing, decorative accents |
| `--dk-gray-300` | `#D6D6D6` | Cube plinth, dividers |

### 5.2 · Surfaces
- White is the default page surface. `--dk-gray-50` (`#F8F8FA`) is the muted alternate. `--dk-purple-50` (`#F8F6FB`) is the only tinted wash and is reserved for hero halos and section breaks.
- **Inverse:** `--dk-ink` (`#0F0F12`) for the final-CTA capsule and footer-CTA blocks.

### 5.3 · Do's & don'ts
- **Do** keep purple to one role per layout (CTA *or* accent — not both at once).
- **Do** use `--dk-purple-700` for body links; never the lighter `500`.
- **Don't** use `--dk-purple-500` as a primary CTA color — it lacks contrast on white (3.4:1).
- **Don't** introduce new purples outside the scale.
- **Don't** combine purple gradients with photography backgrounds; pick one.

### 5.4 · Accessibility pairings
| Foreground | Background | Ratio | OK? |
|---|---|---|---|
| `--dk-ink` `#0F0F12` | white | 19.4 : 1 | ✓ |
| `--dk-gray-700` `#404049` | white | 10.7 : 1 | ✓ |
| `--dk-purple-700` `#7660A8` | white | 5.4 : 1 | ✓ AA normal text |
| white | `--dk-purple-700` `#7660A8` | 5.4 : 1 | ✓ AA normal text |
| `--dk-purple-500` `#9384BD` | white | 3.4 : 1 | ✗ — large text only |

### 5.5 · Semantic / status
Reserved for product UI surfaces: success `#2E8B57`, warning `#C28A00`, danger `#B3261E`, info `#2C6CB0`. Marketing surfaces should not use these as decorative colors.

### 5.6 · Data-viz palette (proposed)
For charts, use the following categorical scale derived from the brand:

`#7660A8 · #9384BD · #2C6CB0 · #2E8B57 · #C28A00 · #B3261E · #5C4A8E`

Sequential ramp (light → dark): `#F1EEF8 · #C9C0DE · #9384BD · #7660A8 · #4A3878`.

---

## 6 · Typography

### 6.1 · Family
**Poppins** (Google Fonts) for everything — display and body. Six weights are bundled locally in `/fonts/`: 300, 400, 500, 600, 700, 800.

### 6.2 · Hierarchy

| Role | Family · Weight · Size | Tracking · Leading |
|---|---|---|
| H1 / Hero display | Poppins 800 · 56–120px (clamped) | -0.03em · 0.98 |
| H2 / Section head | Poppins 700 · 32–56px (clamped) | -0.02em · 1.10 |
| H3 / Subsection | Poppins 700 · 32px | -0.015em · 1.15 |
| H4 / Card title | Poppins 600 · 24px | normal · 1.15 |
| H5 / List head | Poppins 600 · 20px | normal · 1.15 |
| Lead | Poppins 400 · 20px | normal · 1.55 |
| Body | Poppins 400 · 16px | normal · 1.65 |
| Meta | Poppins 500 · 14px | normal · 1.50 |
| Caption | Poppins 500 · 12px | 0.02em · 1.50 |
| Eyebrow | Poppins 600 · 14px UPPERCASE | 0.04em · 1.50 |

### 6.3 · Rules
- **No italic.** No oblique. No condensed/expanded. No font-stretch.
- **No colored body text** — body is `--dk-gray-700`. Color is for headings, CTAs, links only.
- **One typeface only.** Don't introduce a second display family (Manrope, Inter, etc.).

---

## 7 · Imagery

The DKube image style is **warm photographic, daylight, and human**.

### 7.1 · Categories actively used
- **Industry verticals** in real environments: mortgage paperwork on a desk, construction sites, classrooms, lab benches, document close-ups.
- **Team & culture:** candid, unposed group photographs from the Hyderabad and San Jose offices.
- **Headshots:** plain-background, eye-level portraits for executive and board cards.

### 7.2 · Direction
- **Tone:** warm, neutral white balance. Avoid icy blues and saturated oversaturation.
- **Light:** natural daylight or soft office light. Avoid hard studio strobes.
- **Composition:** generous negative space — DKube layouts often crop wide and overlay small chips.
- **Subject:** humans + their work. Documents, screens in context, hands at keyboards.

### 7.3 · Don'ts
- **No AI-generated stock.** No glossy 3D renders of brains, neurons, or "AI cubes."
- **No neon gradient tech imagery.** No purple-and-cyan circuit photography.
- **No hand-drawn illustrations.** The brand is photographic, not illustrated.
- **No emoji as imagery.**

---

## 8 · Iconography

- **Primary set:** the existing site icons (in `assets/`) — `icon-magic`, `icon-trust`, `icon-scalable` for the three pillars; `arrow-icon`, `arrow-top-right`, `round-arrow-right` for CTAs; `si-linkedin`, `si-twitter`, `si-insta` for socials; `icon-call`, `icon-sms`, `icon-marker` for contact.
- **For new icons** (where dkube.io has no precedent): use **Lucide** (1.5px stroke, rounded terminals, 24px grid). Match its visual register.
- **Color:** icons inherit `--dk-fg` on light surfaces, `--dk-fg-on-brand` on brand surfaces. The pillar icons sit in a 56px `--dk-purple-50` tile with `--dk-radius-md` corners.
- **No emoji** in product or marketing UI.

---

## 9 · Components

The full component vocabulary lives in `colors_and_type.css` and the `preview/` cards. Key rules:

- **Buttons:** pill (`--dk-radius-pill`), Poppins 600, primary fills `--dk-brand`, hover darkens to `--dk-brand-hover` and lifts with `--dk-shadow-brand`. Secondary buttons are white with a 1px `--dk-border-strong`. Ghost buttons drop the pill — text only with a right arrow.
- **Cards:** white surface, `--dk-radius-lg` (16px), 1px `--dk-border`, `--dk-shadow-sm` resting → `--dk-shadow-md` on hover, lift `-3px translateY`.
- **Chips:** pill (`--dk-radius-pill`), 11–12px Poppins 600, `--dk-purple-100` background with `--dk-brand` text for branded tags; neutral and status variants follow the semantic palette.
- **Form fields:** 1px `--dk-border-strong`, `--dk-radius-sm`, focus ring is `0 0 0 3px var(--dk-purple-100)` plus `--dk-brand` border.

---

## 10 · Motion

- **Easing:** `cubic-bezier(0.22, 1, 0.36, 1)` (out-quart). No bounces, no overshoots.
- **Durations:** 150 ms micro-interactions, 240 ms standard, 420 ms larger entrances.
- **Scroll-in:** fade + 12 px translate-Y. Stagger by 60 ms between sibling cards.
- **Hover:** buttons darken + shadow grow; cards lift -3 px; CTA arrows nudge `+2px x / -2px y`.
- **Marquee:** customer-logo strip auto-scrolls at constant speed, paused on hover.
- **No** parallax, no glassmorphism panels (except the sticky nav bar), no hand-drawn gestural motion.

---

## 11 · Trademark & Legal

- **Brand:** DKube is a DBA / trademark of **One Convergence, Inc.**
- The site logo includes a small **™** mark — preserve it on the SVG; do not crop or recreate.
- Footer copyright on all surfaces: **©2026 One Convergence. All Rights Reserved.**
- When citing partners (Nutanix, VMware, Rancher, Boston Ltd., AWS), keep the partner's logo unmodified and link to the partner page on first mention.

---

## 13 · Slides

DKube ships fifteen master slide layouts derived from the **DKubeX 2.0 Introduction**, **Executive Overview**, and **DKubeX 2.0 Architecture Diagrams** decks. Full reference and grid rules: see [`slides/SLIDE_GUIDE.md`](slides/SLIDE_GUIDE.md). Live masters: [`slides/index.html`](slides/index.html).

- **Canvas:** 1920×1080 (16:9 — imports cleanly into Google Slides and PowerPoint at default 16:9). Outer padding 96 / 120 px (safe area).
- **Chrome:** Logo top-left, page number bottom-right, `dkube.io` bottom-left on every slide. Cover and Closing override with a stamp lockup. Architecture-diagram slides (11–14) override with a flush-left purple title and the `Empowering Enterprise AI on Kubernetes` tagline at bottom-right.
- **Type:** Slide titles are 64–96 px Poppins Bold; body/bullets 22 px; eyebrows 22 px UPPERCASE. Never go below 18 px.
- **Color:** White default; `--dk-purple-50` for section dividers; `--dk-ink` reserved for the closing slide only. Brand-fill emphasis (`--dk-brand` background + white type) one per slide max.
- **Masters:** Cover · Section Divider · Content + Bullets · Quadrant · Process · Team · Architecture Stack · Compare · Solutions · Logo Wall · Architecture Diagram (Platform Overview) · Architecture Diagram (Multi-Column Flow) · Architecture Diagram (Request Pipeline) · Architecture Diagram (Cross-System) · Closing.
- **Architecture diagram primitives:** four masters (11–14) share a single primitive set — `.dgrp` (dashed group container), `.dcard` (solid purple card), `.dsub` (gray caption), `.dnode` (framed glyph entrypoint), `.dwires` (SVG connector layer). Each diagram is built inside a fixed 1740×820 `.dstage` that scales to fit the slide. Reuse these primitives — never invent new card/group styles. CSS lives in `slides/arch-diagrams.css`.

## 14 · Open items

- **Co-branding visual examples** — paint co-marketing layouts with Cisco, VMware, AWS so designers have reference compositions, not just rules.
- **Stationery & merch** — letterhead, email signature, business card, swag — out of scope until requested.
- **Localized copy** — only English (en-US) is documented today.
- **Chart styling** — slide masters cover layouts; data visualization (bar/line/donut chart styling) needs a dedicated pass against real chart examples.
