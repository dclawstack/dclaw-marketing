#!/usr/bin/env bash
# docs_to_pdf.sh — bundle the markdown docs into a single PDF.
#
# Strategy: concatenate the canonical doc set in a sensible order →
# pass through pandoc with the LaTeX engine. Falls back to Chromium
# headless print-to-PDF when pandoc isn't installed (npm i -g
# md-to-pdf works too).
#
# Usage:
#   ./scripts/docs_to_pdf.sh                 # writes docs/dclaw-handbook.pdf
#   OUT=/tmp/x.pdf ./scripts/docs_to_pdf.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$REPO_ROOT/docs/dclaw-handbook.pdf}"

DOCS=(
  "$REPO_ROOT/README.md"
  "$REPO_ROOT/docs/USER-GUIDE.md"
  "$REPO_ROOT/docs/ARCHITECTURE.md"
  "$REPO_ROOT/docs/WORKFLOW-FAILURE-PLAYBOOK.md"
  "$REPO_ROOT/CHANGELOG.md"
)

TMP="$(mktemp -t dclaw-bundle.XXXXXX.md)"
trap 'rm -f "$TMP"' EXIT
{
  echo "% DClaw Handbook"
  echo "% Generated $(date -u +%FT%TZ)"
  echo ""
  for f in "${DOCS[@]}"; do
    [ -f "$f" ] || continue
    echo ""
    echo "---"
    echo ""
    cat "$f"
    echo ""
  done
} > "$TMP"

if command -v pandoc >/dev/null 2>&1; then
  pandoc "$TMP" -o "$OUT" \
    --pdf-engine=xelatex \
    --variable=geometry:margin=2cm \
    --variable=mainfont:'Helvetica' \
    --toc \
    --number-sections
  echo "wrote $OUT (via pandoc)"
elif command -v md-to-pdf >/dev/null 2>&1; then
  cp "$TMP" /tmp/dclaw-bundle.md
  md-to-pdf /tmp/dclaw-bundle.md --pdf-options.format=A4
  mv /tmp/dclaw-bundle.pdf "$OUT"
  echo "wrote $OUT (via md-to-pdf)"
else
  echo "Neither pandoc nor md-to-pdf installed; bundled markdown left at $TMP"
  cp "$TMP" "${OUT%.pdf}.md"
  echo "wrote ${OUT%.pdf}.md instead"
fi
