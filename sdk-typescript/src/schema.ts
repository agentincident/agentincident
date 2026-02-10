import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Incident } from "./types.js";

const require = createRequire(import.meta.url);

let _cachedSchema: Record<string, unknown> | null = null;

export function getSchema(): Record<string, unknown> {
  if (_cachedSchema) return _cachedSchema;
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const schemaPath = join(__dirname, "..", "src", "schema", "v0.1.json");
  let raw: string;
  try {
    raw = readFileSync(schemaPath, "utf-8");
  } catch {
    const distPath = join(__dirname, "schema", "v0.1.json");
    try {
      raw = readFileSync(distPath, "utf-8");
    } catch {
      const projectPath = join(__dirname, "..", "src", "schema", "v0.1.json");
      raw = readFileSync(projectPath, "utf-8");
    }
  }
  _cachedSchema = JSON.parse(raw) as Record<string, unknown>;
  return _cachedSchema;
}

export function validate(
  data: Record<string, unknown> | Incident,
  level: "core" | "standard" | "full" = "core"
): string[] {
  let Ajv: unknown;
  let addFormats: unknown;

  try {
    // Use ajv/dist/2020 for JSON Schema 2020-12 support
    let ajvModule;
    try {
      ajvModule = require("ajv/dist/2020");
    } catch {
      ajvModule = require("ajv");
    }
    Ajv = ajvModule.default || ajvModule;
    try {
      const formatsModule = require("ajv-formats");
      addFormats = formatsModule.default || formatsModule;
    } catch {
      // ajv-formats not available
    }
  } catch {
    return [
      "ajv is not installed. Install ajv for schema validation: npm install ajv ajv-formats",
    ];
  }

  const schema = getSchema();

  const schemaId = (schema as Record<string, unknown>).$id as string;
  const refMap: Record<string, string> = {
    core: `${schemaId}#/$defs/CoreRecord`,
    standard: `${schemaId}#/$defs/StandardRecord`,
    full: `${schemaId}#/$defs/FullRecord`,
  };

  const ajv = new (Ajv as new (opts: Record<string, unknown>) => {
    compile: (s: unknown) => {
      (data: unknown): boolean;
      errors?: Array<{ instancePath: string; message?: string }> | null;
    };
    addSchema: (s: unknown) => void;
  })({ allErrors: true, strict: false });

  if (typeof addFormats === "function") {
    (addFormats as (a: unknown) => void)(ajv);
  }

  ajv.addSchema(schema);
  const validateFn = ajv.compile({ $ref: refMap[level] });
  const valid = validateFn(data);

  if (valid) return [];

  return (validateFn.errors ?? []).map(
    (e) => `${e.instancePath} ${e.message ?? "unknown error"}`
  );
}
