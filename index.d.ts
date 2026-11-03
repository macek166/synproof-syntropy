export interface SyntropyClientOptions {
  apiKey?: string;
  llmApiKey?: string;
  baseUrl?: string;
  modelName?: string;
}

export interface DebateParams {
  thesis: string;
  world?: string;
  initialAxioms?: string[];
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
  };
  constructor(options?: SyntropyClientOptions);
  debate(params: DebateParams): Promise<DebateVerdict>;
}
