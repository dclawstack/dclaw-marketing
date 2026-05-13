# Design

Reference material for the DClaw Marketing visual system. The single source of truth for tokens lives in [`frontend/src/styles/brand.css`](../frontend/src/styles/brand.css) and is exposed through Tailwind via [`frontend/tailwind.config.ts`](../frontend/tailwind.config.ts).

## Layout

| Path | Use |
|---|---|
| [`source/`](./source/) | Historical design ingest — palette derivation, component preview cards, slide masters. Reference only; product code MUST NOT import from here. |

## About `source/`

The `source/` directory is a design handoff bundle from Claude Design. It contains:

- `source/project/` — the DKube Design System: brand guidelines, token CSS, component preview cards, slide masters, UI kit, and the Claude Code skill front-matter.
- `source/chats/` — *(removed; outputs are in `project/`)*.

The files in `source/project/` are **reference only** — product code must not import from here. All tokens are already mirrored in `frontend/src/styles/brand.css`. When recreating designs, match the visual output of the previews; do not copy the prototype's internal structure.

---

## Working with the brand

- All component design is governed by [`frontend/src/components/dk/`](../frontend/src/components/dk/) (the canonical primitive library). Eyeball-compare new primitives against `source/project/preview/*.html`.
- All tokens use the `--dk-*` prefix (where `dk` = "design kit"). No hardcoded hex anywhere in the product.
- Light mode only. Poppins only. Pill CTAs. 16-24px card radius. Soft neutral shadows.
- Voice rules and motion specs live in `source/project/BRAND_GUIDELINES.md` — extracted into product code as needed.
