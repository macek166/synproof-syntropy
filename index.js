"use strict";

/**
 * Official Node.js / TypeScript SDK for Synproof's Syntropy (https://synproof.ai)
 * Production Control Plane API: https://api.synproof.ai
 */

const INJECTION_RE =
  /(ignore\s+(all\s+)?(previous|prior|above)\s+instructions|system\s*prompt\s*:|<\s*\/?\s*(system|instruction|tool_call|function_call)\s*>)/gi;

function sanitizeUntrustedText(raw, maxLength = 8000) {
  const str = String(raw || "")
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "")
    .replace(INJECTION_RE, "[REDACTED_DIRECTIVE]");
  return str.trim().slice(0, maxLength);
}

class SyntropyClient {
  /**
   * @param {Object} [options]
   * @param {string} [options.apiKey] - SYNTROPY_API_KEY
   * @param {string} [options.baseUrl] - Defaults to https://api.synproof.ai
   * @param {string} [options.modelName] - Defaults to gemini-2.5-flash
   */
  constructor(options = {}) {
    this.apiKey = options.apiKey || process.env.SYNTROPY_API_KEY || "";
    this.baseUrl = (
      options.baseUrl ||
      process.env.SYNTROPY_BASE_URL ||
      "https://api.synproof.ai"
    ).replace(/\/+$/, "");
    this.modelName = options.modelName || "gemini-2.5-flash";

    this.worlds = {
      list: (params = {}) => {
        const qs = new URLSearchParams();
        if (params.domain) qs.set("domain", params.domain);
        if (params.search) qs.set("search", params.search);
        const query = qs.toString() ? `?${qs.toString()}` : "";
        return this._request("GET", `/v1/worlds${query}`);
      },
      getAxioms: (worldIdOrHandle) =>
        this._request(
          "GET",
          `/v1/worlds/${encodeURIComponent(worldIdOrHandle)}/axioms`
        ),
      fork: (worldIdOrHandle, { title, description, isPublic = false } = {}) =>
        this._request(
          "POST",
          `/v1/worlds/${encodeURIComponent(worldIdOrHandle)}/fork`,
          { title, description, is_public: isPublic }
        ),
      ingest: (
        worldIdOrHandle,
        { text, payload, sourceReference, onConflict = "flag" } = {}
      ) =>
        this._request(
          "POST",
          `/v1/worlds/${encodeURIComponent(worldIdOrHandle)}/ingest`,
          {
            raw_text: text,
            payload,
            source_reference: sourceReference,
            on_conflict: onConflict,
          }
        ),
      registerConnector: (
        worldIdOrHandle,
        {
          name,
          connectorType = "rest_webhook",
          endpointUrl,
          method = "POST",
          headers = {},
          description,
          timeoutMs = 4000,
          responseAxiomsPath,
          rowTemplate,
          staticRows,
          enabled = true,
        } = {}
      ) =>
        this._request(
          "POST",
          `/v1/worlds/${encodeURIComponent(worldIdOrHandle)}/connectors`,
          {
            name,
            connector_type: connectorType,
            endpoint_url: endpointUrl,
            method,
            headers,
            description,
            timeout_ms: timeoutMs,
            response_axioms_path: responseAxiomsPath,
            row_template: rowTemplate,
            static_rows: staticRows,
            enabled,
          }
        ),
      listConnectors: (worldIdOrHandle) =>
        this._request(
          "GET",
          `/v1/worlds/${encodeURIComponent(worldIdOrHandle)}/connectors`
        ),
      deleteConnector: (worldIdOrHandle, connectorId) =>
        this._request(
          "DELETE",
          `/v1/worlds/${encodeURIComponent(worldIdOrHandle)}/connectors/${encodeURIComponent(connectorId)}`
        ),
      queryConnector: (
        worldIdOrHandle,
        connectorId,
        { query = "", thesis, ingestIntoWorld = false, onConflict = "flag" } = {}
      ) =>
        this._request(
          "POST",
          `/v1/worlds/${encodeURIComponent(worldIdOrHandle)}/connectors/${encodeURIComponent(connectorId)}/query`,
          {
            query,
            thesis,
            ingest_into_world: ingestIntoWorld,
            on_conflict: onConflict,
          }
        ),
    };
  }

  _headers(extra = {}) {
    const headers = {
      "User-Agent": "Syntropy-Node-SDK/2.5.0 (+https://synproof.ai)",
      ...extra,
    };
    if (this.apiKey) {
      headers["X-API-Key"] = this.apiKey;
      headers["X-Syntropy-API-Key"] = this.apiKey;
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  async _request(method, path, body) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: this._headers(
        body !== undefined ? { "Content-Type": "application/json" } : {}
      ),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Syntropy API error (${res.status}): ${text}`);
    }
    return res.json();
  }

  /**
   * Run a formal 5-sieve dialectical verification debate.
   */
  async debate({
    thesis,
    world,
    initialAxioms = [],
    axiomProvider,
    customConnectors,
    connectors,
    maxFailures = 3,
    modelName,
    enableResearch = true,
    wait = true,
    pollIntervalMs = 500,
    maxWaitMs = 180000,
  }) {
    const effectiveModel = modelName || this.modelName;
    const llmProvider =
      effectiveModel.includes("/") &&
      !effectiveModel.toLowerCase().startsWith("models/gemini")
        ? "openrouter"
        : "gemini";

    const safeThesis = sanitizeUntrustedText(thesis);
    const safeAxioms = (initialAxioms || []).map((a) => sanitizeUntrustedText(a));

    if (typeof axiomProvider === "function") {
      const resolved = await axiomProvider(safeThesis);
      const list = Array.isArray(resolved) ? resolved : [resolved];
      for (const item of list) {
        if (item) {
          const clean = sanitizeUntrustedText(
            typeof item === "object" ? JSON.stringify(item) : String(item)
          );
          if (clean && !safeAxioms.includes(clean)) {
            safeAxioms.push(clean);
          }
        }
      }
    }

    const payload = {
      thesis: safeThesis,
      world,
      initial_axioms: safeAxioms,
      max_failures: maxFailures,
      enable_research: enableResearch,
      model_name: effectiveModel,
      llm_provider: llmProvider,
    };

    const effectiveConns = customConnectors || connectors;
    if (Array.isArray(effectiveConns) && effectiveConns.length > 0) {
      payload.custom_connectors = effectiveConns;
    }

    const startRes = await this._request("POST", "/v1/debate", payload);

    if (!wait) return startRes;

    const jobId = startRes.job_id;
    const deadline = Date.now() + maxWaitMs;
    while (Date.now() < deadline) {
      const job = await this._request("GET", `/v1/debate/${jobId}`);
      if (job.status === "completed") {
        const r = job.result || job;
        return {
          jobId,
          thesis: safeThesis,
          status: r.original_thesis_status || "UNKNOWN",
          winningThesis: r.winning_thesis || null,
          refutingArgument: r.refuting_argument || null,
          stoppingReason: r.stopping_reason || null,
          totalIterations: r.total_iterations || r.total_steps || 0,
          telemetry: r.telemetry || {},
          verdictReport: r.verdict_report || {},
          raw: job,
        };
      }
      if (job.status === "failed") {
        throw new Error(`Syntropy debate job ${jobId} failed: ${job.error}`);
      }
      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }
    throw new Error(`Syntropy debate job ${jobId} timed out`);
  }
}

module.exports = { SyntropyClient, sanitizeUntrustedText };
