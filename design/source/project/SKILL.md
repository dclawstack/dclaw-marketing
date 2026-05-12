---
name: dkube-design
description: Use this skill to generate well-branded interfaces and assets for DKube (dkube.io) — an enterprise Private AI company — for production work or throwaway prototypes/mocks/decks. Contains essential design guidelines, colors, type tokens, fonts, brand assets, and UI kit components.
user-invocable: true
---

Read the `README.md` file within this skill, and explore the other available files (`colors_and_type.css`, `assets/`, `preview/`, `ui_kits/`).

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

Key brand reminders:
- Primary purple `#7660A8`, secondary `#9384BD`. Soft purple tint `#F8F6FB` for hero washes. Otherwise white surfaces with near-black ink.
- Poppins for everything (300–800). 700–800 for display headlines, 600 for buttons, 500 for UI labels, 400 for body.
- 16px card radius, 999px pill buttons, soft neutral shadows, no glassmorphism, no gradient backgrounds, no emoji, no AI-render imagery.
- Voice: enterprise, calm, Title Case headlines, period-stop one-liners, no exclamation marks.

Slides:
- Slide masters live in `slides/index.html` — fifteen layouts including four architecture-diagram masters (11–14). Full reference: `slides/SLIDE_GUIDE.md`.
- Canvas is 1920×1080 (16:9), imports cleanly into Google Slides / PowerPoint.
- Architecture diagrams use a fixed primitive set (`.dgrp` / `.dcard` / `.dsub` / `.dnode` / `.dwires`) defined in `slides/arch-diagrams.css`. Reuse these primitives — never invent new card/group styles for diagrams.
- Slide title minimums: 64px (display titles), 22px (body). Never go below 18px on a slide.
