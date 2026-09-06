/**
 * Wire types for the REST + WebSocket contract in `studio/docs/API.md`, plus the
 * one props interface every feature area is built against.
 */

import type { ReactNode } from "react";

import type {
  Expression,
  JsonObject,
  LogicalType,
  Module,
  ProjectDocument,
  Projection,
  RefKind,
  Source,
  Struct,
  Table,
} from "./ir";

/* --------------------------------------------------------------------- problem model */

/** `types` = pyright, `blueprint` = framework validation, `build` = execution. */
export type ProblemTier = "types" | "blueprint" | "build" | "document";

export type ProblemSeverity = "error" | "warning" | "info";

/** How a problem's `ref` was arrived at; the UI must not present `null` as certain. */
export type RefTrust = "anchor" | "name" | null;

/** One shape for every tier, so the UI has a single problems component. */
export interface Problem {
  readonly id: string;
  readonly tier: ProblemTier;
  readonly severity: ProblemSeverity;
  readonly message: string;
  /** pyright rule, or framework error class. */
  readonly code?: string | null;
  /** Project-relative; null for `tier === "build"`. */
  readonly file?: string | null;
  readonly line?: number | null;
  readonly column?: number | null;
  readonly end_line?: number | null;
  readonly end_column?: number | null;
  /** Null when the problem is unmappable to a component. */
  readonly ref?: string | null;
  readonly ref_trusted?: RefTrust;
  readonly hint?: string | null;
}

export const PROBLEM_TIERS: readonly ProblemTier[] = ["types", "blueprint", "build", "document"];

export const TIER_LABEL: Readonly<Record<ProblemTier, string>> = {
  types: "types",
  blueprint: "blueprint",
  build: "build",
  document: "document",
};

export const SEVERITY_RANK: Readonly<Record<ProblemSeverity, number>> = {
  error: 0,
  warning: 1,
  info: 2,
};

/* -------------------------------------------------------------------- status model */

export type GenerationState = "clean" | "dirty" | "running" | "done" | "failed" | "never";

export interface GenerationStatus {
  readonly state: GenerationState;
  readonly at?: string | null;
  readonly changed?: readonly string[];
  readonly error?: string | null;
}

export interface StatusModel {
  readonly revision?: number;
  readonly generation?: GenerationStatus;
  readonly blueprint?: { readonly ok: boolean; readonly errors: number };
  readonly types?: {
    readonly errors: number;
    readonly warnings: number;
    readonly state?: string;
  };
  readonly build?: { readonly state: string };
  readonly project_root?: string | null;
}

/* ------------------------------------------------------------------ authoring index */

export type SelectableKind = "table" | "projection";

/** One flattened, addressable path inside a selectable, nested struct members included. */
export interface IndexPath {
  readonly path: readonly string[];
  readonly logical_type: LogicalType;
  readonly nullable?: boolean;
  readonly description?: string | null;
}

export interface SelectableEntry {
  readonly kind: SelectableKind;
  readonly id: string;
  readonly name: string;
  readonly declaration_name: string;
  readonly group?: string | null;
  readonly paths?: readonly IndexPath[];
}

export interface ResolvedProperty {
  readonly name: string;
  readonly logical_type: LogicalType;
  readonly optional?: boolean;
  /** The component that declares the slot, for inherited slots. */
  readonly declared_by?: string | null;
}

export interface ComponentIndexEntry {
  readonly id: string;
  readonly kind: "node" | "edge";
  readonly tier: "template" | "category" | "concrete";
  readonly resolved_properties?: readonly ResolvedProperty[];
  readonly endpoint_is_category?: { readonly source: boolean; readonly target: boolean };
}

export interface StructIndexEntry {
  readonly id: string;
  readonly declaration_name: string;
  readonly name?: string;
  readonly module?: string;
  readonly fields?: readonly ResolvedProperty[];
}

/** The guard a block applies to its predecessor, per API.md. */
export type OperatorShape =
  | "any"
  | "nullable"
  | "non_nullable"
  | "array"
  | "array_of_struct"
  | "struct"
  | "unit:str"
  | "unit:int"
  | "unit:float"
  | "unit:bool"
  | "array_of_non_null_str";

export type OperatorGroup = "source" | "navigation" | "effect" | "calculation" | string;

export interface OperatorEntry {
  readonly operator: string;
  readonly label: string;
  readonly requires?: { readonly shape?: OperatorShape | string };
  readonly produces?: string;
  readonly arity?: number;
  readonly group?: OperatorGroup;
  readonly docs?: string | null;
}

/**
 * Everything a visual editor needs to offer only valid choices; computed
 * server-side from the document so availability can never disagree with the
 * generator. The block palette the bindings composer renders is `operators`
 * filtered against the stack tip — never a hardcoded frontend list.
 */
export interface AuthoringIndex {
  readonly selectable?: readonly SelectableEntry[];
  readonly components?: readonly ComponentIndexEntry[];
  readonly operators?: readonly OperatorEntry[];
  readonly structs?: readonly StructIndexEntry[];
}

/* ------------------------------------------------------------------------ catalog */

export interface ModuleEntry {
  readonly id: string;
  readonly role: string;
  readonly label: string;
  readonly summary?: string;
  readonly import_module?: string;
  readonly class_qualname?: string;
  readonly configuration_schema?: JsonObject | null;
  readonly default_configuration?: JsonObject | null;
}

export interface UnitEntry {
  readonly name: string;
  readonly representative?: string;
  readonly graph_safe?: boolean;
}

export interface CatalogResponse {
  readonly modules?: readonly ModuleEntry[];
  readonly units?: readonly UnitEntry[];
  readonly operators?: readonly OperatorEntry[];
  readonly vocabulary?: Readonly<Record<string, JsonObject>>;
}

export interface DataFile {
  readonly location: string;
  readonly name: string;
  readonly format: string;
  readonly size_bytes?: string | number | null;
}

/* ----------------------------------------------------------------------------- plan */

export type PlanNodeKind =
  | "source"
  | "projection"
  | "binding"
  | "aggregate"
  | "operator"
  | "export"
  | "document"
  | "script";

export interface PlanSlot {
  readonly slot_id: string;
  readonly role?: string | null;
  readonly ref?: string | null;
}

export interface PlanNode {
  readonly id: string;
  readonly module_id: string;
  readonly label: string;
  readonly kind: PlanNodeKind;
  /** IR ref when the step is component-scoped. */
  readonly component?: string | null;
  readonly inputs?: readonly PlanSlot[];
  readonly outputs?: readonly PlanSlot[];
  /** Present when the step payload carries lowered SQL; shown verbatim. */
  readonly sql?: string | null;
  readonly notes?: readonly string[];
}

export interface PlanEdge {
  readonly id: string;
  readonly from_step: string;
  readonly from_slot: string;
  readonly to_step: string;
  readonly to_slot: string;
}

export interface PlanModule {
  readonly id: string;
  readonly label: string;
  readonly role?: string;
  readonly implementation_version?: string;
}

export interface Plan {
  readonly fingerprint?: string;
  readonly modules?: readonly PlanModule[];
  readonly nodes?: readonly PlanNode[];
  readonly edges?: readonly PlanEdge[];
}

/* ---------------------------------------------------------------- endpoint payloads */

export interface StateResponse {
  readonly document: ProjectDocument;
  readonly revision: number;
  readonly status?: StatusModel;
  readonly project_root?: string | null;
}

export interface DocumentResponse {
  readonly revision: number;
  readonly document: ProjectDocument;
}

export interface PutDocumentRequest {
  readonly revision: number;
  readonly document: ProjectDocument;
}

export interface PutDocumentResponse extends DocumentResponse {
  readonly problems?: readonly Problem[];
}

/** `409` body: the current document, which the client adopts. */
export interface ConflictResponse {
  readonly revision: number;
  readonly document: ProjectDocument;
  readonly reason: string;
}

export interface FieldError {
  readonly loc: readonly (string | number)[] | string;
  readonly msg: string;
}

export interface DiagnosticsResponse {
  readonly problems: readonly Problem[];
  readonly pyright?: { readonly state?: string; readonly files_open?: number };
}

export interface PlanResponse {
  readonly plan: Plan | null;
  readonly errors?: readonly Problem[];
  readonly fingerprint?: string | null;
}

export interface BlueprintResponse {
  readonly blueprint: JsonObject | null;
  readonly errors?: readonly Problem[];
  readonly fingerprint?: string | null;
  readonly summary?: JsonObject;
}

export interface BuildResponse {
  readonly ok: boolean;
  readonly report?: JsonObject | null;
  readonly artifacts?: readonly string[];
  readonly problems?: readonly Problem[];
}

export interface SourceResponse {
  readonly ref: string;
  readonly path: string | null;
  readonly text: string | null;
  readonly line?: number | null;
}

export interface NameSuggestRequest {
  readonly section: string;
  readonly label: string;
}

export interface NameSuggestResponse {
  readonly id: string;
  readonly declaration_name: string;
  readonly python_name: string;
  readonly taken: boolean;
}

export interface InferRequest {
  readonly location: string;
  readonly mode: string;
  readonly table?: string | null;
  readonly layout?: string | null;
}

export interface InferResponse {
  readonly tables?: readonly Table[];
  readonly structs?: readonly Struct[];
  readonly sources?: readonly Source[];
  readonly notes?: readonly string[];
}

export interface WorkspaceRequest {
  readonly project_root: string;
  readonly package: string;
  readonly name: string;
}

/* ------------------------------------------------------------------ WS event union */

/** The event types the backend documents in API.md. */
export type WsEventType =
  | "hello"
  | "document"
  | "generation"
  | "diagnostics"
  | "blueprint"
  | "plan"
  | "build"
  | "log";

export interface HelloEvent {
  readonly type: "hello";
  readonly revision?: number;
  readonly status?: StatusModel;
}

export interface DocumentEvent {
  readonly type: "document";
  readonly revision?: number;
  readonly document?: ProjectDocument;
  readonly origin?: "remote" | "self";
}

export interface GenerationEvent {
  readonly type: "generation";
  readonly state: GenerationState;
  readonly changed?: readonly string[];
  readonly error?: string | null;
  readonly elapsed_ms?: number | null;
}

export interface DiagnosticsEvent {
  readonly type: "diagnostics";
  readonly problems?: readonly Problem[];
  readonly pyright?: { readonly state?: string; readonly files_open?: number };
}

export interface BlueprintEvent {
  readonly type: "blueprint";
  readonly ok?: boolean;
  readonly errors?: readonly Problem[];
  readonly summary?: JsonObject;
}

export interface PlanEvent {
  readonly type: "plan";
  readonly plan?: Plan | null;
}

export interface BuildEvent {
  readonly type: "build";
  readonly state: "running" | "done" | "failed";
  readonly ok?: boolean;
  readonly artifacts?: readonly string[];
  readonly problems?: readonly Problem[];
}

export interface LogEvent {
  readonly type: "log";
  readonly level?: string;
  readonly text?: string;
}

/**
 * An event whose `type` the client does not model. It is still handed to
 * subscribers so a backend addition can never be silently swallowed.
 */
export interface UnknownEvent {
  readonly type: "unknown";
  readonly name: string;
  readonly payload: JsonObject;
}

export interface SocketEvent {
  readonly type: "socket";
  readonly state: "connecting" | "open" | "closed" | "error";
  readonly detail?: string;
}

/** Emitted locally after the `GET /api/state` resync on every (re)connect. */
export interface ResyncEvent {
  readonly type: "resync";
  readonly revision?: number;
  readonly document?: ProjectDocument;
  readonly status?: StatusModel;
}

export type StudioEvent =
  | HelloEvent
  | DocumentEvent
  | GenerationEvent
  | DiagnosticsEvent
  | BlueprintEvent
  | PlanEvent
  | BuildEvent
  | LogEvent
  | UnknownEvent
  | SocketEvent
  | ResyncEvent;

/* ------------------------------------------------------------------------ the shell */

/** The seven shell areas. Order is the tab order and the 1–7 key order. */
export const TAB_AREAS = [
  "topology",
  "contracts",
  "projections",
  "bindings",
  "sources",
  "modules",
  "plan",
] as const;

export type TabArea = (typeof TAB_AREAS)[number];

export const TAB_LABEL: Readonly<Record<TabArea, string>> = {
  topology: "Topology",
  contracts: "Contracts",
  projections: "Projections",
  bindings: "Bindings",
  sources: "Sources",
  modules: "Modules",
  plan: "Plan",
};

/**
 * Which area owns a ref kind: used by the problems panel to jump to the offending
 * tab and by the command palette.
 */
export const AREA_FOR_REF_KIND: Readonly<Record<RefKind, TabArea>> = {
  table: "contracts",
  struct: "contracts",
  annotation_type: "contracts",
  projection: "projections",
  component: "topology",
  binding: "bindings",
  source: "sources",
  module: "modules",
};

/** A feature area a tab renders; projections share the contracts feature. */
export const FEATURE_FOR_TAB: Readonly<Record<TabArea, string>> = {
  topology: "topology",
  contracts: "contracts",
  projections: "contracts",
  bindings: "bindings",
  sources: "sources",
  modules: "modules",
  plan: "plan",
};

export interface Notice {
  readonly id: string;
  readonly level: "info" | "warn" | "error";
  readonly text: string;
  readonly at: number;
}

/**
 * The contract every feature area is built against. The shell guarantees a
 * non-null document (it renders its own empty state otherwise) and passes the same
 * object to all areas, so an area never fetches or merges by itself.
 */
export interface FeatureProps {
  /** Current IR document, never null in the shell. */
  document: ProjectDocument;
  /** Derived selectable/operator catalogue; null until `GET /api/index` resolves. */
  index: AuthoringIndex | null;
  /** Problems relevant to this area, pre-filtered by the shell. */
  problems: Problem[];
  /** IR ref selected globally. */
  selectedRef: string | null;
  onSelectRef(ref: string | null): void;
  /**
   * Optimistic patch: the store applies `mutate` locally, `PUT`s the whole document
   * with the revision it last saw, adopts the server document on `200`, and adopts
   * the server document plus a notice on `409`. Coalesced to one request per 250 ms
   * window and recorded on the undo stack.
   */
  apply(mutate: (draft: ProjectDocument) => ProjectDocument): void;
}

/** What an inspector panel receives when the shell renders it for a selected ref. */
export interface InspectorProps {
  document: ProjectDocument;
  ref: string;
  problems: Problem[];
  onSelectRef(ref: string | null): void;
  apply: FeatureProps["apply"];
}

/** A panel registered by a feature so the inspector renders its own ref kinds. */
export interface InspectorPanel {
  readonly id: string;
  readonly label: string;
  /** Higher wins; the shell's generic panel registers at 0. */
  readonly priority?: number;
  matches(ref: string, document: ProjectDocument): boolean;
  render(props: InspectorProps): ReactNode;
}

/* ------------------------------------------------------------- expression re-exports */

/** One import surface for feature modules. */
export type { Expression, LogicalType, Module, ProjectDocument, Projection, Source, Struct, Table };
