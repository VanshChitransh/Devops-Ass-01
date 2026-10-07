#!/usr/bin/env bash
# Builds the distributable: copies the app into build/ and writes build-info.txt
set -euo pipefail
cd "$(dirname "$0")"
rm -rf build && mkdir -p build
cp app/calculator.py build/
{
  echo "project:   vansh-session16-calculator"
  echo "built_at:  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "built_by:  ${GITHUB_ACTOR:-$(whoami)}"
  echo "commit:    ${GITHUB_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo local)}"
  echo "python:    $(python3 --version 2>&1)"
  echo "tests:     $(grep -c '^def test_' tests/test_calculator.py) test functions"
} > build/build-info.txt
echo "Build complete:"; ls -l build
