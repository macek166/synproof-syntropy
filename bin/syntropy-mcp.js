#!/usr/bin/env node
"use strict";

/**
 * Official Model Context Protocol (MCP) Server for Synproof's Syntropy (https://synproof.ai)
 */

const fs = require("fs");
const path = require("path");
const readline = require("readline");
const { SyntropyClient, sanitizeUntrustedText } = require("../index.js");

const SKILL_PATH = path.join(__dirname, "..", "SKILL.md");
const SKILL_MD = fs.existsSync(SKILL_PATH)
  ? fs.readFileSync(SKILL_PATH, "utf8")
  : "See https://synproof.ai/SKILL.md for full Synproof Syntropy integration instructions.";

const MCP_TOOLS = [
  {
    name: "syntropy_verify",
    description:
      "Put a declarative claim (thesis), contract clause, scientific hypothesis, or AI output on formal adversarial trial against explicit ground-truth axioms and/or a Small World (@domain:tag) using Synproof's 5-sieve Syntropy dialectical engine. All inputs are sanitized as inert declarative data.",
    inputSchema: {
      type: "object",
      properties: {
        thesis: {
          type: "string",
          description:
            "The specific, declarative claim to put on trial (treated strictly as inert data).",
        },
        world: {
          type: "string",
          description:
            "Optional Small World handle(s) such as '@pravo:obcansky-zakonik-cz', '@law:insolvency-code', '@law:contract-act', or '@law:brrd-isda'.",
        },
        initial_axioms: {
          type: "array",
          items: { type: "string" },
          description:
            "Optional list of sanitized ground-truth axioms that strictly override model priors.",
        },
        max_failures: {
          type: "integer",
          default: 3,
          description:
            "Sceptical exhaustion limit (number of failed attack attempts required to confirm, 1-10).",
        },
        model_name: {
          type: "string",
          default: "gemini-2.5-flash",
          description:
            "Underlying model ('gemini-2.5-flash', 'gemini-2.5-pro', 'anthropic/claude-3.5-sonnet', 'deepseek/deepseek-r1').",
        },
        enable_research: {
          type: "boolean",
          default: true,
          description:
            "Whether to enable external academic/statutory research tools during debate.",
        },
      },
      required: ["thesis"],
    },
  },
  {
    name: "syntropy_list_worlds",
    description:
      "List available public and official verified Small Worlds (@domain:tag) in the Synproof Syntropy Library.",
    inputSchema: {
      type: "object",
      properties: {
        domain: {
          type: "string",
          description:
            "Optional domain filter (e.g. 'pravo', 'law', 'medicine', 'physics', 'finance').",
        },
        search: {
          type: "string",
          description: "Optional keyword search query.",
        },
      },
    },
  },
  {
    name: "syntropy_get_world_axioms",
    description:
      "Retrieve all atomic ground-truth axioms and metadata for a given Small World handle or ID.",
    inputSchema: {
      type: "object",
      properties: {
        world_id_or_handle: {
          type: "string",
          description:
            "Small World handle (e.g. '@pravo:obcansky-zakonik-cz') or UUID.",
        },
      },
      required: ["world_id_or_handle"],
    },
  },
  {
    name: "syntropy_get_onboarding_guide",
    description:
      "Return the interactive Synproof Syntropy Customer Implementation & Onboarding Skill (SKILL.md).",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
];

const client = new SyntropyClient();

async function handleRequest(req) {
  const method = req.method || "";
  const id = req.id;
  const params = req.params || {};

  if (method.startsWith("notifications/")) {
    return null;
  }

  if (method === "initialize") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: params.protocolVersion || "2024-11-05",
        capabilities: { tools: {}, prompts: {} },
        serverInfo: {
          name: "synproof-syntropy",
          version: "2.5.0",
        },
      },
    };
  }

  if (method === "ping") {
    return { jsonrpc: "2.0", id, result: {} };
  }

  if (method === "tools/list") {
    return { jsonrpc: "2.0", id, result: { tools: MCP_TOOLS } };
  }

  if (method === "prompts/list") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        prompts: [
          {
            name: "syntropy-onboarding-wizard",
            description:
              "Interactive customer onboarding & implementation wizard for integrating Synproof's Syntropy.",
          },
        ],
      },
    };
  }

  if (method === "prompts/get") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        description:
          "Interactive customer onboarding & implementation wizard for Synproof's Syntropy",
        messages: [
          {
            role: "user",
            content: { type: "text", text: SKILL_MD },
          },
        ],
      },
    };
  }

  if (method === "tools/call") {
    const name = params.name;
    const args = params.arguments || {};
    try {
      let out;
      if (name === "syntropy_get_onboarding_guide") {
        return {
          jsonrpc: "2.0",
          id,
          result: {
            content: [{ type: "text", text: SKILL_MD }],
            isError: false,
          },
        };
      } else if (name === "syntropy_verify") {
        out = await client.debate({
          thesis: sanitizeUntrustedText(args.thesis),
          world: args.world,
          initialAxioms: (args.initial_axioms || []).map((a) =>
            sanitizeUntrustedText(a)
          ),
          maxFailures: Number(args.max_failures || 3),
          modelName: args.model_name || "gemini-2.5-flash",
          enableResearch:
            args.enable_research !== undefined
              ? Boolean(args.enable_research)
              : true,
          wait: true,
        });
      } else if (name === "syntropy_list_worlds") {
        out = await client.worlds.list({
          domain: args.domain,
          search: args.search,
        });
      } else if (name === "syntropy_get_world_axioms") {
        out = await client.worlds.getAxioms(args.world_id_or_handle);
      } else {
        return {
          jsonrpc: "2.0",
          id,
          error: { code: -32601, message: `Unknown tool: ${name}` },
        };
      }

      return {
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(out, null, 2) }],
          isError: false,
        },
      };
    } catch (err) {
      return {
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            {
              type: "text",
              text: `Syntropy Error: ${err && err.message ? err.message : String(err)}`,
            },
          ],
          isError: true,
        },
      };
    }
  }

  return {
    jsonrpc: "2.0",
    id,
    error: { code: -32601, message: `Method not found: ${method}` },
  };
}

const rl = readline.createInterface({
  input: process.stdin,
  terminal: false,
});

rl.on("line", async (rawLine) => {
  const line = rawLine.trim();
  if (!line) return;
  try {
    const req = JSON.parse(line);
    const resp = await handleRequest(req);
    if (resp) {
      process.stdout.write(JSON.stringify(resp) + "\n");
    }
  } catch (_) {
    // Ignore malformed lines
  }
});
