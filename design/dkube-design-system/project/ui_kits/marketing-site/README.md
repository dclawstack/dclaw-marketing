# DKube Marketing Site — UI Kit

A pixel-faithful React recreation of `dkube.io`. Built from the public marketing site (Webflow) since no codebase or Figma was provided.

## Files
- `index.html` — full home page composed from the components below
- `styles.css` — kit-scoped styles, importing `colors_and_type.css`
- `components.jsx` — exported components

## Components
- `<Header active onNav>` — sticky transparent-blur nav with logo + 6 links + Contact Us CTA
- `<Hero>` — "Private AI" hero with eyebrow, marquee chip row, lede, double CTA
- `<TrustStrip>` — desaturated customer-logo wall
- `<Pillars>` — three icon-led feature pillars + 3 large stat numbers
- `<Blueprints>` — three blueprint cards (image · tags · title · explore · description)
- `<Platforms>` — tabbed DKubeX / DKube split with mock product render
- `<CaseStudies>` — 2×2 photographic case-study grid with scrim + circular CTA
- `<FAQ>` — accordion of 6 questions (rotating + glyph)
- `<FinalCTA>` — dark capsule with "Talk to Us"
- `<Footer>` — 5-col link grid + socials + ©One Convergence

## Notes / caveats
- Customer logos: only VMware + Cisco SVGs were copied; remaining logos are rendered as text wordmarks. Drop the rest of the SVGs into `/assets/` and they'll slot in.
- Fonts (Inter + Manrope) are best-guess substitutions of the Webflow site.
- Platforms section's "product render" is an illustrative gradient placeholder — confirm the design wants a screenshot or schematic instead.
