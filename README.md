# Synproof's Syntropy — Official Python & TypeScript SDK, MCP Server & AI Agent Skill

[![Website](https://img.shields.io/badge/Website-synproof.ai-c8a96e?style=flat-square)](https://synproof.ai)
[![PyPI](https://img.shields.io/pypi/v/syntropy-client?style=flat-square&label=PyPI%20syntropy-client)](https://pypi.org/project/syntropy-client/)
[![Documentation](https://img.shields.io/badge/Docs-synproof.ai%2Fdocs-blue?style=flat-square)](https://synproof.ai/docs)
[![AI Agent Skill](https://img.shields.io/badge/Skill-SKILL.md-10b981?style=flat-square)](https://synproof.ai/SKILL.md)
[![OpenAPI 3.1](https://img.shields.io/badge/OpenAPI-3.1.0-6366f1?style=flat-square)](https://synproof.ai/openapi.json)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](./LICENSE)

> **Language models guess. Syntropy proves.**  
> **Synproof's Syntropy** ([https://synproof.ai](https://synproof.ai)) is a deterministic 5-sieve dialectical verification engine, Small Worlds axiom library, and **Axiomat** document-to-axiom compiler for AI agents, legal compliance, scientific verification, and enterprise decision pipelines.

---

## Canonical Links & Machine-Readable Discovery

| Resource | URL |
| :--- | :--- |
| **Web Platform & Interactive Studio** | [https://synproof.ai](https://synproof.ai) |
| **Developer Documentation (20 Chapters)** | [https://synproof.ai/docs](https://synproof.ai/docs) |
| **How the 5-Sieve Architecture Works** | [https://synproof.ai/how-it-works](https://synproof.ai/how-it-works) |
| **AI Coding Agent Skill (`SKILL.md`)** | [https://synproof.ai/SKILL.md](https://synproof.ai/SKILL.md) |
| **Coding Agent Rules (`AGENTS.md`)** | [https://synproof.ai/AGENTS.md](https://synproof.ai/AGENTS.md) |
| **LLM Index (`llms.txt` / `llms-full.txt`)** | [https://synproof.ai/llms.txt](https://synproof.ai/llms.txt) · [https://synproof.ai/llms-full.txt](https://synproof.ai/llms-full.txt) |
| **MCP Discovery Manifest** | [https://synproof.ai/.well-known/mcp.json](https://synproof.ai/.well-known/mcp.json) |
| **OpenAPI 3.1 Specification** | [https://synproof.ai/openapi.json](https://synproof.ai/openapi.json) |
| **Production API Endpoint** | `https://api.synproof.ai` |

---

## 1. Install the AI Coding Agent Skill (Claude Code, Cursor, Antigravity, Windsurf, Codex)

Give your coding agent full autonomous knowledge of Synproof's Syntropy in one command:

```bash
# Via Vercel Skills CLI (skills.sh)
npx skills add macek166/syntropy

# Or directly via curl into your workspace
curl -sL https://synproof.ai/SKILL.md -o SKILL.md

# Or via the Python CLI (installs into .agents/skills, .claude/skills, and .cursor/rules)
pip install --upgrade syntropy-client
python -m syntropy install-skill
```

---

## 2. Python SDK & CLI (`syntropy-client`)

### Installation

```bash
pip install --upgrade syntropy-client
```

### 1-Line Hallucination Guardrail (`@verify_agent_output`)

```python
from syntropy import SyntropyClient, verify_agent_output

client = SyntropyClient()  # Reads SYNTROPY_API_KEY, OPENROUTER_API_KEY, or GEMINI_API_KEY

@verify_agent_output(
    world="@pravo:obcansky-zakonik-cz",
    axioms=["Smluvní pokuta nesmí překročit 0.5 % denně z dlužné částky."],
    max_failures=3,
    model_name="gemini-2.5-flash",
    on_refuted="fallback",  # "fallback" | "raise" | "return_verdict"
    client=client,
)
def legal_advisor_agent(user_query: str) -> dict:
    return {"answer": "Spotřebitel má právo odstoupit od e-shop smlouvy do 7 dnů."}

result = legal_advisor_agent("Jaká je lhůta pro odstoupení od smlouvy?")
print("Proven Answer:", result["answer"])
```

### Direct Dialectical Verification & Axiomat Ingestion

```python
from syntropy import SyntropyClient

client = SyntropyClient()

verdict = client.debate(
    thesis="A consumer can withdraw from a distance contract within 7 days without penalty.",
    world="@pravo:obcansky-zakonik-cz",
    max_failures=3,
    model_name="gemini-2.5-flash",
)

print("Status:", verdict.status)                 # CONFIRMED | REFUTED
print("Winning Thesis:", verdict.winning_thesis)
print("Refuting Argument:", verdict.refuting_argument)
```

### CLI Usage

```bash
python -m syntropy worlds
python -m syntropy axioms @pravo:obcansky-zakonik-cz
python -m syntropy verify "Spotřebitel může odstoupit od smlouvy do 14 dnů." --world @pravo:obcansky-zakonik-cz
```

---

## 3. Model Context Protocol (MCP) Server (`syntropy-mcp`)

Works out-of-the-box with **Claude Desktop**, **Claude Code**, **Cursor**, **Windsurf**, **Cline**, and **Google Antigravity** using either **Node.js (`npx`)** or **Python (`uvx` / `python -m syntropy mcp`)**.

### Option A: Zero-Install via `npx` (Node.js)

Add to `.cursor/mcp.json` or `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "synproof-syntropy": {
      "command": "npx",
      "args": ["-y", "syntropy-mcp"],
      "env": {
        "SYNTROPY_API_KEY": "YOUR_SYNTROPY_OR_GEMINI_OR_OPENROUTER_KEY"
      }
    }
  }
}
```

### Option B: Via Python (`syntropy-client`)

```json
{
  "mcpServers": {
    "synproof-syntropy": {
      "command": "python",
      "args": ["-m", "syntropy", "mcp"],
      "env": {
        "SYNTROPY_API_KEY": "YOUR_SYNTROPY_OR_GEMINI_OR_OPENROUTER_KEY"
      }
    }
  }
}
```

### Exposed MCP Tools
- `syntropy_verify` — Put any claim, code assumption, or legal clause on formal 5-sieve dialectical trial against a Small World.
- `syntropy_list_worlds` — List verified public Small Worlds (`@law:...`, `@pravo:...`, `@medicine:...`, `@finance:...`, `@physics:...`).
- `syntropy_get_world_axioms` — Inspect all atomic axioms of a Small World.
- `syntropy_fork_world` — Fork a public Small World into an isolated private workspace.
- `syntropy_ingest_axioms` — Compile raw contracts, policies, or JSON database rows into formal axioms via Axiomat.
- `syntropy_get_onboarding_guide` — Retrieve the interactive implementation wizard (`SKILL.md`).

---

## 4. Drop-In OpenAI / OpenRouter Compatible Proxy (`/v1/chat/completions`)

Use Synproof's Syntropy from **any language** (TypeScript, Go, Rust, Python, Vercel AI SDK, LangChain) by pointing the standard OpenAI SDK to `https://api.synproof.ai/v1`:

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://api.synproof.ai/v1",
  apiKey: process.env.SYNTROPY_API_KEY, // or GEMINI_API_KEY / OPENROUTER_API_KEY
});

const response = await client.chat.completions.create({
  model: "gemini-2.5-flash",
  messages: [
    { role: "user", content: "Can a company in insolvency freely set off mutual claims?" }
  ],
  // @ts-expect-error syntropy extension
  syntropy: {
    world: "@law:insolvency-code",
    max_failures: 3,
    mode: "verify_output",
    action_on_refuted: "fallback"
  }
});

console.log(response.choices[0].message.content);
```

---

## License

MIT © [Synproof](https://synproof.ai)
