#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "============================================================"
echo " Synproof's Syntropy — Public Repo, npm & Registry Publisher"
echo "============================================================"

# 1. GitHub authentication & public repository creation
if ! gh auth status >/dev/null 2>&1; then
  echo "[1/3] Přihlašuji do GitHubu (gh auth login)..."
  gh auth login -p https -w
fi

GH_USER="$(gh api user -q .login)"
echo "Přihlášen jako GitHub uživatel: ${GH_USER}"

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "Vytvářím veřejný repozitář https://github.com/${GH_USER}/syntropy ..."
  gh repo create "${GH_USER}/syntropy" \
    --public \
    --description "Official Python & TypeScript SDK, Model Context Protocol (MCP) Server, and AI Agent Skill for Synproof's Syntropy (https://synproof.ai)" \
    --homepage "https://synproof.ai" \
    --source=. \
    --remote=origin \
    --push
else
  echo "Pushing do existujícího origin..."
  git push -u origin main
fi

# Nastavení GitHub Topics pro vyhledávače, MCP katalogy a AI agenty
gh repo edit "${GH_USER}/syntropy" \
  --add-topic syntropy \
  --add-topic synproof \
  --add-topic mcp \
  --add-topic mcp-server \
  --add-topic model-context-protocol \
  --add-topic ai-verification \
  --add-topic hallucination-guardrail \
  --add-topic small-worlds \
  --add-topic claude-skills \
  --add-topic agent-skills || true

echo "✅ Veřejný GitHub repozitář je živý na: https://github.com/${GH_USER}/syntropy"

# 2. npm Registry (syntropy-mcp)
echo ""
echo "[2/3] Kontrola přihlášení do npm registru (npmjs.com)..."
if ! npm whoami >/dev/null 2>&1; then
  echo "Prosím přihlas se do npm (otevře se prohlížeč nebo zadej údaje):"
  npm login
fi

echo "Publikuji balíček 'syntropy-mcp' na npmjs.com..."
npm publish --access public
echo "✅ Balíček 'syntropy-mcp' je publikován na: https://www.npmjs.com/package/syntropy-mcp"

echo ""
echo "============================================================"
echo " HOTOVO! Nyní může kdokoliv spustit:"
echo "   npx -y syntropy-mcp"
echo "   npx skills add ${GH_USER}/syntropy"
echo "   pip install syntropy-client"
echo "============================================================"
