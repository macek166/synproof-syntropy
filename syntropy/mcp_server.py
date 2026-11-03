import sys
import json
from typing import Any, Dict, List, Optional
from .client import SyntropyClient, DebateVerdict
from .skill_template import SKILL_MD_CONTENT


MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "syntropy_verify",
        "description": (
            "Put a falsifiable claim (thesis), contract clause, scientific hypothesis, or AI output "
            "on formal adversarial trial against explicit ground-truth axioms and/or a Small World "
            "(@domain:tag) using Synproof's 5-sieve Syntropy dialectical engine. Returns a deterministic "
            "CONFIRMED or REFUTED verdict, winning thesis, refuting argument, and triggered axioms."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "thesis": {
                    "type": "string",
                    "description": "The specific, declarative claim to put on trial.",
                },
                "world": {
                    "type": "string",
                    "description": (
                        "Optional Small World handle(s) such as '@pravo:obcansky-zakonik-cz', "
                        "'@law:insolvency-code', '@law:contract-act', or '@law:brrd-isda'."
                    ),
                },
                "initial_axioms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of explicit ground-truth axioms that strictly override model priors.",
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
                    "description": "Optional domain filter (e.g. 'pravo', 'law', 'medicine', 'physics', 'finance').",
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
                    "description": "Small World handle (e.g. '@pravo:obcansky-zakonik-cz') or UUID.",
                },
            },
            "required": ["world_id_or_handle"],
        },
    },
    {
        "name": "syntropy_fork_world",
        "description": "Create an isolated private fork of a public Small World so custom rules can be ingested without altering public axioms.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "world_id_or_handle": {
                    "type": "string",
                    "description": "Source Small World handle or ID to fork.",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the new private fork.",
                },
            },
            "required": ["world_id_or_handle"],
        },
    },
    {
        "name": "syntropy_ingest_axioms",
        "description": "Extract and synchronize atomic axioms from raw text or a JSON record into a Small World via Axiomat with deduplication and conflict resolution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "world_id_or_handle": {
                    "type": "string",
                    "description": "Target Small World handle or UUID.",
                },
                "text": {
                    "type": "string",
                    "description": "Raw regulatory, contractual, or policy text to compile into atomic axioms.",
                },
                "payload": {
                    "type": "object",
                    "description": "Optional structured JSON/database record to compile into axioms.",
                },
                "source_reference": {
                    "type": "string",
                    "description": "Citation or source identifier for the ingested axioms.",
                },
                "on_conflict": {
                    "type": "string",
                    "enum": ["flag", "replace", "keep"],
                    "default": "flag",
                    "description": "Conflict resolution policy when new axioms contradict existing ones.",
                },
            },
            "required": ["world_id_or_handle"],
        },
    },
    {
        "name": "syntropy_get_onboarding_guide",
        "description": (
            "Return the complete interactive Synproof Syntropy Customer Implementation & Onboarding Skill (SKILL.md). "
            "Call this tool whenever the user asks to integrate, set up, or connect Syntropy into their project so you "
            "know which questions to ask (ground-truth sources, max_failures iterations, on_refuted behavior, API keys) "
            "and which SDK/Proxy code templates to apply."
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
                    "version": "2.5.0",
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
                verdict = syn_client.debate.verify(
                    thesis=args["thesis"],
                    world=args.get("world"),
                    initial_axioms=args.get("initial_axioms"),
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
                out = syn_client.worlds.get_axioms(args["world_id_or_handle"])
            elif tool_name == "syntropy_fork_world":
                out = syn_client.worlds.fork(
                    args["world_id_or_handle"],
                    title=args.get("title"),
                )
            elif tool_name == "syntropy_ingest_axioms":
                out = syn_client.worlds.ingest(
                    args["world_id_or_handle"],
                    text=args.get("text"),
                    payload=args.get("payload"),
                    source_reference=args.get("source_reference"),
                    on_conflict=args.get("on_conflict", "flag"),
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
        except json.JSONDecodeError:
            continue
        resp = handle_mcp_request(req, client=client)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_mcp_server()
