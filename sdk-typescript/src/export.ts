import type { Incident } from "./types.js";

export function incidentToJSON(incident: Incident, indent?: number): string {
  return JSON.stringify(incident, null, indent);
}

export function incidentFromJSON(json: string): Incident {
  return JSON.parse(json) as Incident;
}

export function incidentToDict(
  incident: Incident
): Record<string, unknown> {
  return JSON.parse(JSON.stringify(incident)) as Record<string, unknown>;
}

export function incidentFromDict(
  data: Record<string, unknown>
): Incident {
  return data as unknown as Incident;
}
