# Brand Assets

Authoritative brand assets for the DClaw Marketing product UI.

The DClaw mark is a **signal-broadcast glyph**: a single white dot anchored in the bottom-left of a purple rounded square, with three concentric arcs radiating to the top-right. The mark signals reach across channels — the core thing the platform does. Equal 14-unit safe-area margin on all four sides of the 64-unit canvas.

## Layout

| Path | Use |
|---|---|
| `logos/dclaw-icon-purple.svg` | **Product app icon — primary.** Purple square + white marks. Use on light backgrounds. Favicon + nav badge. |
| `logos/dclaw-icon-white.svg` | Inverse app icon. White square + purple marks. Use on dark / brand-colored surfaces. |
| `logos/dclaw-logo-purple.svg` | Horizontal lockup with "DClaw Marketing" wordmark for light marketing surfaces. |
| `logos/dclaw-logo-white.svg` | Reverse horizontal lockup for dark marketing surfaces. |
| `logos/dclaw-icon-{purple,white}-{16..1024}.{png,webp}` | Rasterized icon variants at 11 sizes (16, 32, 48, 64, 96, 128, 180, 192, 256, 512, 1024) in both PNG and WebP. |
| `logos/dclaw-logo-{purple,white}-h{32..256}.{png,webp}` | Rasterized wordmark lockups at 7 heights (32, 48, 64, 96, 128, 192, 256) — width preserves the 350:64 aspect. |
| `icons/arrow-icon.svg`, `arrow-top-right.png`, `round-arrow-right.svg` | Directional arrows on CTA buttons and case-study cards |
| `icons/si-linkedin.svg`, `si-twitter.svg`, `si-insta.svg` | Social network glyphs |
| `icons/menu-icon.svg` | Mobile menu glyph |

Favicons mirror to `frontend/public/` root: `favicon.svg`, `favicon.png`, `favicon-{16,32,48}x{16,32,48}.png`, `apple-touch-icon.png`, `android-chrome-{192,512}.png`, plus a `.webp` for each. `site.webmanifest` declares the PWA icon set.

## Rules

- **Aspect ratio is locked.** Always scale uniformly. Never stretch, squash, distort.
- **Use the supplied SVG.** Don't redraw, recolor, or re-letter the wordmark.
- **Clear space:** keep a margin equal to half the icon height on all sides.
- **Minimum size:** 24px tall for the icon, 96px wide for the wordmark.
- **On photography:** use the white variant over a dark scrim (≥50% black at logo position). Never place the purple wordmark on a busy or low-contrast photo.
- **Pick the right format.** SVG for any context that will render it (web, modern apps). WebP for compressed raster use. PNG for legacy fallback.

For full vocabulary (palette, typography, motion, component rules) see the design-system reference at [`/design`](../../../design/).
