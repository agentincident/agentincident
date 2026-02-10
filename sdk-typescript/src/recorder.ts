import { computeHash } from "./hash.js";
import type {
  Constraint,
  Classification,
  Environment,
  FaultClass,
  ImpactScore,
  Incident,
  Liability,
  LossEstimate,
  Meta,
  Response,
  TraceEntry,
} from "./types.js";

export interface RecorderOptions {
  agent?: string;
  framework?: string;
  environment?: Environment;
  trigger?: string;
}

export class Recorder {
  private _entries: TraceEntry[] = [];
  private _seq = 0;
  private _incident: Incident | null = null;
  private _options: RecorderOptions;

  constructor(options?: RecorderOptions) {
    this._options = options ?? {};
  }

  record(
    tool: string,
    input: Record<string, unknown>,
    output: Record<string, unknown>,
    options?: {
      irreversible?: boolean;
      agent_reasoning?: string;
      duration_ms?: number;
    }
  ): TraceEntry {
    this._seq += 1;
    const entry: TraceEntry = {
      seq: this._seq,
      tool,
      input,
      output,
      ts: new Date().toISOString(),
      hash: computeHash(input, output),
    };
    if (options?.duration_ms !== undefined) {
      entry.duration_ms = options.duration_ms;
    }
    if (options?.irreversible !== undefined) {
      entry.irreversible = options.irreversible;
    }
    if (options?.agent_reasoning !== undefined) {
      entry.agent_reasoning = options.agent_reasoning;
    }
    this._entries.push(entry);
    return entry;
  }

  wrap<TArgs extends unknown[], TResult>(
    tool: string,
    fn: (...args: TArgs) => TResult | Promise<TResult>,
    options?: { irreversible?: boolean }
  ): (...args: TArgs) => Promise<TResult> {
    return async (...args: TArgs): Promise<TResult> => {
      const inputObj: Record<string, unknown> = { args };
      const start = Date.now();
      const result = await fn(...args);
      const duration_ms = Date.now() - start;
      const outputObj: Record<string, unknown> = { result };
      this.record(tool, inputObj, outputObj, {
        duration_ms,
        irreversible: options?.irreversible,
      });
      return result;
    };
  }

  toIncident(params: {
    fault_class: FaultClass;
    impact_score: ImpactScore;
    loss_amount_usd: number | null;
    constraints: Constraint[];
    meta?: Meta;
    classification?: Classification;
    liability?: Liability;
    loss_estimate?: LossEstimate;
    response?: Response;
  }): Incident {
    const meta: Meta = {
      schema: "agentincident/v0.1",
      created_at: new Date().toISOString(),
      ...this._options,
      ...params.meta,
    };

    const incident: Incident = {
      trace: [...this._entries],
      constraints: params.constraints,
      fault_class: params.fault_class,
      impact_score: params.impact_score,
      loss_amount_usd: params.loss_amount_usd,
      meta,
    };

    if (params.classification) incident.classification = params.classification;
    if (params.liability) incident.liability = params.liability;
    if (params.loss_estimate) incident.loss_estimate = params.loss_estimate;
    if (params.response) incident.response = params.response;

    this._incident = incident;
    return incident;
  }

  toJSON(indent?: number): string {
    if (!this._incident) {
      throw new Error(
        "No incident created yet. Call toIncident() first."
      );
    }
    return JSON.stringify(this._incident, null, indent);
  }

  validate(level: "core" | "standard" | "full" = "core"): string[] {
    const errors: string[] = [];

    if (this._entries.length === 0) {
      errors.push("trace must contain at least one entry");
    }

    if (!this._incident) {
      errors.push("No incident created yet. Call toIncident() first.");
      return errors;
    }

    const inc = this._incident;

    if (!inc.fault_class) errors.push("fault_class is required");
    if (!inc.impact_score) errors.push("impact_score is required");
    if (inc.loss_amount_usd === undefined) {
      errors.push("loss_amount_usd is required (can be null)");
    }
    if (!inc.constraints || inc.constraints.length === 0) {
      errors.push("constraints must contain at least one entry");
    }

    if (level === "standard" || level === "full") {
      if (!inc.meta) errors.push("meta is required for standard level");
      if (!inc.classification)
        errors.push("classification is required for standard level");
      if (!inc.loss_estimate)
        errors.push("loss_estimate is required for standard level");
    }

    if (level === "full") {
      if (!inc.liability)
        errors.push("liability is required for full level");
      if (!inc.response)
        errors.push("response is required for full level");
      if (inc.response) {
        if (!inc.response.actions)
          errors.push("response.actions is required for full level");
        if (!inc.response.constraint_update)
          errors.push(
            "response.constraint_update is required for full level"
          );
        if (!inc.response.verification)
          errors.push("response.verification is required for full level");
      }
    }

    return errors;
  }

  get entries(): ReadonlyArray<TraceEntry> {
    return this._entries;
  }
}
