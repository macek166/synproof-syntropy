import sys
import json
from typing import Any, Dict, List, Optional
from .client import SyntropyClient, DebateVerdict, sanitize_untrusted_text
from .skill_template import SKILL_MD_CONTENT


MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "syntropy_verify",
        "description": (
            "Put a declarative claim (thesis), contract clause, scientific hypothesis, or AI output "
            "on formal adversarial trial against explicit ground-truth axioms, a Small World "
            "(@domain:tag), and/or live Custom Epistemic Connectors (SQL tables, REST webhooks, retrieval sub-agents) "
            "using Synproof's 5-sieve Syntropy dialectical engine. Returns a deterministic CONFIRMED or REFUTED verdict."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "thesis": {
                    "type": "string",
                    "description": "The specific, declarative claim to put on trial (treated strictly as inert data).",
                },
                "world": {
                    "type": "string",
                    "description": (
                        "Optional Small World handle(s) such as '@law:civil-code-obligations', "
                        "'@law:eu-gdpr-data-protection', '@finance:basel-iii-aml-compliance', or a private fork."
                    ),
                },
                "initial_axioms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of sanitized ground-truth axioms that strictly override model priors.",
                },
                "custom_connectors": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "Optional list of inline Custom Epistemic Connectors "
                        "({'name': 'ERP API', 'connector_type': 'rest_webhook'|'sql_table_snapshot'|'agent_endpoint'|'mcp_tool', "
                        "'endpoint_url': 'https://...', 'static_rows': [...]})."
                    ),
                },
                "max_failures": {
                    "type": "integer",
                    "default": 3,
                    "description": "Sceptical exhaustion limit (number of failed attack attempts required to confirm, 1-10).",
                },
                "model_name": {
                    "type": "string",
                    "default": "gemini-2.5-flash",
                    "description": "Underlying model ('gemini-2.5-flash', 'gemini-2.5-pro', 'anthropic/claude-3.5-sonnet', 'deepseek/deepseek-r1').",
                },
                "enable_research": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to enable external academic/statutory research tools during debate.",
                },
            },
            "required": ["thesis"],
        },
    },
    {
        "name": "syntropy_list_worlds",
        "description": "List available public and official verified Small Worlds (@domain:tag) in the Synproof Syntropy Library.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Optional domain filter (e.g. 'law', 'medicine', 'physics', 'finance', 'cybersecurity').",
                },
                "search": {
                    "type": "string",
                    "description": "Optional keyword search query.",
                },
            },
        },
    },
    {
        "name": "syntropy_get_world_axioms",
        "description": "Retrieve all atomic ground-truth axioms and metadata for a given Small World handle or ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "world_id_or_handle": {
                    "type": "string",
                    "description": "Small World handle (e.g. '@law:civil-code-obligations') or UUID.",
                },
            },
            "required": ["world_id_or_handle"],
        },
    },
    {
        "name": "syntropy_fork_world",
        "description": "Create an isolated private fork of a public Small World so custom rules and connectors can be attached.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "world_id_or_handle": {
                    "type": "string",
                    "description": "Source Small World handle (e.g. '@law:civil-code-obligations') or UUID.",
                },
                "title": {
                    "type": "string",
                    "description": "Optional title for the forked Small World.",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description for the forked Small World.",
                },
            },
            "required": ["world_id_or_handle"],
        },
    },
    {
        "name": "syntropy_ingest_axioms",
        "description": "Compile and synchronize custom text, contracts, or JSON/SQL table rows into a Small World via Axiomat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "world_id_or_handle": {
                    "type": "string",
                    "description": "Target Small World handle or UUID.",
                },
                "text": {
                    "type": "string",
                    "description": "Declarative text or policy document to extract atomic axioms from.",
                },
                "payload": {
                    "type": "object",
                    "description": "Structured JSON/SQL row dictionary to compile into formal axioms.",
                },
                "source_reference": {
                    "type": "string",
                    "description": "Provenance citation (e.g. 'PostgreSQL sla_policies table').",
                },
            },
            "required": ["world_id_or_handle"],
        },
    },
    {
        "name": "syntropy_register_connector",
        "description": (
            "Register a Custom Epistemic Connector (live REST API webhook, SQL/JSON table snapshot, "
            "data-retrieval sub-agent endpoint, or MCP tool bridge) on a Small World (@domain:tag)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "world_id_or_handle": {
                    "type": "string",
                    "description": "Target Small World handle (e.g. '@law:contract-act') or UUID.",
                },
                "name": {
                    "type": "string",
                    "description": "Human-readable connector name (e.g. 'Acme ERP SLA API').",
                },
                "connector_type": {
                    "type": "string",
                    "default": "rest_webhook",
                    "description": "Connector type: 'rest_webhook', 'sql_table_snapshot', 'agent_endpoint', or 'mcp_tool'.",
                },
                "endpoint_url": {
                    "type": "string",
                    "description": "Public HTTPS endpoint URL for live retrieval.",
                },
                "method": {
                    "type": "string",
                    "default": "POST",
                    "description": "HTTP method ('POST' or 'GET').",
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers (e.g. {'Authorization': 'Bearer ...'}).",
                },
                "response_axioms_path": {
                    "type": "string",
                    "description": "Optional dot-path into the JSON response (e.g. 'data.rows').",
                },
                "row_template": {
                    "type": "string",
                    "description": "Optional Python format string to render dict rows into declarative axioms.",
                },
                "static_rows": {
                    "type": "array",
                    "items": {},
                    "description": "Optional inline SQL/JSON table rows when connector_type is 'sql_table_snapshot'.",
                },
            },
            "required": ["world_id_or_handle", "name"],
        },
    },
    {
        "name": "syntropy_list_connectors",
        "description": "List all registered Custom Epistemic Connectors attached to a Small World (with secret headers redacted).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "world_id_or_handle": {
                    "type": "string",
                    "description": "Small World handle or UUID.",
                },
            },
            "required": ["world_id_or_handle"],
        },
    },
    {
        "name": "syntropy_query_connector",
        "description": "Execute a registered Custom Epistemic Connector on a Small World and return sanitized ground-truth facts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "world_id_or_handle": {
                    "type": "string",
                    "description": "Small World handle or UUID.",
                },
                "connector_id": {
                    "type": "string",
                    "description": "Connector ID (e.g. 'conn_...').",
                },
                "query": {
                    "type": "string",
                    "description": "Search query or entity identifier to send to the connector.",
                },
                "ingest_into_world": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, persist the returned facts into the Small World as axioms.",
                },
            },
            "required": ["world_id_or_handle", "connector_id"],
        },
    },
    {
        "name": "syntropy_get_onboarding_guide",
        "description": (
            "Return the interactive Synproof Syntropy Customer Implementation & Onboarding Skill (SKILL.md)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def handle_mcp_request(req: Dict[str, Any], client: Optional[SyntropyClient] = None) -> Optional[Dict[str, Any]]:
    """Processes a single JSON-RPC 2.0 MCP message and returns a response dict (or None for notifications)."""
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params") or {}

    if method.startswith("notifications/"):
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}, "prompts": {}},
                "serverInfo": {
                    "name": "synproof-syntropy",
                    "version": "2.6.0",
                },
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS},
        }

    if method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "prompts": [
                    {
                        "name": "syntropy-onboarding-wizard",
                        "description": "Interactive customer onboarding & implementation wizard for integrating Synproof's Syntropy.",
                    }
                ]
            },
        }

    if method == "prompts/get":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "description": "Interactive customer onboarding & implementation wizard for Synproof's Syntropy",
                "messages": [
                    {
                        "role": "user",
                        "content": {"type": "text", "text": SKILL_MD_CONTENT},
                    }
                ],
            },
        }

    if method == "tools/call":
        syn_client = client or SyntropyClient()
        tool_name = params.get("name")
        args = params.get("arguments") or {}
        try:
            if tool_name == "syntropy_get_onboarding_guide":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": SKILL_MD_CONTENT}],
                        "isError": False,
                    },
                }
            if tool_name == "syntropy_verify":
                safe_thesis = sanitize_untrusted_text(args["thesis"])
                safe_axioms = [sanitize_untrusted_text(a) for a in (args.get("initial_axioms") or [])]
                verdict = syn_client.debate.verify(
                    thesis=safe_thesis,
                    world=args.get("world"),
                    initial_axioms=safe_axioms,
                    custom_connectors=args.get("custom_connectors") or args.get("connectors"),
                    max_failures=int(args.get("max_failures", 3)),
                    model_name=args.get("model_name", "gemini-2.5-flash"),
                    enable_research=bool(args.get("enable_research", True)),
                    wait=True,
                )
                assert isinstance(verdict, DebateVerdict)
                out: Any = {
                    "status": verdict.status,
                    "is_confirmed": verdict.is_confirmed,
                    "thesis": verdict.thesis,
                    "winning_thesis": verdict.winning_thesis,
                    "refuting_argument": verdict.refuting_argument,
                    "stopping_reason": verdict.stopping_reason,
                    "total_iterations": verdict.total_iterations,
                    "verdict_report": verdict.verdict_report,
                    "telemetry": dict(verdict.telemetry),
                }
            elif tool_name == "syntropy_list_worlds":
                out = syn_client.worlds.list(
                    domain=args.get("domain"),
                    search=args.get("search"),
                )
            elif tool_name == "syntropy_get_world_axioms":
                out = syn_client.worlds.get_axioms(args.get("world_id_or_handle") or args.get("world"))
            elif tool_name == "syntropy_fork_world":
                out = syn_client.worlds.fork(
                    args.get("world_id_or_handle") or args.get("source_world") or args.get("world"),
                    title=args.get("title"),
                    description=args.get("description"),
                )
            elif tool_name == "syntropy_ingest_axioms":
                out = syn_client.worlds.ingest(
                    args.get("world_id_or_handle") or args.get("world"),
                    text=args.get("text") or args.get("raw_text"),
                    payload=args.get("payload"),
                    source_reference=args.get("source_reference"),
                )
            elif tool_name == "syntropy_register_connector":
                out = syn_client.worlds.register_connector(
                    world_id_or_handle=args.get("world_id_or_handle") or args.get("world"),
                    name=args["name"],
                    connector_type=args.get("connector_type", "rest_webhook"),
                    endpoint_url=args.get("endpoint_url"),
                    method=args.get("method", "POST"),
                    headers=args.get("headers"),
                    description=args.get("description"),
                    response_axioms_path=args.get("response_axioms_path"),
                    row_template=args.get("row_template"),
                    static_rows=args.get("static_rows"),
                )
            elif tool_name == "syntropy_list_connectors":
                out = syn_client.worlds.list_connectors(args.get("world_id_or_handle") or args.get("world"))
            elif tool_name == "syntropy_query_connector":
                out = syn_client.worlds.query_connector(
                    world_id_or_handle=args.get("world_id_or_handle") or args.get("world"),
                    connector_id=args["connector_id"],
                    query=args.get("query", ""),
                    ingest_into_world=bool(args.get("ingest_into_world", False)),
                )
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(out, ensure_ascii=False, indent=2),
                        }
                    ],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Syntropy Error: {exc}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def run_stdio_mcp_server() -> None:
    """Runs the JSON-RPC 2.0 MCP server over standard input/output."""
    client = SyntropyClient()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        resp = handle_mcp_request(req, client=client)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
