#!/usr/bin/env bash
set -euo pipefail

echo "== OpenClaw Project Status =="
echo

echo "Current directory:"
pwd
echo

echo "Current branch:"
git branch --show-current
echo

echo "Git status --short:"
status_output="$(git status --short)"
if [[ -z "$status_output" ]]; then
  echo "clean"
else
  echo "$status_output"
fi
echo

echo "Recent commits:"
git log --oneline -5
echo

if [[ -z "$status_output" ]]; then
  echo "Workspace: clean, no uncommitted changes."
else
  echo "Workspace: has uncommitted changes."
fi
