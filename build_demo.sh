#!/bin/bash
# Build Demo Markdown from Jupyter Notebook
#
# Executes demo.ipynb and converts it to demo.md with all cell outputs embedded.
#
# Prerequisites (not part of tfnsw-trip-planner):
#   pip install jupyter nbconvert
#
# Usage:
#   ./build_demo.sh

set -e

NOTEBOOK="demo.ipynb"
OUTPUT="demo.md"

echo "=========================================="
echo "tfnsw-trip-planner — Build Demo Markdown"
echo "=========================================="
echo ""

# Verify nbconvert is available
if ! command -v jupyter &> /dev/null; then
    echo "Error: 'jupyter' not found. Install with: pip install jupyter nbconvert"
    exit 1
fi

echo "▶  Executing notebook and converting to Markdown..."
jupyter nbconvert \
    --to markdown \
    --execute \
    --ExecutePreprocessor.timeout=120 \
    "$NOTEBOOK" \
    --output "$OUTPUT"

echo ""
echo "✓ Done → ${OUTPUT}"
