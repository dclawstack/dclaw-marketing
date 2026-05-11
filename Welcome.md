# DClaw Marketing — Vault

This repository is also an Obsidian vault. Open the folder in Obsidian and you can navigate the entire project as a knowledge graph.

## Quick links

- **Plan (source of truth):** [[PLAN-v1.2|PLAN-v1.2.md]]
- **Architecture rules for agents:** [[AGENTS|AGENTS.md]]
- **Project dashboard (live):** [[PROJECT-DASHBOARD]]
- **Glossary:** [[GLOSSARY]]
- **Repo structure (file index):** [[Repo Structure]]
- **GitHub Project board:** [DClaw Marketing Project](https://github.com/orgs/dclawstack/projects/1)
- **GitHub repository:** [dclawstack/dclaw-marketing](https://github.com/dclawstack/dclaw-marketing)

## What we're building

**DClaw Marketing** is an agent-driven marketing operating system. Humans set the brand and inputs once; a crew of AI agents (Creatives, Social Media Manager, SEO, Paid Media, Analyst — orchestrated by a Conductor) does the actual work. Humans supervise their **Station** and approve outbound actions.

- Hierarchy: **Organization → Project → Campaign → Asset**
- Roles are **supervision scopes**, not work assignments
- All outbound publishing is **hard-gated** through an Approval Inbox
- Ships as a **Helm chart + GHCR images** to customer-owned k8s clusters

Full vision: [[PLAN-v1.2|PLAN-v1.2.md]] §v2.0 Vision. Technology stack: Appendix A in the same file.

## How to use this vault

- Pages use **`[[wikilinks]]`** to connect concepts. Click them to navigate.
- Use **Cmd+P** for quick-open by file name.
- Use the **graph view** (Cmd+G) to see relationships between docs.
- The repo's source code lives under `backend/`, `frontend/`, `helm/` — those folders show up in the file explorer.
