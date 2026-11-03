import sys
import json
import argparse
from typing import List, Optional
from .client import SyntropyClient, DebateVerdict, sanitize_untrusted_text
from .mcp_server import run_stdio_mcp_server
from .skill_template import SKILL_MD_CONTENT


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="syntropy",
        description="Synproof's Syntropy CLI & MCP Server — Deterministic Dialectical Verification Layer for AI (https://synproof.ai)",
    )
    parser.add_argument("--api-key", help="Syntropy API key or set SYNTROPY_API_KEY in environment")
    parser.add_argument("--base-url", help="API base URL (default: https://api.synproof.ai)")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # 1. syntropy verify "<thesis>"
    p_verify = subparsers.add_parser("verify", help="Verify a declarative thesis against a Small World and/or explicit axioms")
    p_verify.add_argument("thesis", help="The falsifiable claim to put on trial")
    p_verify.add_argument("-w", "--world", help="Small World handle(s), e.g. @pravo:obcansky-zakonik-cz")
    p_verify.add_argument("-a", "--axiom", action="append", default=[], help="Inline ground-truth axiom (can be passed multiple times)")
    p_verify.add_argument("-m", "--model", default="gemini-2.5-flash", help="Model name (default: gemini-2.5-flash)")
    p_verify.add_argument("--max-failures", type=int, default=3, help="Sceptical exhaustion limit (default: 3)")
    p_verify.add_argument("--no-research", action="store_true", help="Disable external academic/statutory research tools")
    p_verify.add_argument("--json", action="store_true", help="Output raw JSON verdict")

    # 2. syntropy worlds
    p_worlds = subparsers.add_parser("worlds", help="List available Small Worlds in the Syntropy Library")
    p_worlds.add_argument("--domain", help="Filter by domain (e.g. pravo, law, medicine, physics, finance)")
    p_worlds.add_argument("--search", help="Filter by search query")
    p_worlds.add_argument("--json", action="store_true", help="Output raw JSON")

    # 3. syntropy axioms <world>
    p_axioms = subparsers.add_parser("axioms", help="Inspect all axioms of a Small World")
    p_axioms.add_argument("world", help="Small World handle (e.g. @pravo:obcansky-zakonik-cz) or UUID")
    p_axioms.add_argument("--json", action="store_true", help="Output raw JSON")

    # 4. syntropy mcp
    subparsers.add_parser("mcp", help="Start the built-in Model Context Protocol (MCP) stdio server for AI agents")

    # 5. syntropy skill
    subparsers.add_parser("skill", help="Print the interactive SKILL.md implementation guide for AI agents")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    if args.command == "mcp":
        run_stdio_mcp_server()
        return 0

    if args.command == "skill":
        print(SKILL_MD_CONTENT)
        return 0

    client = SyntropyClient(
        api_key=args.api_key,
        base_url=args.base_url,
    )

    try:
        if args.command == "verify":
            safe_thesis = sanitize_untrusted_text(args.thesis)
            safe_axioms = [sanitize_untrusted_text(a) for a in (args.axiom or [])]
            verdict = client.debate.verify(
                thesis=safe_thesis,
                world=args.world,
                initial_axioms=safe_axioms,
                max_failures=args.max_failures,
                model_name=args.model,
                enable_research=not args.no_research,
                wait=True,
            )
            assert isinstance(verdict, DebateVerdict)
            if args.json:
                out = {
                    "job_id": verdict.job_id,
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
                print(json.dumps(out, ensure_ascii=False, indent=2))
            else:
                badge = "[CONFIRMED]" if verdict.is_confirmed else "[REFUTED]"
                print(f"{badge} Status: {verdict.status} (Stopping reason: {verdict.stopping_reason})")
                print(f"Thesis: {verdict.thesis}")
                if verdict.winning_thesis:
                    print(f"Winning Thesis: {verdict.winning_thesis}")
                if verdict.refuting_argument:
                    print(f"Refuting Argument: {verdict.refuting_argument}")
                print(f"Steps: {verdict.total_iterations} | Tokens: {verdict.telemetry.total_tokens}")
            return 0 if verdict.is_confirmed else 2

        if args.command == "worlds":
            res = client.worlds.list(domain=args.domain, search=args.search)
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                worlds = res.get("worlds", [])
                for w in worlds:
                    print(f"{w.get('handle', w.get('id')):<42} | {w.get('domain', ''):<14} | {w.get('title', '')}")
            return 0

        if args.command == "axioms":
            res = client.worlds.get_axioms(args.world)
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                axioms = res.get("axioms", [])
                print(f"Small World '{args.world}' ({len(axioms)} axioms):")
                for i, ax in enumerate(axioms, 1):
                    stmt = ax.get("statement") or ax.get("axiom_text") or ""
                    src = ax.get("source_reference") or ax.get("source_ref") or ""
                    print(f"  {i}. {stmt} [{src}]")
            return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
