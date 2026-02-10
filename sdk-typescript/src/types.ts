export type FaultClass =
  | "AGENT_ERROR"
  | "SPEC_AMBIGUITY"
  | "TOOL_FAILURE"
  | "ADVERSARIAL_INPUT"
  | "USER_FAULT"
  | "UNKNOWN";

export type ImpactScore = 1 | 2 | 3 | 4 | 5;

export type EvalResult = "pass" | "fail";

export type IncidentType = "INCIDENT" | "NEAR_MISS";

export type Environment = "production" | "staging" | "development" | "sandbox";

export type ClassifierType = "rules" | "llm" | "hybrid" | "human";

export type ClassificationStatus =
  | "draft"
  | "human_confirmed"
  | "disputed"
  | "revised";

export type ActionStatus = "done" | "in_progress" | "planned";

export type VerificationResult = "pass" | "fail" | "pending";

export type LossConfidence = "low" | "medium" | "high";

export interface TraceEntry {
  seq: number;
  tool: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  ts: string;
  hash: string;
  duration_ms?: number;
  irreversible?: boolean;
  agent_reasoning?: string;
}

export interface Constraint {
  policy: string;
  version?: string;
  eval_result: EvalResult;
  breach_delta?: number;
  gaps_identified?: string[];
}

export interface Meta {
  schema?: string;
  incident_id?: string;
  incident_type?: IncidentType;
  created_at?: string;
  updated_at?: string;
  agent?: string;
  framework?: string;
  environment?: Environment;
  trigger?: string;
}

export interface Classification {
  fault_class?: FaultClass;
  fault_subclass?: string;
  fault_vector?: string;
  confidence?: number;
  classifier?: ClassifierType;
  status?: ClassificationStatus;
  reviewed_by?: string;
  reviewed_at?: string;
  evidence?: string[];
  counterfactuals?: string[];
  review_notes?: string;
  revision_history?: Record<string, unknown>[];
}

export interface Liability {
  primary: string;
  contributing?: string[];
  policy_owner?: string;
}

export interface LossEstimate {
  total_usd: number;
  confidence?: LossConfidence;
  breakdown?: Record<string, number | null>;
}

export interface ResponseAction {
  description: string;
  status: ActionStatus;
  owner?: string;
  completed_at?: string | null;
}

export interface Verification {
  test: string;
  method: string;
  result: VerificationResult;
}

export interface ConstraintUpdate {
  from: string;
  to: string;
  diff?: Record<string, unknown>;
  deployed_at?: string | null;
}

export interface Response {
  actions?: ResponseAction[];
  constraint_update?: ConstraintUpdate;
  verification?: Verification[];
  time_to_detect_sec?: number;
  time_to_contain_sec?: number;
  time_to_remediate_sec?: number;
}

export interface Incident {
  trace: TraceEntry[];
  constraints: Constraint[];
  fault_class: FaultClass;
  impact_score: ImpactScore;
  loss_amount_usd: number | null;
  meta?: Meta;
  classification?: Classification;
  liability?: Liability;
  loss_estimate?: LossEstimate;
  response?: Response;
}
