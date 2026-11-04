# Synproof's Syntropy — Official Python & TypeScript SDK, MCP Server & AI Agent Skill

[![Website](https://img.shields.io/badge/Website-synproof.ai-c8a96e?style=flat-square)](https://synproof.ai)
[![PyPI](https://img.shields.io/pypi/v/syntropy-client?style=flat-square&label=PyPI%20syntropy-client)](https://pypi.org/project/syntropy-client/)
[![Documentation](https://img.shields.io/badge/Docs-synproof.ai%2Fdocs-blue?style=flat-square)](https://synproof.ai/docs)
[![AI Agent Skill](https://img.shields.io/badge/Skill-SKILL.md-10b981?style=flat-square)](https://synproof.ai/SKILL.md)
[![OpenAPI 3.1](https://img.shields.io/badge/OpenAPI-3.1.0-6366f1?style=flat-square)](https://synproof.ai/openapi.json)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](./LICENSE)

> **Language models guess. Syntropy proves.**  
> **Synproof's Syntropy** ([https://synproof.ai](https://synproof.ai)) is a deterministic 5-sieve dialectical verification engine and Small Worlds axiom library for AI agents, legal compliance, scientific verification, and enterprise decision pipelines.

---

## Canonical Links & Documentation

| Resource | URL |
| :--- | :--- |
| **Web Platform & Interactive Studio** | [https://synproof.ai](https://synproof.ai) |
| **Developer Documentation (20 Chapters)** | [https://synproof.ai/docs](https://synproof.ai/docs) |
| **OpenRouter Integration Guide** | [https://synproof.ai/docs/openrouter](https://synproof.ai/docs/openrouter) |
| **How the 5-Sieve Architecture Works** | [https://synproof.ai/how-it-works](https://synproof.ai/how-it-works) |
| **AI Coding Agent Skill (`SKILL.md`)** | [https://synproof.ai/SKILL.md](https://synproof.ai/SKILL.md) |
| **OpenAPI 3.1 Specification** | [https://synproof.ai/openapi.json](https://synproof.ai/openapi.json) |
| **Production API Endpoint** | `https://api.synproof.ai` |

---

## 1. Install the AI Coding Agent Skill

Install via the official Skills CLI:

```bash
npx skills add macek166/synproof-syntropy
```

---

## 2. Python SDK & CLI (`syntropy-client`)

### Installation (Official PyPI Registry)

```bash
pip install syntropy-client
```

### 1-Line Hallucination Guardrail (`@verify_agent_output`)

```python
from syntropy import SyntropyClient, verify_agent_output

client = SyntropyClient()  # Reads SYNTROPY_API_KEY from the runtime environment

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

### Direct Dialectical Verification

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

---

## 3. Model Context Protocol (MCP) Server (`syntropy-mcp`)

Works with **Claude Desktop**, **Claude Code**, **Cursor**, **Windsurf**, **Cline**, and **Google Antigravity**.

```json
{
  "mcpServers": {
    "synproof-syntropy": {
      "command": "python",
      "args": ["-m", "syntropy", "mcp"],
      "env": {
        "SYNTROPY_API_KEY": "YOUR_SYNTROPY_API_KEY"
      }
    }
  }
}
```

### Exposed Read & Verification MCP Tools
- `syntropy_verify` — Put any declarative claim, code assumption, or legal clause on formal 5-sieve dialectical trial against a Small World.
- `syntropy_list_worlds` — List verified public Small Worlds (`@law:...`, `@pravo:...`, `@medicine:...`, `@finance:...`, `@physics:...`).
- `syntropy_get_world_axioms` — Inspect all atomic axioms of a Small World.
- `syntropy_get_onboarding_guide` — Retrieve the interactive implementation guide (`SKILL.md`).

---

## 4. Works with OpenRouter (BYOK & Multi-Model Dialectical Routing)

Synproof's Syntropy natively integrates with **[OpenRouter](https://openrouter.ai)** (`https://synproof.ai/docs/openrouter`). You can bring your own OpenRouter API key (`OPENROUTER_API_KEY`) to run formal 5-sieve dialectical verification across any OpenRouter model (`anthropic/claude-3.5-sonnet`, `anthropic/claude-3.7-sonnet`, `deepseek/deepseek-r1`, `openai/gpt-4o`, `openai/o3-mini`, `google/gemini-2.5-pro`, `meta-llama/llama-3.3-70b-instruct`).

```python
from syntropy import SyntropyClient

# Uses OPENROUTER_API_KEY (or SYNTROPY_API_KEY) configured in your runtime environment
client = SyntropyClient()

verdict = client.debate(
    thesis="GDPR requires notifying the supervisory authority of a personal data breach within 72 hours.",
    world="@law:eu-gdpr-data-protection",
    model_name="anthropic/claude-3.5-sonnet",  # Any OpenRouter vendor/model slug
    max_failures=3,
)
print(verdict.status, verdict.winning_thesis)
```

---

## 5. Security & Data Isolation

- **Zero Credential Scanning:** The skill never inspects `.env` files or local credentials. Developers configure `SYNTROPY_API_KEY` in their own runtime environment.
- **Official Registry Only:** Distributed exclusively via PyPI (`syntropy-client`) and GitHub (`macek166/synproof-syntropy`).
- **Prompt-Injection Sanitization:** All untrusted claims and axioms are sanitized (`sanitize_untrusted_text`) to strip control characters and imperative prompt-injection directives before verification.

---

## License

MIT © [Synproof](https://synproof.ai)
