# Release Timeline

## Versioning convention

The roadmap doc is named `PLAN-v1.2.md`. Releases are aligned with that doc — the stakeholder reads one coherent version line.

> **Note on rename.** `v0.1.0-mvp` and `v0.2.0` were renamed to `v1.0.0` and `v1.1.0` in Sprint 3 (PR #278). Tags re-pointed at the same commit SHAs; releases re-published with new names. Earlier references in old docs may still mention the old names.

## Shipped releases

| Tag | Date | Closeout PR | Theme |
|-----|------|-------------|-------|
| `v1.0.0` | 2026-05-12 | #76 (originally `v0.1.0-mvp`) | End-to-end MVP demo flow · Sprint 1 closeout |
| `v1.1.0` | 2026-05-13 | #211 (originally `v0.2.0`) | Feature-complete vs PLAN-v1.2 · Sprint 2 closeout |
| `v1.1.1` | 2026-05-14 | #279 | Operator-ready hardening + SP3-* polish · Sprint 3 closeout |

## Planned

| Tag | Target | What's in it |
|-----|--------|--------------|
| `v1.2.0` | TBD (post-Sprint 4) | Brand Setup Studio polish · real OAuth credentials wired · TOTP enrollment UI · observability dashboards · user-guide refresh · marketing collateral (owned by operator) |

## v1.1.1 highlights (current)

- **Two-tier admin model** — bootstrap superadmin + per-org admins; centralized guards; last-admin protection; audit + notifications.
- **Universal slug scheme** — `u-/o-/s-` prefix + 6-hex random suffix; migration re-slugs every existing row.
- **Combined create-user-with-org dialog** — superadmin can create user + multi-org assignment + inline new-org creation.
- **Left-sidebar navigation** — domain-grouped; replaces overflowing top bar.
- **Auto-merge + auto-close pipeline** — squash carries PR body; workflow has `issues: write`; queue drains itself.
- **SP3-1 → SP3-24 polish lane** — 24 themes shipped in one burst.
- **DB migrations** — TOTP columns, landing_pages_json, kanban_json, slug refactor.
- **Next.js proxy fix** — `BACKEND_INTERNAL_URL` at container build time.

See [CHANGELOG.md](../CHANGELOG.md) for the full PR list.

## Related

- [[Sprint Timeline]]
- [[Open Issues]]
