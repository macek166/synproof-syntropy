"use strict";

/**
 * Official Node.js / TypeScript SDK for Synproof's Syntropy (https://synproof.ai)
 * Production Control Plane API: https://api.synproof.ai
 */

class SyntropyClient {
  /**
   * @param {Object} [options]
   * @param {string} [options.apiKey] - SYNTROPY_API_KEY (or syn_mng_... / syn_byok_...)
   * @param {string} [options.llmApiKey] - OPENROUTER_API_KEY or GEMINI_API_KEY for zero-friction BYOK
   * @param {string} [options.baseUrl] - Defaults to https://api.synproof.ai
   * @param {string} [options.modelName] - Defaults to gemini-2.5-flash
   */
  constructor(options = {}) {
    this.apiKey = options.apiKey || process.env.SYNTROPY_API_KEY || "";
    this.llmApiKey =
      options.llmApiKey ||
      process.env.SYNTROPY_LLM_API_KEY ||
      process.env.OPENROUTER_API_KEY ||
      process.env.GEMINI_API_KEY ||
      process.env.GOOGLE_API_KEY ||
      "";
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
          {
            title,
            description,
            is_public: isPublic,
          }
        ),
      ingest: (
        worldIdOrHandle,
        { text, payload, sourceReference, onConflict = "flag" } = {}
      ) => {
        const form = new URLSearchParams();
        form.set("on_conflict", onConflict);
        if (sourceReference) form.set("source_reference", sourceReference);
        if (text) form.set("text", text);
        if (payload) form.set("payload_json", JSON.stringify(payload));
        return this._requestForm(
          "POST",
          `/v1/worlds/${encodeURIComponent(worldIdOrHandle)}/axiomat/ingest`,
          form
        );
      },
    };
  }

  _headers(extra = {}) {
    const headers = {
      "User-Agent": "Syntropy-Node-SDK/2.5.0 (+https://synproof.ai)",
      ...extra,
    };
    const key = this.apiKey || this.llmApiKey;
    if (key) {
      headers["X-API-Key"] = key;
      headers["X-Syntropy-API-Key"] = key;
      headers["Authorization"] = `Bearer ${key}`;
    }
    if (this.llmApiKey) {
      headers["X-LLM-API-Key"] = this.llmApiKey;
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

  async _requestForm(method, path, formParams) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: this._headers({
        "Content-Type": "application/x-www-form-urlencoded",
      }),
      body: formParams.toString(),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Syntropy API error (${res.status}): ${text}`);
    }
    return res.json();
  }

  /**
   * Run a formal 5-sieve dialectical verification debate.
   * @param {Object} params
   * @param {string} params.thesis
   * @param {string} [params.world]
   * @param {string[]} [params.initialAxioms]
   * @param {number} [params.maxFailures=3]
   * @param {string} [params.modelName]
   * @param {boolean} [params.enableResearch=true]
   * @param {boolean} [params.wait=true]
   */
  async debate({
    thesis,
    world,
    initialAxioms = [],
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

    const startRes = await this._request("POST", "/v1/debate", {
      thesis,
      world,
      initial_axioms: initialAxioms,
      max_failures: maxFailures,
      enable_research: enableResearch,
      model_name: effectiveModel,
      llm_provider: llmProvider,
    });

    if (!wait) return startRes;

    const jobId = startRes.job_id;
    const deadline = Date.now() + maxWaitMs;
    while (Date.now() < deadline) {
      const job = await this._request("GET", `/v1/debate/${jobId}`);
      if (job.status === "completed") {
        const r = job.result || job;
        return {
          jobId,
          thesis,
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

module.exports = { SyntropyClient };
