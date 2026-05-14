"""Five production-ready workflow templates (S4-D2).

Each template is a `dsl_json` dict that drops directly into a
`Workflow` row. The frontend visual builder (D6) seeds new workflows
from this catalog.
"""

from __future__ import annotations

from typing import Any


TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "launch_announcement",
        "label": "Launch Announcement (multi-channel)",
        "description": (
            "Decompose a launch brief → draft LinkedIn + X + email → "
            "Reviewer agent pass → queue ScheduledPost rows after Approval."
        ),
        "dsl": {
            "nodes": [
                {
                    "id": "draft_li",
                    "type": "llm",
                    "system": "You are the SMM Agent. Draft a LinkedIn post.",
                    "user_template": "{{brief}}",
                    "output_var": "linkedin_post",
                },
                {
                    "id": "draft_x",
                    "type": "llm",
                    "system": "You are the SMM Agent. Draft an X (Twitter) thread.",
                    "user_template": "{{brief}}",
                    "output_var": "x_thread",
                },
                {
                    "id": "draft_email",
                    "type": "llm",
                    "system": "You are the Creatives Agent. Draft a launch email.",
                    "user_template": "{{brief}}",
                    "output_var": "email_body",
                },
                {
                    "id": "review",
                    "type": "llm",
                    "system": "You are the Reviewer Agent. Audit the drafts below.",
                    "user_template": "LinkedIn:\n{{linkedin_post}}\n\nX:\n{{x_thread}}\n\nEmail:\n{{email_body}}",
                    "output_var": "review_notes",
                },
                {
                    "id": "approve",
                    "type": "approval",
                    "kind": "launch.publish_all",
                    "subject_template": "Approve launch publication?",
                },
            ],
            "edges": [
                {"from": "draft_li", "to": "review"},
                {"from": "draft_x", "to": "review"},
                {"from": "draft_email", "to": "review"},
                {"from": "review", "to": "approve"},
            ],
        },
    },
    {
        "key": "weekly_digest",
        "label": "Weekly Digest (analyst → newsletter)",
        "description": "Analyst summarises last 7 days → SEO turns it into a newsletter.",
        "dsl": {
            "nodes": [
                {
                    "id": "analyse",
                    "type": "llm",
                    "system": "You are the Analyst Agent. Summarise the metrics.",
                    "user_template": "Rollups: {{rollups_json}}",
                    "output_var": "analysis",
                },
                {
                    "id": "newsletter",
                    "type": "llm",
                    "system": "You are the Creatives Agent. Turn this into a newsletter body.",
                    "user_template": "Source: {{analysis}}",
                    "output_var": "newsletter_body",
                },
            ],
            "edges": [{"from": "analyse", "to": "newsletter"}],
        },
    },
    {
        "key": "lead_magnet",
        "label": "Lead Magnet (long-form → CTA)",
        "description": "Long-form article + CTA + form copy in one pass.",
        "dsl": {
            "nodes": [
                {
                    "id": "outline",
                    "type": "llm",
                    "system": "You are the SEO Agent. Outline a long-form article.",
                    "user_template": "{{topic}}",
                    "output_var": "outline",
                },
                {
                    "id": "draft",
                    "type": "llm",
                    "system": "You are the Creatives Agent. Write the long-form article.",
                    "user_template": "Outline: {{outline}}",
                    "output_var": "article",
                },
                {
                    "id": "cta",
                    "type": "llm",
                    "system": "You are the SMM Agent. Draft a CTA + lead-form copy.",
                    "user_template": "Article: {{article}}",
                    "output_var": "cta_copy",
                },
            ],
            "edges": [
                {"from": "outline", "to": "draft"},
                {"from": "draft", "to": "cta"},
            ],
        },
    },
    {
        "key": "ad_campaign",
        "label": "Paid Ad Campaign (3 concepts + budget)",
        "description": "Paid Media outlines campaign + creative pulls in 3 concepts.",
        "dsl": {
            "nodes": [
                {
                    "id": "plan",
                    "type": "llm",
                    "system": "You are the Paid Media Agent. Plan the campaign.",
                    "user_template": "{{brief}}",
                    "output_var": "plan",
                },
                {
                    "id": "creative",
                    "type": "llm",
                    "system": "You are the Creatives Agent. Produce 3 ad concepts.",
                    "user_template": "Plan: {{plan}}",
                    "output_var": "ad_concepts",
                },
                {
                    "id": "approve",
                    "type": "approval",
                    "kind": "ad.spend",
                    "subject_template": "Approve paid spend?",
                },
            ],
            "edges": [
                {"from": "plan", "to": "creative"},
                {"from": "creative", "to": "approve"},
            ],
        },
    },
    {
        "key": "aeo_audit",
        "label": "AEO Audit (answer-engine optimisation)",
        "description": "SEO Agent scores content for AI-search discoverability + suggests rewrites.",
        "dsl": {
            "nodes": [
                {
                    "id": "score",
                    "type": "llm",
                    "system": "You are the SEO Agent. Score the page for AEO 0-100, list weak spots.",
                    "user_template": "{{page_text}}",
                    "output_var": "aeo_score",
                },
                {
                    "id": "rewrite",
                    "type": "llm",
                    "system": "You are the Creatives Agent. Rewrite the weak spots.",
                    "user_template": "Weak spots: {{aeo_score}}\n\nPage:\n{{page_text}}",
                    "output_var": "rewrite",
                },
            ],
            "edges": [{"from": "score", "to": "rewrite"}],
        },
    },
]


def list_templates() -> list[dict[str, Any]]:
    return TEMPLATES


def get_template(key: str) -> dict[str, Any] | None:
    for t in TEMPLATES:
        if t["key"] == key:
            return t
    return None
