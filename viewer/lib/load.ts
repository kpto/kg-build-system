import type {
  AssetDTO,
  AssetProfileDTO,
  BindingDTO,
  BlueprintDTO,
  BuildReport,
  DataField,
  GraphDeclarationDTO,
  GraphSemanticsDTO,
  MetaGraph,
  ProjectionDTO,
  PurposeDTO,
  RelationDTO,
  SemanticsDTO,
  SemanticsFrameDTO,
  SemanticText,
  StructDTO,
  TopologyEdge,
  TopologyGraph,
  TopologyNode,
  TopologyProperty,
  ViewerSnapshot,
  WorkflowComponent,
  WorkflowConnection,
  WorkflowPlan,
  WorkflowStep,
} from "./types";

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

// ---------------------------------------------------------------------------
// Semantics, graph declaration and asset profile
// ---------------------------------------------------------------------------

function normalizeSemanticText(value: unknown): SemanticText | undefined {
  if (!isObject(value) || typeof value.text !== "string") return undefined;
  return { ...value, text: value.text };
}

function normalizeSemanticTexts(value: unknown): SemanticText[] | undefined {
  if (!Array.isArray(value)) return undefined;
  return value
    .map(normalizeSemanticText)
    .filter((entry): entry is SemanticText => Boolean(entry));
}

function normalizeFrame(value: unknown): SemanticsFrameDTO | undefined {
  if (!isObject(value) || typeof value.text !== "string") return undefined;
  const limitations = normalizeSemanticTexts(value.limitations);
  return {
    ...value,
    text: value.text,
    ...(limitations ? { limitations } : {}),
  };
}

function normalizeFrames(value: unknown): SemanticsFrameDTO[] | undefined {
  if (!Array.isArray(value)) return undefined;
  return value
    .map(normalizeFrame)
    .filter((entry): entry is SemanticsFrameDTO => Boolean(entry));
}

/** Normalise attached semantics; unknown fields inside each unit survive. */
export function normalizeSemantics(value: unknown): SemanticsDTO | undefined {
  if (!isObject(value)) return undefined;
  const claims = normalizeSemanticTexts(value.claims);
  const frames = normalizeFrames(value.frames);
  return {
    ...value,
    ...(claims ? { claims } : {}),
    ...(frames ? { frames } : {}),
  };
}

function normalizePurpose(value: unknown): PurposeDTO | undefined {
  if (!isObject(value) || typeof value.text !== "string") return undefined;
  const frames = normalizeFrames(value.frames);
  return {
    ...value,
    text: value.text,
    ...(frames ? { frames } : {}),
  };
}

/** Normalise a graph declaration; a missing declaration is allowed. */
export function normalizeGraphDeclaration(
  value: unknown,
): GraphDeclarationDTO | undefined {
  if (!isObject(value) || !isObject(value.semantics)) return undefined;
  const raw = value.semantics;
  const claims = normalizeSemanticTexts(raw.claims);
  const semantics: GraphSemanticsDTO = {
    ...raw,
    ...(claims ? { claims } : {}),
    purpose: normalizePurpose(raw.purpose) ?? { text: "" },
  };
  return {
    ...value,
    name: asString(value.name),
    ...(typeof value.description === "string" || value.description === null
      ? { description: value.description }
      : {}),
    semantics,
  };
}

/** Normalise an asset profile; a missing profile is allowed. */
export function normalizeAssetProfile(value: unknown): AssetProfileDTO | undefined {
  if (!isObject(value)) return undefined;
  return {
    ...value,
    subject: asString(value.subject),
    coverage: asString(value.coverage),
    authority: asString(value.authority),
    basis: asString(value.basis),
    ...(typeof value.title === "string" || value.title === null
      ? { title: value.title }
      : {}),
    ...(typeof value.description === "string" || value.description === null
      ? { description: value.description }
      : {}),
  };
}

function withSemantics<T>(value: unknown): T {
  if (!isObject(value)) return value as T;
  const semantics = normalizeSemantics(value.semantics);
  return (semantics ? { ...value, semantics } : value) as T;
}

function normalizeField(value: unknown): DataField {
  return withSemantics<DataField>(value);
}

function normalizeColumns(value: unknown): DataField[] | undefined {
  return Array.isArray(value) ? value.map(normalizeField) : undefined;
}

function normalizeOwner<T>(value: unknown): T {
  if (!isObject(value)) return value as T;
  const columns = normalizeColumns(value.columns);
  const semantics = normalizeSemantics(value.semantics);
  return {
    ...value,
    ...(columns ? { columns } : {}),
    ...(semantics ? { semantics } : {}),
  } as T;
}

function normalizeTopologyProperty(value: unknown): TopologyProperty {
  return withSemantics<TopologyProperty>(value);
}

function normalizeTopologyComponent<T extends TopologyNode | TopologyEdge>(
  value: unknown,
): T {
  if (!isObject(value)) return value as T;
  const properties = Array.isArray(value.properties)
    ? value.properties.map(normalizeTopologyProperty)
    : undefined;
  const semantics = normalizeSemantics(value.semantics);
  return {
    ...value,
    ...(properties ? { properties } : {}),
    ...(semantics ? { semantics } : {}),
  } as T;
}

function normalizeAsset(value: unknown): AssetDTO {
  if (!isObject(value)) return value as AssetDTO;
  const profile = normalizeAssetProfile(value.profile);
  const semantics = normalizeSemantics(value.semantics);
  return {
    ...value,
    ...(profile ? { profile } : {}),
    ...(semantics ? { semantics } : {}),
  } as AssetDTO;
}

function normalizeBinding(value: unknown): BindingDTO {
  return withSemantics<BindingDTO>(value);
}

function normalizeGraph(value: unknown): TopologyGraph {
  if (!isObject(value)) return { nodes: [], edges: [] };
  return {
    ...value,
    nodes: asArray<unknown>(value.nodes).map((node) =>
      normalizeTopologyComponent<TopologyNode>(node),
    ),
    edges: asArray<unknown>(value.edges).map((edge) =>
      normalizeTopologyComponent<TopologyEdge>(edge),
    ),
  };
}

function normalizeData(value: unknown): BlueprintDTO["data"] {
  if (!isObject(value)) return { structs: [], relations: [], projections: [] };
  return {
    ...value,
    structs: asArray<unknown>(value.structs).map((struct) =>
      normalizeOwner<StructDTO>(struct),
    ),
    relations: asArray<unknown>(value.relations).map((relation) =>
      normalizeOwner<RelationDTO>(relation),
    ),
    projections: asArray<unknown>(value.projections).map((projection) =>
      normalizeOwner<ProjectionDTO>(projection),
    ),
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
    ...value,
    graph_declaration: normalizeGraphDeclaration(value.graph_declaration),
    graph: normalizeGraph(value.graph),
    data: normalizeData(value.data),
    assets: unwrapCollection<unknown>(value.assets, ["assets", "items"]).map(
      normalizeAsset,
    ),
    bindings: unwrapCollection<unknown>(value.bindings, ["bindings", "items"]).map(
      normalizeBinding,
    ),
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

function embeddedBlueprint(value: unknown): unknown {
  if (!isObject(value)) return undefined;
  const provenance = isObject(value.provenance) ? value.provenance : undefined;
  if (!provenance) return undefined;
  return isObject(provenance.blueprint) ? provenance.blueprint : undefined;
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
    return {
      format: "kg-viewer-snapshot",
      version: asNumber(value.version, 1),
      name: asString(value.name, "snapshot"),
      title: asString(value.title, asString(value.name, "Untitled snapshot")),
      blueprint: normalizeBlueprint(
        value.blueprint ?? embeddedBlueprint(value.workflow),
      ),
      workflow: normalizeWorkflow(value.workflow),
      report: normalizeReport(value.report),
      metaGraph: normalizeMetaGraph(value.metaGraph),
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
      blueprint: normalizeBlueprint(embeddedBlueprint(value)),
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
