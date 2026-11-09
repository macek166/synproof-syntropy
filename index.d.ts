export interface SyntropyClientOptions {
  apiKey?: string;
  llmApiKey?: string;
  baseUrl?: string;
  modelName?: string;
}

export interface CustomConnectorConfig {
  id?: string;
  name: string;
  connector_type?:
    | "rest_webhook"
    | "rest_api"
    | "sql_table_snapshot"
    | "sql_postgrest"
    | "agent_endpoint"
    | "agent_webhook"
    | "mcp_tool"
    | "graphql";
  endpoint_url?: string;
  method?: "POST" | "GET";
  headers?: Record<string, string>;
  description?: string;
  timeout_ms?: number;
  response_axioms_path?: string;
  row_template?: string;
  static_rows?: Array<string | Record<string, unknown>>;
  enabled?: boolean;
}

export interface DebateParams {
  thesis: string;
  world?: string;
  initialAxioms?: string[];
  axiomProvider?: (thesis: string) => Promise<string[] | Record<string, unknown>> | string[] | Record<string, unknown>;
  customConnectors?: CustomConnectorConfig[];
  connectors?: CustomConnectorConfig[];
  maxFailures?: number;
  modelName?: string;
  enableResearch?: boolean;
  wait?: boolean;
  pollIntervalMs?: number;
  maxWaitMs?: number;
}

export interface DebateVerdict {
  jobId: string;
  thesis: string;
  status: "CONFIRMED" | "REFUTED" | "UNKNOWN" | string;
  winningThesis: string | null;
  refutingArgument: string | null;
  stoppingReason: string | null;
  totalIterations: number;
  telemetry: Record<string, unknown>;
  verdictReport: Record<string, unknown>;
  raw: Record<string, unknown>;
}

export declare class SyntropyClient {
  apiKey: string;
  llmApiKey: string;
  baseUrl: string;
  modelName: string;
  worlds: {
    list(params?: { domain?: string; search?: string }): Promise<Record<string, unknown>>;
    getAxioms(worldIdOrHandle: string): Promise<Record<string, unknown>>;
    fork(
      worldIdOrHandle: string,
      options?: { title?: string; description?: string; isPublic?: boolean }
    ): Promise<Record<string, unknown>>;
    ingest(
      worldIdOrHandle: string,
      options?: {
        text?: string;
        payload?: Record<string, unknown>;
        sourceReference?: string;
        onConflict?: "flag" | "replace" | "keep";
      }
    ): Promise<Record<string, unknown>>;
    registerConnector(
      worldIdOrHandle: string,
      options: {
        name: string;
        connectorType?: "rest_webhook" | "sql_table_snapshot" | "agent_endpoint" | "mcp_tool";
        endpointUrl?: string;
        method?: "POST" | "GET";
        headers?: Record<string, string>;
        description?: string;
        timeoutMs?: number;
        responseAxiomsPath?: string;
        staticRows?: Array<string | Record<string, unknown>>;
        enabled?: boolean;
      }
    ): Promise<Record<string, unknown>>;
    listConnectors(worldIdOrHandle: string): Promise<Record<string, unknown>>;
    deleteConnector(worldIdOrHandle: string, connectorId: string): Promise<Record<string, unknown>>;
    queryConnector(
      worldIdOrHandle: string,
      connectorId: string,
      options?: { query?: string; thesis?: string; ingestIntoWorld?: boolean; onConflict?: string }
    ): Promise<Record<string, unknown>>;
  };
  constructor(options?: SyntropyClientOptions);
  debate(params: DebateParams): Promise<DebateVerdict>;
}
