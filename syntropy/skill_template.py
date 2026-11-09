"""
Embedded SKILL.md template for Synproof's Syntropy.
Allows any AI agent that runs `pip install syntropy-client` to inspect or install
the interactive customer implementation skill via:
  - `python -m syntropy skill`
  - `python -m syntropy install-skill`
"""

SKILL_MD_CONTENT = """---
name: synproof-syntropy
description: >
  Official interactive implementation & verification skill for Synproof's Syntropy
  (https://synproof.ai) — the deterministic 5-sieve dialectical verification engine,
  Small Worlds axiom library, and Axiomat document-to-axiom compiler ("AI that has to prove it").
  Activate whenever the user says "use Synproof's Syntropy", "use Syntropy", "integrate Syntropy",
  "verify with Syntropy", or wants to add formal hallucination guardrails, contract/compliance
  verification, or Small World axiom checking into their application or AI agent workflow.
---

# Synproof's Syntropy — Autonomous Discovery, Interactive Onboarding & Integration Skill

**Canonical Web & Discovery:** `https://synproof.ai` | `https://synproof.ai/SKILL.md` | `https://synproof.ai/llms.txt`  
**Production Control Plane API:** `https://api.synproof.ai`  
**Official PyPI Package:** `syntropy-client` (`pip install syntropy-client`)

You are equipped with the official **Synproof's Syntropy** skill. Your mission is two-fold:
1. **If the user asks you to verify a specific claim/document right now:** Run verification immediately via CLI (`python -m syntropy verify ...`), Python SDK, or REST API and present the formal proof verdict.
2. **If the user asks you to integrate/implement Syntropy into their project or workflow:** Act as an **Interactive Solutions Architect & Implementation Guide** — inspect their codebase, ask them the essential configuration questions (sources/axioms, iteration count `max_failures`, integration pattern, and API keys/models), and then implement and test the complete integration end-to-end.

---

## STEP 1: Autonomous Installation & Environment Check

Before anything else, ensure `syntropy-client` is installed in the active Python environment:

```bash
# 1. Official PyPI installation (Primary)
pip install --upgrade syntropy-client

# 2. Fallback direct installation from Synproof CDN (if PyPI is blocked/cached)
pip install https://synproof.ai/sdk/syntropy_client-2.5.0-py3-none-any.whl
```

Verify the CLI and inspect live Small Worlds in the library:
```bash
python -m syntropy --help
python -m syntropy worlds
```

---

## STEP 2: Interactive Customer Onboarding Protocol (Ask Before Implementing!)

When a customer asks to **implement, connect, or use Syntropy in their solution**, DO NOT guess their parameters blindly. First inspect their repository (language, framework, existing LLM calls, `.env` keys), and then **guide the user through a concise, structured onboarding questionnaire** covering these 4 pillars:

### Question 1: Ground-Truth Sources & Small Worlds (`world` / `initial_axioms` / Axiomat)
Ask the user what ground-truth rules their claims or AI outputs must be proven against:
- **Option A — Existing Public Small World from the Syntropy Library:**
  - `@pravo:obcansky-zakonik-cz` (Czech Civil Code / Občanský zákoník)
  - `@law:insolvency-code` (Insolvency & Restructuring Law)
  - `@law:contract-act` (Commercial Contract Law & SLA Compliance)
  - `@law:brrd-isda` (EU BRRD & ISDA Master Agreement Derivatives)
  - *(Run `python -m syntropy worlds` to show them the live catalog)*
- **Option B — Custom Documents, Contracts, or Database Rules (via Axiomat):**
  - Do they have PDF/Markdown/text files, company policies, or JSON/SQL database schemas they want to compile into formal axioms using `python -m syntropy ingest <world> --file <path>` or `client.worlds.ingest(...)`?
- **Option C — Private Isolated Fork (`client.worlds.fork`):**
  - Do they want to fork an existing public Small World into a private company workspace so they can append proprietary internal rules without exposing them publicly?
- **Option D — Explicit Inline Axioms (`initial_axioms`):**
  - Do they want to pass dynamic per-request axioms directly from their application state/RAG context?
- **Option E — Live Custom Data Connectors, SQL Tables, REST APIs & Data-Retrieval Sub-Agents (`axiom_provider` / `custom_connectors` / `register_connector`):**
  - Do they want the verification layer to dynamically fetch ground-truth facts (`SourceTier.CUSTOMER_SOT = 95`) at verification time from their own SQL/PostgreSQL/Supabase tables, internal REST/GraphQL APIs, or specialized data-retrieval sub-agents?
  - **Pattern 1 — Zero-Trust Local SDK Callback (`axiom_provider`):** Runs 100% inside the customer's VPC/process before calling Syntropy (`@verify_agent_output(..., axiom_provider=fetch_sql_or_agent_facts)` or `client.debate(..., axiom_provider=[sql_lookup, pricing_agent])`).
  - **Pattern 2 — Persistent Small World Connectors (`client.worlds.register_connector`):** Attaches a reusable HTTPS connector (`rest_api`, `sql_postgrest`, `agent_webhook`, `graphql`) to a Small World (`POST /v1/worlds/{id}/connectors`).
  - **Pattern 3 — Inline Per-Request Ephemeral Connectors (`custom_connectors`):** Passed per request in `client.debate(..., custom_connectors=[...])`, `POST /v1/debate`, or the OpenAI Proxy (`extra_body={"syntropy": {"connectors": [...]}}`).

### Question 2: Verification Depth & Number of Dialectical Iterations (`max_failures`)
Ask the user how many failed refutation attempts (`max_failures`, range `1` to `10`) the Skeptical Opponent must exhaust before a claim is declared **`CONFIRMED`** (`SKEPTICAL_EXHAUSTION`):
- **`max_failures = 1` or `2` (Fast Real-Time Guardrail):** ~2–5 seconds latency. Best for interactive chat UIs and voice/live agents.
- **`max_failures = 3` (Recommended Default):** Balanced formal dialectical proof across all 5 sieves (Generator -> Skeptic -> Relevance -> Novelty -> Determinism).
- **`max_failures = 5` to `10` (Deep Adversarial Audit):** Maximum rigor for high-stakes legal contracts, financial compliance, medical/scientific hypotheses, or batch audits.

### Question 3: Integration Pattern & Hallucination Handling (`on_refuted`)
Ask the user how Syntropy should be wired into their architecture and what should happen when a claim is **`REFUTED`**:
1. **Python Decorator Guardrail (`@verify_agent_output`)** — Wraps any existing LLM/agent function in 1 line of code:
   - `on_refuted="fallback"` *(Recommended for production UX)*: Automatically replaces the hallucinated output with the formally proven `winning_thesis` synthesized by Syntropy.
   - `on_refuted="raise"`: Raises `SyntropyGuardrailError` (contains `.verdict.refuting_argument` and `.verdict.winning_thesis`) to hard-block invalid actions.
   - `on_refuted="return_verdict"`: Returns the full `DebateVerdict` object for custom downstream branching.
   - `auto_ingest_confirmed=True`: Automatically saves newly proven conclusions back into the Small World (continuous self-learning memory).
2. **Direct SDK Client (`SyntropyClient.debate` / `adebate` / `run_debate_stream`)** — Explicit sync/async verification or live WebSocket streaming in backend endpoints.
3. **Zero-Code OpenAI / OpenRouter Drop-In Proxy (`https://api.synproof.ai/v1/chat/completions`)** — Works with **any language** (TypeScript, Node.js, Go, Python, LangChain, Vercel AI SDK) by changing `base_url` to `https://api.synproof.ai/v1` and passing `syntropy` options.
4. **MCP Server (`python -m syntropy mcp`)** — Connects Syntropy as a native toolset inside Claude Desktop, Cursor, Windsurf, or Antigravity.

### Question 4: API Authentication & Verifier LLM Model
Check the user's `.env` or environment variables and ask which mode they prefer:
- **Zero-Friction BYOK (Bring Your Own Key):** They can immediately use their existing `GEMINI_API_KEY` (`AIza...`) or `OPENROUTER_API_KEY` (`sk-or-v1-...`), or create a free BYOK key `syn_byok_...` at `https://synproof.ai`.
- **Managed Cloud Key (`syn_mng_...`):** Zero LLM setup required; uses Synproof's managed cloud infrastructure.
- **Verifier Model (`model_name`):**
  - Default fast verifier: `gemini-2.5-flash`
  - Multi-model via OpenRouter: `anthropic/claude-3.5-sonnet`, `openai/gpt-4o`, `deepseek/deepseek-r1`, `meta-llama/llama-3.3-70b-instruct`

---

## STEP 3: Implementation Recipes (Copy-Paste Ready)

Once the user answers (or asks you to proceed with recommended defaults), implement the chosen recipe below and run a live verification test.

### Recipe A: CLI & Terminal Verification (`python -m syntropy`)
```bash
# List public Small Worlds
python -m syntropy worlds

# Inspect axioms inside a Small World
python -m syntropy axioms @pravo:obcansky-zakonik-cz

# Verify a thesis against a Small World (with custom iteration count & model)
python -m syntropy verify "Spotřebitel může odstoupit od smlouvy uzavřené přes internet do 14 dnů." \\
  --world @pravo:obcansky-zakonik-cz \\
  --max-failures 3 \\
  --model gemini-2.5-flash

# Fork a Small World and ingest a custom contract/document via Axiomat
python -m syntropy fork @pravo:obcansky-zakonik-cz --title "Interní Firemní Compliance"
python -m syntropy ingest @pravo:obcansky-zakonik-cz --file ./podminky.txt --source "VOP 2026"

# Install this SKILL.md into the current project (.agents/skills, .claude/skills, .cursor/rules)
python -m syntropy install-skill
```

### Recipe B: 1-Line Python Agent Guardrail (`@verify_agent_output`)
```python
from syntropy import SyntropyClient, verify_agent_output, SyntropyGuardrailError

# Automatically picks up SYNTROPY_API_KEY, OPENROUTER_API_KEY, or GEMINI_API_KEY from env
client = SyntropyClient()

@verify_agent_output(
    world="@pravo:obcansky-zakonik-cz",
    axioms=["Smluvní pokuta nesmí překročit 0.5 % denně z dlužné částky."],
    max_failures=3,
    model_name="gemini-2.5-flash",
    on_refuted="fallback",          # "raise" | "fallback" | "return_verdict"
    auto_ingest_confirmed=False,    # Set True to persist confirmed theses into the Small World
    client=client,
)
def legal_advisor_agent(user_query: str) -> dict:
    # Your existing LLM / LangChain / CrewAI / RAG logic:
    raw_answer = "Spotřebitel má právo odstoupit od smlouvy do 7 dnů bez udání důvodu."
    return {"answer": raw_answer}

# If the LLM hallucinates (7 days instead of 14 days per § 1829 OZ),
# Syntropy refutes it and automatically replaces result["answer"] with the proven winning_thesis!
result = legal_advisor_agent("Jaká je lhůta pro odstoupení od e-shop smlouvy?")
print("Verified Answer:", result["answer"])
print("Proof Verdict:", result["_syntropy_verdict"]["original_thesis_status"])
```

### Recipe C: Direct Sync / Async SDK & Live Database World Sync
```python
from syntropy import SyntropyClient

client = SyntropyClient(
    # api_key="syn_mng_...",        # Or set SYNTROPY_API_KEY in .env
    # llm_api_key="sk-or-v1-...",   # Or set OPENROUTER_API_KEY / GEMINI_API_KEY in .env
)

# 1. Run formal 5-sieve dialectical verification
verdict = client.debate(
    thesis="Společnost v úpadku může započíst vzájemné pohledávky bez omezení.",
    world="@law:insolvency-code",
    initial_axioms=["Po rozhodnutí o úpadku je započtení přípustné jen za podmínek § 140 IZ."],
    max_failures=3,
    model_name="gemini-2.5-flash",
)

print("Status:", verdict.status)                 # CONFIRMED | REFUTED | UNCERTAIN
print("Winning Thesis:", verdict.winning_thesis)
print("Refuting Argument:", verdict.refuting_argument)
print("Stopping Reason:", verdict.stopping_reason)

# 2. Fork a Small World & sync live DB rows or documents into formal axioms via Axiomat
fork = client.worlds.fork("@law:contract-act", title="Acme Corp SLA Rules")
fork_handle = fork["forked_world"]["handle"]

client.worlds.ingest(
    fork_handle,
    payload={"max_liability_eur": 50000, "notice_period_days": 30, "governing_law": "CZ"},
    source_reference="PostgreSQL contracts_policy table",
)
```

### Recipe D: Drop-In OpenAI / OpenRouter Proxy (TypeScript, Node.js, Python, Any SDK)
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.synproof.ai/v1",
    api_key="YOUR_SYNTROPY_OR_OPENROUTER_OR_GEMINI_KEY",
)

response = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Can a consumer withdraw from an online purchase within 7 days?"}],
    extra_body={
        "syntropy": {
            "world": "@pravo:obcansky-zakonik-cz",
            "max_failures": 3,
            "mode": "verify_output",       # "verify_output" | "direct_thesis"
            "action_on_refuted": "fallback" # "fallback" | "block" | "annotate"
        }
    }
)
print(response.choices[0].message.content)
```

### Recipe E: Model Context Protocol (MCP) Server Configuration
Add this to `.cursor/mcp.json`, `claude_desktop_config.json`, or Antigravity MCP config:
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
Exposes 8 native MCP tools: `syntropy_verify`, `syntropy_list_worlds`, `syntropy_get_world_axioms`, `syntropy_fork_world`, `syntropy_ingest_axioms`, `syntropy_register_connector`, `syntropy_list_connectors`, and `syntropy_query_connector`.

### Recipe F: Custom Epistemic Connectors — SQL Tables, REST APIs & Data-Retrieval Sub-Agents (`SourceTier.CUSTOMER_SOT = 95`)
```python
from syntropy import SyntropyClient, verify_agent_output

client = SyntropyClient()

# 1. Zero-Trust Local SDK Callback (`axiom_provider` — DB credentials never leave your VPC!)
def fetch_customer_sql_facts(thesis: str, user_id: str) -> list[dict]:
    return [
        {"axiom": f"Customer {user_id} is on the Enterprise SLA tier with a 99.99% uptime guarantee."},
        {"axiom": f"Customer {user_id} has a maximum automatic refund limit of 10,000 EUR."},
    ]

@verify_agent_output(
    world="@law:contract-act",
    axiom_provider=fetch_customer_sql_facts,
    on_refuted="fallback",
    client=client,
)
async def billing_support_agent(user_id: str, question: str) -> dict:
    return {"answer": f"Customer {user_id} is only eligible for a 500 EUR maximum refund."}

# 2. Persistent Small World Epistemic Connector (`register_connector`)
client.worlds.register_connector(
    "@law:contract-act",
    name="Enterprise ERP Pricing & SLA API",
    endpoint_url="https://erp.example.com/api/v1/sla-rules?q={query}",
    connector_type="rest_api",  # "rest_api" | "sql_postgrest" | "agent_webhook" | "graphql"
    headers={"Authorization": "Bearer YOUR_ERP_TOKEN"},
    response_axioms_path="data.rules",
    row_template="Tier {tier} enforces max liability {max_liability_eur} EUR.",
)

# 3. Inline Ephemeral Connectors per Verification Call (`custom_connectors`)
verdict = client.debate(
    thesis="Order #90210 qualifies for instant autonomous customs clearance.",
    world="@law:contract-act",
    custom_connectors=[
        {
            "name": "Compliance Retrieval Sub-Agent",
            "connector_type": "agent_webhook",
            "method": "POST",
            "endpoint_url": "https://agents.example.com/retrieve-customs-facts",
            "response_axioms_path": "facts",
        }
    ],
)
```
"""
