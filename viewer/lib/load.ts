import type {
  AssetDTO,
  BindingDTO,
  BlueprintDTO,
  BuildReport,
  MetaGraph,
  ProjectionDTO,
  RelationDTO,
  StructDTO,
  TopologyEdge,
  TopologyGraph,
  TopologyNode,
  ViewerSnapshot,
  WorkflowComponent,
  WorkflowConnection,
  WorkflowPlan,
  WorkflowStep,
} from "./types";
import type {
  AuditSubject,
  Decision,
  DecisionStatus,
  EvidenceRef,
  ReviewSidecar,
} from "./reviewTypes";

type JsonObject = Record<string, unknown>;

function isObject(value: unknown): value is JsonObject {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function normalizeGraph(value: unknown): TopologyGraph {
  if (!isObject(value)) return { nodes: [], edges: [] };
  return {
    nodes: asArray<TopologyNode>(value.nodes),
    edges: asArray<TopologyEdge>(value.edges),
  };
}

function normalizeData(value: unknown): BlueprintDTO["data"] {
  if (!isObject(value)) return { structs: [], relations: [], projections: [] };
  return {
    structs: asArray<StructDTO>(value.structs),
    relations: asArray<RelationDTO>(value.relations),
    projections: asArray<ProjectionDTO>(value.projections),
  };
}

/** Accept either an array or an `{ items: [...] }`/`{ assets: [...] }` wrapper. */
function unwrapCollection<T>(
  value: unknown,
  keys: string[],
): T[] {
  if (Array.isArray(value)) return value as T[];
  if (!isObject(value)) return [];
  for (const key of keys) {
    if (Array.isArray(value[key])) return value[key] as T[];
  }
  return [];
}

export function normalizeBlueprint(value: unknown): BlueprintDTO {
  if (!isObject(value)) {
    return {
      graph: { nodes: [], edges: [] },
      data: { structs: [], relations: [], projections: [] },
      assets: [],
      bindings: [],
    };
  }
  return {
    graph: normalizeGraph(value.graph),
    data: normalizeData(value.data),
    assets: unwrapCollection<AssetDTO>(value.assets, ["assets", "items"]),
    bindings: unwrapCollection<BindingDTO>(value.bindings, ["bindings", "items"]),
  };
}

export function normalizeWorkflow(value: unknown): WorkflowPlan {
  if (!isObject(value)) {
    return { components: [], steps: [], connections: [], provenance: null };
  }
  return {
    components: asArray<WorkflowComponent>(value.components),
    steps: asArray<WorkflowStep>(value.steps),
    connections: asArray<WorkflowConnection>(value.connections),
    provenance: isObject(value.provenance) ? value.provenance : null,
  };
}

export function normalizeReport(value: unknown): BuildReport {
  if (!isObject(value)) {
    return {
      published_artifacts: [],
      recovered_failures: [],
      unresolved_failures: [],
      provenance: null,
    };
  }
  return {
    published_artifacts: asArray(value.published_artifacts),
    recovered_failures: asArray(value.recovered_failures),
    unresolved_failures: asArray(value.unresolved_failures),
    provenance: isObject(value.provenance) ? value.provenance : null,
  };
}

function normalizeMetaGraph(value: unknown): MetaGraph | undefined {
  if (!isObject(value)) return undefined;
  return {
    nodes: asArray(value.nodes),
    edges: asArray(value.edges),
    examples: isObject(value.examples) ? value.examples : undefined,
    summary: isObject(value.summary) ? value.summary : undefined,
    generated_by: isObject(value.generated_by) ? value.generated_by : undefined,
  };
}

function asStringArray(value: unknown): string[] {
  return asArray<unknown>(value).filter(
    (entry): entry is string => typeof entry === "string",
  );
}

function oneOf<T extends string>(
  value: unknown,
  allowed: readonly T[],
  fallback: T,
): T {
  return typeof value === "string" && (allowed as readonly string[]).includes(value)
    ? (value as T)
    : fallback;
}

const EVIDENCE_ARTIFACTS = [
  "blueprint",
  "workflow",
  "report",
  "metaGraph",
] as const;

const AUDIT_SUBJECT_KINDS = [
  "property",
  "node",
  "edge",
  "binding",
  "step",
  "asset",
  "relation",
  "projection",
] as const;

const DECISION_STATUSES = [
  "proposed",
  "accepted",
  "rejected",
  "open",
] as const;

const ENTITY_KINDS = ["node", "edge"] as const;

function normalizeEvidenceRef(value: unknown): EvidenceRef | undefined {
  if (!isObject(value)) return undefined;
  const jsonPointer = asString(value.jsonPointer);
  const label = asString(value.label, jsonPointer);
  const ref = asStringArray(value.ref);
  return {
    label,
    artifact: oneOf(value.artifact, EVIDENCE_ARTIFACTS, "blueprint"),
    jsonPointer,
    ...(ref.length ? { ref } : {}),
  };
}

function normalizeAuditSubject(value: unknown): AuditSubject | undefined {
  if (!isObject(value)) return undefined;
  const kind = oneOf(value.kind, AUDIT_SUBJECT_KINDS, "property");
  const name = asString(value.name);
  if (!name) return undefined;
  const stepId =
    Array.isArray(value.stepId) &&
    value.stepId.length >= 2 &&
    typeof value.stepId[0] === "string" &&
    typeof value.stepId[1] === "string"
      ? ([value.stepId[0], value.stepId[1]] as [string, string])
      : undefined;
  return {
    kind,
    name,
    ...(typeof value.component === "string" ? { component: value.component } : {}),
    ...(typeof value.property === "string" ? { property: value.property } : {}),
    ...(value.entityKind === "node" || value.entityKind === "edge"
      ? { entityKind: oneOf(value.entityKind, ENTITY_KINDS, "node") }
      : {}),
    ...(typeof value.bindingIndex === "number" &&
    Number.isFinite(value.bindingIndex)
      ? { bindingIndex: value.bindingIndex }
      : {}),
    ...(stepId ? { stepId } : {}),
  };
}

function normalizeDecision(value: unknown): Decision | undefined {
  if (!isObject(value)) return undefined;
  const id = asString(value.id);
  if (!id) return undefined;
  const status: DecisionStatus = oneOf(value.status, DECISION_STATUSES, "open");
  const subject = normalizeAuditSubject(value.subject);
  return {
    id,
    title: asString(value.title, id),
    status,
    rationale: asString(value.rationale),
    evidence: asArray<unknown>(value.evidence)
      .map(normalizeEvidenceRef)
      .filter((entry): entry is EvidenceRef => Boolean(entry)),
    ...(subject ? { subject } : {}),
    ...(Array.isArray(value.tags) ? { tags: asStringArray(value.tags) } : {}),
  };
}

/**
 * Validate and normalise a review sidecar.
 *
 * A sidecar is optional and purely descriptive. Anything that does not match
 * the documented shape is dropped rather than allowed to fail a snapshot load.
 */
export function normalizeReviewSidecar(value: unknown): ReviewSidecar | undefined {
  if (!isObject(value) || value.format !== "kg-viewer-review") return undefined;
  const decisions = asArray<unknown>(value.decisions)
    .map(normalizeDecision)
    .filter((entry): entry is Decision => Boolean(entry));

  const ai = isObject(value.ai)
    ? {
        ...(typeof value.ai.model === "string" ? { model: value.ai.model } : {}),
        ...(typeof value.ai.runId === "string" ? { runId: value.ai.runId } : {}),
        ...(typeof value.ai.generatedAt === "string"
          ? { generatedAt: value.ai.generatedAt }
          : {}),
        ...(typeof value.ai.note === "string" ? { note: value.ai.note } : {}),
      }
    : undefined;

  const notes = asArray<unknown>(value.notes)
    .filter(isObject)
    .map((note) => {
      const subject = normalizeAuditSubject(note.subject);
      return {
        id: asString(note.id, asString(note.text)),
        text: asString(note.text),
        ...(typeof note.author === "string" ? { author: note.author } : {}),
        ...(typeof note.createdAt === "string" ? { createdAt: note.createdAt } : {}),
        ...(subject ? { subject } : {}),
      };
    })
    .filter((note) => note.id && note.text);

  return {
    format: "kg-viewer-review",
    version: 1,
    ...(ai ? { ai } : {}),
    decisions,
    ...(notes.length ? { notes } : {}),
  };
}

/**
 * Load a snapshot, a blueprint object, or a workflow plan object.
 *
 * The viewer is artifact-driven: a partial artifact is valid and simply yields
 * empty indexes for the missing side. This keeps dropped files useful without
 * inventing data.
 */
export function loadSnapshotFromObject(value: unknown): ViewerSnapshot {
  if (!isObject(value)) {
    throw new Error("Expected a JSON object");
  }

  if (value.format === "kg-viewer-snapshot" || (value.blueprint && value.workflow)) {
    const review = normalizeReviewSidecar(value.review);
    return {
      format: "kg-viewer-snapshot",
      version: asNumber(value.version, 1),
      name: asString(value.name, "snapshot"),
      title: asString(value.title, asString(value.name, "Untitled snapshot")),
      blueprint: normalizeBlueprint(value.blueprint),
      workflow: normalizeWorkflow(value.workflow),
      report: normalizeReport(value.report),
      metaGraph: normalizeMetaGraph(value.metaGraph),
      ...(review ? { review } : {}),
    };
  }

  const workflowShape =
    Array.isArray(value.steps) ||
    Array.isArray(value.connections) ||
    Array.isArray(value.components);
  if (workflowShape) {
    return {
      format: "kg-viewer-snapshot",
      version: 1,
      name: asString(value.name, "workflow"),
      title: asString(value.title, "Workflow plan"),
      blueprint: normalizeBlueprint(undefined),
      workflow: normalizeWorkflow(value),
      report: normalizeReport(undefined),
    };
  }

  const blueprintShape =
    isObject(value.graph) ||
    isObject(value.data) ||
    Array.isArray(value.bindings) ||
    Array.isArray(value.assets);
  if (blueprintShape) {
    return {
      format: "kg-viewer-snapshot",
      version: 1,
      name: asString(value.name, "blueprint"),
      title: asString(value.title, "Blueprint"),
      blueprint: normalizeBlueprint(value),
      workflow: normalizeWorkflow(undefined),
      report: normalizeReport(undefined),
    };
  }

  throw new Error(
    "Unrecognised artifact: expected a kg-viewer-snapshot, a blueprint with graph/data, or a workflow plan with steps/connections",
  );
}

export function loadSnapshotFromText(text: string): ViewerSnapshot {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    throw new Error(`Invalid JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
  return loadSnapshotFromObject(parsed);
}

export async function loadSnapshotFromFile(file: File): Promise<ViewerSnapshot> {
  return loadSnapshotFromText(await file.text());
}

const DEFAULT_FETCH_TIMEOUT_MS = 20_000;

async function fetchJson(url: string, timeoutMs: number): Promise<unknown> {
  if (typeof fetch !== "function") {
    throw new Error("This browser does not provide fetch");
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`.trim());
    }
    return await response.json();
  } catch (error) {
    if (
      error instanceof DOMException &&
      (error.name === "AbortError" || error.name === "TimeoutError")
    ) {
      throw new Error(`request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

const SNAPSHOT_TIMEOUT_MS = 45_000;

async function fetchGzipJson(url: string, timeoutMs: number): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`.trim());
    }
    const buffer = await response.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    if (bytes.length >= 2 && bytes[0] === 0x1f && bytes[1] === 0x8b) {
      if (typeof DecompressionStream !== "function") {
        throw new Error("this browser cannot decompress gzip");
      }
      const stream = new Blob([buffer])
        .stream()
        .pipeThrough(new DecompressionStream("gzip"));
      return JSON.parse(await new Response(stream).text());
    }
    return JSON.parse(new TextDecoder().decode(buffer));
  } catch (error) {
    if (
      error instanceof DOMException &&
      (error.name === "AbortError" || error.name === "TimeoutError")
    ) {
      throw new Error(`request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Load the default Open Targets snapshot.
 *
 * `/api/snapshot` serves committed gzip bytes (`application/gzip`); the client
 * decompresses them, so the transfer is roughly 450 KB. The plain public JSON
 * is a fallback for static hosting. A base URL selects the plain file directly.
 */
export async function loadDefaultSnapshot(baseUrl = ""): Promise<ViewerSnapshot> {
  const prefix = baseUrl && !baseUrl.endsWith("/") ? `${baseUrl}/` : baseUrl;
  const failures: string[] = [];

  if (!baseUrl) {
    try {
      return loadSnapshotFromObject(
        await fetchGzipJson("/api/snapshot", SNAPSHOT_TIMEOUT_MS),
      );
    } catch (error) {
      failures.push(
        `/api/snapshot: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  const endpoints = baseUrl
    ? [`${prefix}data/opentargets.snapshot.json`]
    : ["/data/opentargets.snapshot.json"];
  for (const url of endpoints) {
    try {
      return loadSnapshotFromObject(await fetchJson(url, SNAPSHOT_TIMEOUT_MS));
    } catch (error) {
      failures.push(
        `${url}: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }
  throw new Error(
    `Could not load the Open Targets snapshot. ${failures.join("; ")}. ` +
      "The default data is served from /api/snapshot (gzip) or the plain public JSON. " +
      "A remote proxy can block either path; use Import to open a snapshot file directly.",
  );
}

/** Load the bundled reference-estate snapshot for comparison and tests. */
export async function loadReferenceSnapshot(
  baseUrl = "",
): Promise<ViewerSnapshot> {
  const prefix = baseUrl && !baseUrl.endsWith("/") ? `${baseUrl}/` : baseUrl;
  return loadSnapshotFromObject(
    await fetchJson(
      `${prefix}data/reference.snapshot.json`,
      SNAPSHOT_TIMEOUT_MS,
    ),
  );
}

/** Load the reference review sidecar. */
export async function loadReferenceReview(
  baseUrl = "",
): Promise<ReviewSidecar | undefined> {
  const prefix = baseUrl && !baseUrl.endsWith("/") ? `${baseUrl}/` : baseUrl;
  try {
    return normalizeReviewSidecar(
      await fetchJson(
        `${prefix}data/reference.review.json`,
        DEFAULT_FETCH_TIMEOUT_MS,
      ),
    );
  } catch {
    return undefined;
  }
}

/**
 * Load the optional Open Targets review sidecar.
 *
 * A missing, malformed or unavailable sidecar is not a snapshot failure: the
 * viewer simply derives its ledger without one.
 */
export async function loadReviewSidecar(
  baseUrl = "",
): Promise<ReviewSidecar | undefined> {
  const prefix = baseUrl && !baseUrl.endsWith("/") ? `${baseUrl}/` : baseUrl;
  const endpoints = baseUrl
    ? [`${prefix}data/opentargets.review.json`]
    : ["/api/review", "/data/opentargets.review.json"];
  for (const url of endpoints) {
    try {
      const loaded = normalizeReviewSidecar(
        await fetchJson(url, DEFAULT_FETCH_TIMEOUT_MS),
      );
      if (loaded) return loaded;
    } catch {
      // Try the next endpoint; a missing sidecar is allowed.
    }
  }
  return undefined;
}
