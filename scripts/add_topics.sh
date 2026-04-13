#!/bin/bash
# Add GitHub repository topics for mcp-prompt-optimizer.
#
# Usage:
#   chmod +x scripts/add_topics.sh
#   ./scripts/add_topics.sh YOUR_GITHUB_TOKEN
#
# The token needs the 'public_repo' scope (or 'repo' for private repos).

set -euo pipefail

TOKEN=$1

if [[ -z "$TOKEN" ]]; then
  echo "Error: GitHub token required."
  echo "Usage: $0 YOUR_GITHUB_TOKEN"
  exit 1
fi

curl -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  https://api.github.com/repos/yusufkucukates/mcp-prompt-optimizer/topics \
  -d '{"names":["mcp","prompt-engineering","prompt-optimization","claude-code","cursor","python","llm","ai-agents","developer-tools"]}'

echo ""
echo "Topics added successfully"
