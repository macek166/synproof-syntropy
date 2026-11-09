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
      "Put a declarative claim (thesis), contract clause, scientific hypothesis, or AI output on formal adversarial trial against explicit ground-truth axioms, a Small World (@domain:tag), and/or live Custom Epistemic Connectors (SQL tables, REST webhooks, retrieval sub-agents) using Synproof's 5-sieve Syntropy dialectical engine.",
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
            "Optional Small World handle(s) such as '@law:civil-code-obligations', '@law:eu-gdpr-data-protection', or '@finance:basel-iii-aml-compliance'.",
        },
        initial_axioms: {
          type: "array",
          items: { type: "string" },
          description:
            "Optional list of sanitized ground-truth axioms that strictly override model priors.",
        },
        custom_connectors: {
          type: "array",
          items: { type: "object" },
          description:
            "Optional list of inline Custom Epistemic Connectors ({name, connector_type, endpoint_url, static_rows}).",
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
            "Optional domain filter (e.g. 'law', 'medicine', 'physics', 'finance', 'cybersecurity').",
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
            "Small World handle (e.g. '@law:civil-code-obligations') or UUID.",
        },
      },
      required: ["world_id_or_handle"],
    },
  },
  {
    name: "syntropy_fork_world",
    description:
      "Fork an existing Small World (@domain:tag) into a private company workspace.",
    inputSchema: {
      type: "object",
      properties: {
        world_id_or_handle: {
          type: "string",
          description: "Source Small World handle or UUID.",
        },
        title: { type: "string" },
        description: { type: "string" },
      },
      required: ["world_id_or_handle"],
    },
  },
  {
    name: "syntropy_ingest_axioms",
    description:
      "Compile raw text or structured JSON/SQL payload into formal atomic axioms inside a Small World via Axiomat.",
    inputSchema: {
      type: "object",
      properties: {
        world_id_or_handle: {
          type: "string",
          description: "Target Small World handle or UUID.",
        },
        text: { type: "string" },
        payload: { type: "object" },
        source_reference: { type: "string" },
      },
      required: ["world_id_or_handle"],
    },
  },
  {
    name: "syntropy_register_connector",
    description:
      "Register a Custom Epistemic Connector (live REST API webhook, SQL/JSON table snapshot, data-retrieval sub-agent endpoint, or MCP tool bridge) on a Small World (@domain:tag).",
    inputSchema: {
      type: "object",
      properties: {
        world_id_or_handle: {
          type: "string",
          description: "Target Small World handle or UUID.",
        },
        name: {
          type: "string",
          description: "Human-readable connector name.",
        },
        connector_type: {
          type: "string",
          default: "rest_webhook",
          description:
            "Connector type: 'rest_webhook', 'rest_api', 'sql_table_snapshot', 'sql_postgrest', 'agent_endpoint', 'agent_webhook', 'mcp_tool', or 'graphql'.",
        },
        endpoint_url: {
          type: "string",
          description: "Public HTTPS endpoint URL for live retrieval.",
        },
        response_axioms_path: {
          type: "string",
          description: "Optional dot-path into the JSON response.",
        },
        row_template: {
          type: "string",
          description: "Optional Python/format template for dict rows.",
        },
        static_rows: {
          type: "array",
          items: {},
          description: "Optional inline SQL/JSON table rows.",
        },
      },
      required: ["world_id_or_handle", "name"],
    },
  },
  {
    name: "syntropy_list_connectors",
    description:
      "List all registered Custom Epistemic Connectors attached to a Small World (with secret headers redacted).",
    inputSchema: {
      type: "object",
      properties: {
        world_id_or_handle: {
          type: "string",
          description: "Small World handle or UUID.",
        },
      },
      required: ["world_id_or_handle"],
    },
  },
  {
    name: "syntropy_query_connector",
    description:
      "Execute a registered Custom Epistemic Connector on a Small World and return sanitized ground-truth facts.",
    inputSchema: {
      type: "object",
      properties: {
        world_id_or_handle: {
          type: "string",
          description: "Small World handle or UUID.",
        },
        connector_id: {
          type: "string",
          description: "Connector ID (e.g. 'conn_...').",
        },
        query: {
          type: "string",
          description: "Search query or entity identifier.",
        },
        ingest_into_world: {
          type: "boolean",
          default: false,
        },
      },
      required: ["world_id_or_handle", "connector_id"],
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
          version: "2.6.0",
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
          customConnectors: args.custom_connectors || args.connectors,
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
        out = await client.worlds.getAxioms(args.world_id_or_handle || args.world);
      } else if (name === "syntropy_fork_world") {
        out = await client.worlds.fork(
          args.world_id_or_handle || args.source_world || args.world,
          {
            title: args.title,
            description: args.description,
          }
        );
      } else if (name === "syntropy_ingest_axioms") {
        out = await client.worlds.ingest(
          args.world_id_or_handle || args.world,
          {
            text: args.text || args.raw_text,
            payload: args.payload,
            sourceReference: args.source_reference,
          }
        );
      } else if (name === "syntropy_register_connector") {
        out = await client.worlds.registerConnector(
          args.world_id_or_handle || args.world,
          {
            name: args.name,
            connectorType: args.connector_type || "rest_webhook",
            endpointUrl: args.endpoint_url,
            responseAxiomsPath: args.response_axioms_path,
            rowTemplate: args.row_template,
            staticRows: args.static_rows,
          }
        );
      } else if (name === "syntropy_list_connectors") {
        out = await client.worlds.listConnectors(args.world_id_or_handle || args.world);
      } else if (name === "syntropy_query_connector") {
        out = await client.worlds.queryConnector(
          args.world_id_or_handle || args.world,
          args.connector_id,
          {
            query: args.query || "",
            ingestIntoWorld: Boolean(args.ingest_into_world),
          }
        );
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

rl.on("line", async (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;
  try {
    const req = JSON.parse(trimmed);
    const resp = await handleRequest(req);
    if (resp) {
      process.stdout.write(JSON.stringify(resp) + "\n");
    }
  } catch (_err) {
    // ignore malformed json lines
  }
});
