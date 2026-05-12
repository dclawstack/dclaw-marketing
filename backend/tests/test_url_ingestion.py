"""Theme Q2 follow-up — URL ingestion path."""

from __future__ import annotations

import pytest

from app.services.ingestion import extract_html_text, extract_text


def test_extract_html_text_strips_scripts_styles_and_tags():
    html = """
    <html><head>
      <title>T</title>
      <style>body{color:red}</style>
      <script>alert('x')</script>
    </head>
    <body>
      <h1>Welcome</h1>
      <p>Hello <b>world</b>.</p>
      <p>Second paragraph &mdash; with an &amp; entity.</p>
      <noscript>fallback</noscript>
    </body></html>
    """
    out = extract_html_text(html)
    assert "alert" not in out
    assert "color:red" not in out
    assert "fallback" not in out
    assert "Welcome" in out
    assert "Hello world." in out
    assert "—" in out
    assert "& entity" in out


def test_extract_html_text_handles_numeric_entities():
    out = extract_html_text("<p>caf&#233;</p>")
    assert "café" in out


def test_extract_html_text_empty_input():
    assert extract_html_text("") == ""


def test_extract_text_routes_html_mime():
    """The /urls worker calls extract_text with the Content-Type from
    the response; verify text/html routes through the stripper."""
    out = extract_text(b"<p>Hello <b>HTML</b></p>", "text/html; charset=utf-8")
    assert "Hello HTML" in out
    assert "<" not in out


def test_extract_text_rejects_binary():
    from app.services.ingestion import UnsupportedMimeTypeError

    with pytest.raises(UnsupportedMimeTypeError):
        extract_text(b"\x00\x01\x02", "application/octet-stream")
