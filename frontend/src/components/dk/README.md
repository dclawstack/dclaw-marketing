# Dk Component Library

The canonical primitive library for the DClaw Marketing product UI. Every screen built from Phase 0 onward MUST use these — see [`design/source/project/BRAND_GUIDELINES.md`](../../../../design/source/project/BRAND_GUIDELINES.md) for the underlying visual rules.

## Why a new library?

The legacy `@/components/ui/*` set is shadcn-shaped but doesn't apply the DClaw brand vocabulary: square buttons, generic gray surfaces, no eyebrow tier, etc. The `Dk*` library re-encodes the brand rules directly:

- **Buttons** are pill-shaped (`--dk-radius-pill`), Poppins 600, brand fill → brand-hover darkening on hover with `--dk-shadow-brand`.
- **Cards** are 16px-radius, 1px border, soft `shadow-sm` resting → `shadow-md` on hover with `-3px translateY` lift and brand-tinted border.
- **Chips & badges** ride `--dk-purple-100` background with `--dk-brand` text for brand-tone; semantic tones (`success` / `warning` / `danger` / `info`) use the matching `--dk-*-bg` pairing.
- **Form fields** are 8px-radius, 1px `--dk-border-strong`, focus ring `0 0 0 3px var(--dk-purple-100)` plus `--dk-brand` border.
- **Eyebrows** are 14px uppercase Poppins 600 with `0.04em` tracking in brand tint.

## Import

```tsx
import { DkButton, DkCard, DkCardHeader, DkCardTitle, DkInput, DkLabel } from "@/components/dk";
```

## Components

| Component | Purpose |
|---|---|
| `DkButton` | Pill CTAs. `variant`: `primary` / `secondary` / `ghost` / `danger` / `ink`. `size`: `sm` / `md` / `lg` / `icon`. `loading` and `withArrow` props. |
| `DkCard` + subparts | Surface container with hover-lift. Subparts: `DkCardHeader`, `DkCardTitle`, `DkCardDescription`, `DkCardContent`, `DkCardFooter`. |
| `DkEyebrow` | Section eyebrow label. |
| `DkChip` | Pill-tagged label. `tone`: `brand` / `neutral` / `success` / `warning` / `danger` / `info` / `outline`. |
| `DkBadge` | Inline status badge. Same tone set as Chip. |
| `DkAvatar` | Image avatar with initials fallback. `size`: `sm` / `md` / `lg`. |
| `DkSkeleton` | Loading placeholder. |
| `DkProgress` | Linear progress bar. |
| `DkInput` / `DkTextarea` / `DkLabel` / `DkSelect` | Form fields. |
| `DkSwitch` / `DkCheckbox` / `DkRadio` + `DkRadioGroup` / `DkSlider` | Form controls. |
| `DkDialog` + subparts | Modal. `size`: `sm` / `md` / `lg` / `xl`. |
| `DkTabs` + subparts | Tab navigation. |
| `DkTable` + subparts | Tabular data with brand-themed header row. |
| `DkPageHeader` | Standard page top with eyebrow + title + description + actions. |
| `DkEmptyState` | Empty / first-run state with icon + title + description + CTA. |
| `DkBreadcrumb` | Hierarchical nav crumb. |
| `DkSidebar` | Side nav with grouped items + active-state highlighting. |
| `DkToastProvider` + `useDkToast()` | Toast notifications. |

## Rules

- **No raw Tailwind grays** (`bg-slate-100`, `text-gray-500`). Use semantic aliases (`bg-bg-muted`, `text-fg-2`) or `--dk-*` tokens directly.
- **No `dark:` variants** anywhere. Brand is light-mode only.
- **Poppins only.** All `font-sans` / `font-display` resolve to `var(--dk-font-sans)`.
- **Pill or 16px** corners. Forms use 8px (`rounded-md`); everything else is 16px (`rounded-2xl`) or pill (`rounded-pill`).
- **Soft, neutral shadows.** Only brand CTAs get a `--dk-shadow-brand` accent.
- **Motion is restrained.** `transition-all duration-base ease-out-quart` is the default. No bounces. No glassmorphism except the sticky nav.

## Visual reference

Eyeball comparisons against the source-of-truth previews:
- [`design/source/project/preview/components-buttons.html`](../../../../design/source/project/preview/components-buttons.html)
- [`design/source/project/preview/components-card.html`](../../../../design/source/project/preview/components-card.html)
- [`design/source/project/preview/components-chips.html`](../../../../design/source/project/preview/components-chips.html)
- [`design/source/project/preview/components-input.html`](../../../../design/source/project/preview/components-input.html)

A live in-app reference page lives at `/admin/design` (Story 0.4) once it ships.
