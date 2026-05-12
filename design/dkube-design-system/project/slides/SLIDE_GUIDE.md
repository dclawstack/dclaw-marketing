# DKube Slide Templates

Fifteen master layouts derived from the **DKubeX 2.0 Introduction**, **DKube Executive Overview**, and **DKubeX 2.0 Architecture Diagrams** decks — the most current and on-brand decks in the source set. Open `slides/index.html` to view all masters in sequence.

## The masters

| # | Layout | Use for |
|--:|---|---|
| 01 | **Cover** | Deck opener — product/topic name + tagline + cube mark |
| 02 | **Section divider / Hero** | Section starts ("About Us", "Solutions", "Pricing"); pairs a headline with 3 numbered pillars |
| 03 | **Content + bullets** | The workhorse. Eyebrow + title + lede + 4 left-bordered bullets. Use this for ~60% of body slides |
| 04 | **Quadrant** | Four equal value props or benefits |
| 05 | **Process** | Horizontal step pipeline (3–9 steps) — best for delivery models, lifecycles, journeys |
| 06 | **Team grid** | 4-up (or 8-up) people cards with photo, name, role, one-line credential |
| 07 | **Architecture stack** | Layered platform diagram (pill rows) with optional brand-fill emphasis row |
| 08 | **Two-column compare** | "Before vs After," "What you have vs What we add" — left neutral, right brand-fill |
| 09 | **Solutions / Tile grid** | 3-up product or use-case tiles with image hero + tag + title + description |
| 10 | **Logo wall** | 5×N grid for customers, partners, integrations |
| 11 | **Architecture diagram — platform overview** | Tiered cluster diagram: external nodes → grouped service tiers (Core, App Store, Data, Observability, Tools) inside a Kubernetes cluster boundary |
| 12 | **Architecture diagram — lifecycle / multi-column flow** | 5–7 column horizontal reconcile flow with arrows between stages (User Intent → Frontend/Backend → CR → Operator → Provisioning/Helm → Status) |
| 13 | **Architecture diagram — request pipeline** | Client → Auth → API Layer → Core Engine → Health/Cache/Rate-Limit → Providers; horizontal layered with side-rail provider list |
| 14 | **Architecture diagram — cross-system** | Browser → Edge/Auth → Product Core/Data/Runtimes inside a product container, with a sibling "Platform" sidebar (Services, Observability, Tools) and external registries column |
| 15 | **Closing** | Inverse-fill thank-you slide with contact rail |

### Architecture diagrams (11–14)

The four architecture masters share a single visual language built from a small primitive set:

- **`.dgrp`** — dashed gray rounded container (groups of related cards). Title sits centered or left on the top edge in white, in `--dk-purple-700` (or gray-600 for utility groupings).
- **`.dcard`** — solid `--dk-purple-700` card with white text, 10px radius, soft offset shadow. The signature node primitive.
- **`.dsub`** — small gray sub-label that sits below a `.dcard` to caption it.
- **`.dnode`** — standalone framed glyph (e.g. user terminal, SSO icon) used as a flow entrypoint.
- **`.dwires`** — full-bleed SVG layer carrying connector lines between groups; thin `#4D4D4D` strokes with arrow-head markers.

Each diagram lives inside a fixed-size **1740×820 `.dstage`** which is scaled to fit the slide's available content area (chrome safe-zone is 180px). All four slides also override the chrome with a flush-left purple title, `Empowering Enterprise AI on Kubernetes` tagline at bottom-right, and `dkube.io` at bottom-left.

CSS lives in `slides/arch-diagrams.css`. To add a new architecture-style master, reuse the same primitives — never invent new card/group styles. Box positions are absolute pixel coords inside the 1740×820 design space.

## Slide grid

- **Canvas:** 1920 × 1080 (16:9). Other aspect ratios will scale via the deck stage but masters are designed for 16:9.
- **Outer padding:** 96 px top, 120 px sides (the "safe area"). Cover and Closing use 160 px for breathing room.
- **Persistent chrome:** logo top-left (44 px tall), page number bottom-right, `dkube.io` URL bottom-left. The Cover and Closing slides override this with a stamp lockup.
- **Vertical rhythm:** 32 / 48 / 56 / 64 / 96 — drawn from the spacing scale (`--dk-space-*`).

## Type for slides

Slide type is **larger than web type**. Anything below 18 px is unreadable from the back of a meeting room.

| Role | Family · Weight · Size |
|---|---|
| Hero / cover product | Poppins 800 · 200 px |
| Closing / thank-you | Poppins 700 · 200 px |
| Slide title | Poppins 700 · 72–96 px |
| Subtitle | Poppins 500 · 36 px |
| Lede | Poppins 400 · 28 px |
| Body / bullets | Poppins 400 · 22 px |
| Card title | Poppins 700 · 24–32 px |
| Card body | Poppins 400 · 18–20 px |
| Eyebrow | Poppins 600 · 22 px UPPERCASE · 0.08 em tracking |
| Page number | Poppins 500 · 18 px |

## Color usage on slides

- **Default:** white slide, ink type, brand purple for CTAs and eyebrows.
- **Section divider (`l-divider`):** `--dk-purple-50` background to break rhythm.
- **Closing (`l-closing`):** `--dk-ink` background, white type. **Use only for the last slide** — never in the middle of a deck.
- **Brand-filled emphasis:** the right column of the Compare layout and the top row of the Architecture stack use `--dk-brand` fill with white type. Use this sparingly — one per slide max.

## Imagery on slides

- Replace the gradient `.hero` placeholders in the Solutions layout with real photography (use the brand `assets/img-*` files or comparable).
- For team grids, replace `.photo` placeholder tiles with real headshots, square-cropped, with the same `--dk-radius-lg` corner.
- Architecture / diagrams: stay schematic. Don't render glossy 3D infrastructure illustrations. The arch-diagram masters (11–14) are the canonical schematic style — use their `.dgrp` / `.dcard` / `.dsub` primitives, not custom shapes.

## Do / Don't

| Do | Don't |
|---|---|
| Keep one idea per slide | Pack 6 bullets where 3 will do |
| Use eyebrows to set context | Skip eyebrows on body slides — they orient the audience |
| Title with a period-stop | Title with a question mark |
| Reuse the master, replace the copy | Hand-tune type sizes per slide |
| Use Quadrant for exactly 4 things | Force 5 or 6 things into a Quadrant — switch to Solutions or a list |
| Inverse the **last** slide only | Inverse-fill mid-deck (the audience loses orientation) |

## Extending the system

To add a new master, copy any `<section>` block in `slides/index.html` and:
1. Give it a new `data-screen-label="NN Name"` (the deck stage will read it for navigation).
2. Add a `.l-<name>` class with its layout CSS in the `<style>` block at the top.
3. Re-use the existing `.s-eyebrow`, `.s-title`, `.s-subtitle`, `.s-lede`, `.s-body` type classes — don't redefine them.
4. Always include `.chrome-logo`, `.chrome-page`, `.chrome-url` (or override on the Cover/Closing).

## Exporting to PowerPoint

The deck is built on `deck-stage.js`, which supports a clean PPTX export. Open `slides/index.html`, then run the Export as PPTX skill — slides come out as native, editable PowerPoint shapes/text (not flat images).
