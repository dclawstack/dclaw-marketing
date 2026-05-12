"""SEO Agent depth (Theme H) — site audit, internal-linking suggester,
ranking-delta tracker.

The Ahrefs MCP adapter (`app.services.mcp.ahrefs`) is the data source
for off-platform signal (keyword difficulty, SERP positions, site
audit findings). The internal-linking suggester is pure-local — it
reuses the pgvector KG that already powers `/api/v1/kg/search`.
"""

from app.services.seo.audit import run_site_audit, list_audit_findings
from app.services.seo.internal_linking import suggest_internal_links
from app.services.seo.ranking_delta import (
    snapshot_keyword_positions,
    compute_ranking_delta,
)


__all__ = [
    "run_site_audit",
    "list_audit_findings",
    "suggest_internal_links",
    "snapshot_keyword_positions",
    "compute_ranking_delta",
]
