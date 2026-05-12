"""Agent layer — direct Anthropic SDK calls for v0.1.

Phase 2 in PLAN-v1.2 §v2.0 §9. Full Claude Agent SDK + MCP runtime
comes later; for the MVP we use direct Claude API calls with the
brand kit + Knowledge Graph retrieval as context. Outputs land in
the ApprovalRequest queue for the Hard-gate review flow.
"""

from app.agents.creatives import generate_social_posts

__all__ = ["generate_social_posts"]
