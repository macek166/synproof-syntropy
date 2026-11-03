#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "============================================================"
echo " Synproof's Syntropy — Public Repo, npm & MCP Registry Setup"
echo "============================================================"

# 1. GitHub authentication & public repository creation
if ! gh auth status >/dev/null 2>&1; then
  echo "[1/3] Přihlašuji do GitHubu (gh auth login)..."
  gh auth login -p https -w
fi

GH_USER="$(gh api user -q .login)"
echo "Přihlášen jako GitHub uživatel: ${GH_USER}"

# Sjednocení GitHub username v souborech pokud se liší od macek166
if [ "${GH_USER}" != "macek166" ]; then
  sed -i "s/macek166/${GH_USER}/g" package.json server.json glama.json README.md
  git add package.json server.json glama.json README.md
  git commit -m "chore: align GitHub namespace with ${GH_USER}" || true
fi

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

# 3. Official Model Context Protocol Registry (registry.modelcontextprotocol.io)
echo ""
echo "[3/3] Publikace do oficiálního MCP Registru (registry.modelcontextprotocol.io)..."
~/.local/bin/mcp-publisher validate
~/.local/bin/mcp-publisher login github
~/.local/bin/mcp-publisher publish
echo "✅ MCP Server je publikován v oficiálním MCP Registru!"

echo ""
echo "============================================================"
echo " HOTOVO! Všechny hlavní registry jsou publikované:"
echo "   • GitHub: https://github.com/${GH_USER}/syntropy"
echo "   • npm:    https://www.npmjs.com/package/syntropy-mcp"
echo "   • PyPI:   https://pypi.org/project/syntropy-client/"
echo "   • MCP:    https://registry.modelcontextprotocol.io"
echo "============================================================"
