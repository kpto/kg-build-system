/**
 * Public data model for the viewer.
 *
 * These types mirror the JSON artifacts produced by kg-build-system. They are
 * deliberately structural: unknown payload fields survive round trips and the
 * data/index layer never mutates a loaded artifact.
 */



export type Ref = string[];

/** A workflow step identity: [component, name]. */
export type StepId = [string, string];

/** An instruction identity: [operation, engine], for example ["sql", "duckdb"]. */
export type InstructionKind = [string, string];

/** A fully qualified artifact/opening tuple, e.g. ["core", "binding.0", "output", "output"]. */
export type Opening = string[];

/** A blueprint artifact type, e.g. ["core", "binding", "defect", "0"]. */
export type ArtifactType = string[];

export type EntityKind = "node" | "edge";

export interface LogicalType {
  kind: string;
  name?: string;
  module?: string;
  qualname?: string;
  value?: LogicalType;
  item?: LogicalType;
  [key: string]: unknown;
}

export interface AnnotationDTO {
  namespace: string;
  id: string;
  arguments?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Semantics and graph declaration
// ---------------------------------------------------------------------------

/** A single attached semantic unit: one claim, limitation or purpose text. */
export interface SemanticText {
  text: string;
}

/** One expected use of a subject and the limitations that bound it. */
export interface PurposeDTO {
  text: string;
  limitations?: SemanticText[];
}

/**
 * Meaning attached to any subject: at most one local purpose plus contextless
 * claims. The graph declaration's purpose is the root.
 */
export interface SemanticsDTO {
  purpose?: PurposeDTO;
  claims?: SemanticText[];
}

/** The one graph declaration a project carries. */
export interface GraphDeclarationDTO {
  name: string;
  description?: string | null;
  semantics: SemanticsDTO;
}

/** Descriptive asset profile; separate from attached semantics. */
export interface AssetProfileDTO {
  subject: string;
  coverage: string;
  authority: string;
  basis: string;
  title?: string | null;
  description?: string | null;
}

export interface FieldExpression {
  kind: "field";
  field: Ref;
  path?: string[];
  logical_type?: LogicalType;
  [key: string]: unknown;
}

export interface LiteralExpression {
  kind: "literal";
  value: unknown;
  logical_type?: LogicalType;
  [key: string]: unknown;
}

export interface OperationExpression {
  kind: "operation";
  operator: Ref;
  arguments: Expression[];
  parameters?: Record<string, unknown>;
  logical_type?: LogicalType;
  [key: string]: unknown;
}

export type Expression = FieldExpression | LiteralExpression | OperationExpression;

export interface DataField {
  name: string;
  logical_type: LogicalType;
  ref?: Ref;
  annotations?: AnnotationDTO[];
  description?: string;
  expression?: Expression;
  semantics?: SemanticsDTO;
  [key: string]: unknown;
}

export interface RowSource {
  kind: string;
  relation?: Ref;
  left?: RowSource;
  right?: RowSource;
  [key: string]: unknown;
}

export interface RelationDTO {
  name: string;
  columns: DataField[];
  annotations?: AnnotationDTO[];
  description?: string;
  asset?: Ref;
  semantics?: SemanticsDTO;
  [key: string]: unknown;
}

export interface ProjectionDTO {
  name: string;
  columns: DataField[];
  annotations?: AnnotationDTO[];
  description?: string;
  asset?: Ref;
  row_source: RowSource;
  semantics?: SemanticsDTO;
  [key: string]: unknown;
}

export interface StructDTO {
  name: string;
  columns: DataField[];
  annotations?: AnnotationDTO[];
  description?: string;
  semantics?: SemanticsDTO;
  [key: string]: unknown;
}

export interface AssetLayout {
  kind?: string;
  locator?: string | null;
  format?: string;
  selector?: string | null;
  partition_by?: string[];
  members?: Record<string, string>;
  properties?: Record<string, unknown>;
  [key: string]: unknown;
}

/**
 * @deprecated The current blueprint splits an asset into `profile`
 * ({@link AssetProfileDTO}) and attached `semantics` ({@link SemanticsDTO}).
 * This alias remains only for older documents and consumers.
 */
export type AssetSemantics = AssetProfileDTO & {
  claims?: string[];
  limitations?: string[];
  [key: string]: unknown;
};

export interface AssetLicense {
  identifier: string;
  url?: string | null;
  attribution?: string | null;
  [key: string]: unknown;
}

export interface AssetGovernance {
  /** A structured licence, or the older plain-string form. */
  license?: AssetLicense | string | null;
  owner?: string | null;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AssetDTO {
  name: string;
  website?: string | null;
  version?: string | null;
  layout?: AssetLayout;
  profile?: AssetProfileDTO;
  semantics?: SemanticsDTO;
  governance?: AssetGovernance;
  annotations?: AnnotationDTO[];
  [key: string]: unknown;
}

export interface TopologyProperty {
  name: string;
  logical_type: LogicalType;
  ref: Ref;
  annotations?: AnnotationDTO[];
  description?: string;
  semantics?: SemanticsDTO;
  [key: string]: unknown;
}

export interface TopologyNode {
  name: string;
  labels?: string[];
  abstract?: boolean;
  properties?: TopologyProperty[];
  annotations?: AnnotationDTO[];
  description?: string;
  parent?: Ref;
  semantics?: SemanticsDTO;
  [key: string]: unknown;
}

export interface TopologyEdge extends TopologyNode {
  source?: Ref;
  target?: Ref;
}

export interface TopologyGraph {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface BlueprintData {
  structs: StructDTO[];
  relations: RelationDTO[];
  projections: ProjectionDTO[];
}

export interface BindingDTO {
  kind: EntityKind;
  node?: Ref;
  edge?: Ref;
  identity?: Expression;
  source_identity?: Expression;
  target_identity?: Expression;
  properties?: Record<string, Expression>;
  rows?: RowSource;
  annotations?: AnnotationDTO[];
  mode?: string;
  debug_name?: string;
  python_ref?: {
    module?: string;
    qualname?: string;
    signature?: string;
    [key: string]: unknown;
  };
  semantics?: SemanticsDTO;
  [key: string]: unknown;
}

export interface BlueprintDTO {
  graph_declaration?: GraphDeclarationDTO;
  graph: TopologyGraph;
  data: BlueprintData;
  assets: AssetDTO[];
  bindings: BindingDTO[];
}

export interface WorkflowComponent {
  id: string;
  runtime_fields?: Array<string | Record<string, unknown>>;
  version?: string;
  [key: string]: unknown;
}

export interface WorkflowInputOpening {
  declared_name?: string;
  opening_name: Opening;
  type: ArtifactType;
  [key: string]: unknown;
}

export interface WorkflowOutputOpening {
  kind?: string;
  opening_name: Opening;
  type: ArtifactType;
  [key: string]: unknown;
}

export interface WorkflowInstruction {
  kind: InstructionKind;
  payload: Record<string, unknown>;
  [key: string]: unknown;
}

export interface WorkflowStep {
  id: StepId;
  inputs?: WorkflowInputOpening[];
  outputs?: WorkflowOutputOpening[];
  instruction: WorkflowInstruction;
  assembly_preference?: string;
  [key: string]: unknown;
}

export interface WorkflowConnection {
  input: Opening;
  output: Opening;
  [key: string]: unknown;
}

export interface WorkflowPlan {
  components: WorkflowComponent[];
  steps: WorkflowStep[];
  connections: WorkflowConnection[];
  provenance?: Record<string, unknown> | null;
}

export interface PublishedArtifact {
  opening: Opening;
  type: ArtifactType;
  value: Record<string, unknown>;
}

export interface BuildReport {
  published_artifacts: PublishedArtifact[];
  recovered_failures: unknown[];
  unresolved_failures: unknown[];
  provenance?: Record<string, unknown> | null;
}

export interface MetaGraphProperty {
  name: string;
  description?: string;
  logical_type?: LogicalType;
  type?: string;
  nullable?: boolean;
  examples?: unknown[];
  annotations?: AnnotationDTO[];
  [key: string]: unknown;
}

export interface MetaGraphCounts {
  bindings?: number;
  declared_children?: number;
  inclusive_records?: number;
  records?: number;
  [key: string]: number | undefined;
}

export interface MetaGraphComponent {
  name: string;
  kind: EntityKind;
  label?: string;
  labels?: string[];
  parent?: string | null;
  abstract?: boolean;
  description?: string;
  annotations?: AnnotationDTO[];
  properties?: MetaGraphProperty[];
  counts?: MetaGraphCounts;
  bindings?: Array<Record<string, unknown>>;
  endpoints?: { source?: string; target?: string } | null;
  source?: string | null;
  target?: string | null;
  depth?: number;
  children?: unknown[];
  [key: string]: unknown;
}

export interface MetaGraph {
  nodes: MetaGraphComponent[];
  edges: MetaGraphComponent[];
  examples?: {
    limit?: number;
    method?: string;
    [key: string]: unknown;
  };
  summary?: Record<string, unknown>;
  generated_by?: Record<string, unknown>;
}

export interface ViewerSnapshot {
  format: "kg-viewer-snapshot";
  version: number;
  name: string;
  title: string;
  blueprint: BlueprintDTO;
  workflow: WorkflowPlan;
  report: BuildReport;
  metaGraph?: MetaGraph;
}

// ---------------------------------------------------------------------------
// Normalized workflow identities
// ---------------------------------------------------------------------------

export interface OpeningRef {
  raw: Opening;
  component: string;
  step: string;
  direction: "input" | "output" | string;
  opening: string[];
  openingName: string;
  key: string;
  stepId: StepId;
  stepKey: string;
}

export interface NormalizedConnection {
  id: string;
  input: OpeningRef;
  output: OpeningRef;
  inputStepId: StepId;
  outputStepId: StepId;
  inputKey: string;
  outputKey: string;
}

export interface IndexedBinding {
  /** Index in `blueprint.bindings`; this is the binding identity used by output artifacts. */
  index: number;
  binding: BindingDTO;
  kind: EntityKind;
  component: string;
  componentRef: Ref;
  outputArtifact: ArtifactType;
  outputArtifactKey: string;
  step?: WorkflowStep;
}

export interface PropertyLookupEntry {
  component: string;
  kind: EntityKind;
  property: string;
  propertyRef: Ref;
  binding: IndexedBinding;
  expression?: Expression;
  fieldRefs: Ref[];
}

export interface FieldLocation {
  key: string;
  ownerName: string;
  ownerKind: "relation" | "projection" | "struct";
  field: DataField;
}

export interface MetaGraphIndex {
  byKey: Map<string, MetaGraphComponent>;
  byName: Map<string, MetaGraphComponent[]>;
  components: MetaGraphComponent[];
}

export interface SearchSource {
  topologyNodes: TopologyNode[];
  topologyEdges: TopologyEdge[];
  relations: RelationDTO[];
  projections: ProjectionDTO[];
  structs: StructDTO[];
  fields: FieldLocation[];
  assets: AssetDTO[];
  bindings: IndexedBinding[];
  steps: WorkflowStep[];
  workflowComponents: WorkflowComponent[];
}

/**
 * Every subject kind that can carry attached semantics.
 *
 * `graph` is the graph declaration; its root purpose is `semantics.purpose`.
 */
export type SemanticSubjectKind =
  | "graph"
  | "asset"
  | "relation"
  | "projection"
  | "struct"
  | "field"
  | "node"
  | "edge"
  | "property"
  | "binding";

/** One indexed semantic subject. The attached units are evidence, not inferred. */
export interface SemanticSubject {
  kind: SemanticSubjectKind;
  /** Deterministic viewer-side key; see `semanticSubjectKey`. */
  key: string;
  /** Display name; for a field this is the field name. */
  name: string;
  /** Attached semantics, if the snapshot carries any. */
  semantics?: SemanticsDTO;
  ref?: Ref;
  ownerName?: string;
  entityKind?: EntityKind;
  bindingIndex?: number;
  assetName?: string;
}

export interface ViewerIndex extends SearchSource {
  snapshot: ViewerSnapshot;
  blueprint: BlueprintDTO;
  workflow: WorkflowPlan;
  /** The graph declaration, absent when the snapshot does not carry one. */
  graphDeclaration?: GraphDeclarationDTO;
  graphSemantics?: SemanticsDTO;
  stepsById: Map<string, WorkflowStep>;
  stepIdByKey: Map<string, StepId>;
  componentsById: Map<string, WorkflowComponent>;
  stepsByComponent: Map<string, WorkflowStep[]>;
  stepsByEmitter: Map<string, WorkflowStep[]>;
  connections: NormalizedConnection[];
  incomingByStepId: Map<string, NormalizedConnection[]>;
  outgoingByStepId: Map<string, NormalizedConnection[]>;
  producersByArtifactKey: Map<string, WorkflowStep[]>;
  producerByArtifactKey: Map<string, WorkflowStep>;
  topologyNodesByName: Map<string, TopologyNode>;
  topologyEdgesByName: Map<string, TopologyEdge>;
  topologyComponentsByName: Map<string, TopologyNode | TopologyEdge>;
  topologyPropertyByName: Map<string, TopologyProperty>;
  relationByName: Map<string, RelationDTO>;
  projectionByName: Map<string, ProjectionDTO>;
  structByName: Map<string, StructDTO>;
  dataEntityByName: Map<string, RelationDTO | ProjectionDTO | StructDTO>;
  fieldsByKey: Map<string, FieldLocation>;
  assetsByName: Map<string, AssetDTO>;
  /** Asset profile by asset name; profiles are descriptive metadata. */
  assetProfilesByName: Map<string, AssetProfileDTO>;
  bindings: IndexedBinding[];
  bindingByComponent: Map<string, IndexedBinding[]>;
  bindingByOutputArtifactKey: Map<string, IndexedBinding>;
  propertyIndex: Map<string, PropertyLookupEntry[]>;
  /** Every subject that may carry semantics, in deterministic order. */
  semanticSubjects: SemanticSubject[];
  /** Semantic subjects keyed by `semanticSubjectKey`. */
  semanticsByKey: Map<string, SemanticSubject>;
  /** Semantic subjects grouped by kind. */
  semanticsByKind: Map<SemanticSubjectKind, SemanticSubject[]>;
  metaGraph: MetaGraphIndex;
  searchRecords: SearchRecord[];
  stats: ViewerStats;
}

export interface ViewerStats {
  assets: number;
  tables: number;
  projections: number;
  structs: number;
  topologyNodes: number;
  topologyEdges: number;
  topologyProperties: number;
  bindings: number;
  components: number;
  steps: number;
  connections: number;
}

export type SearchKind =
  | "topology-node"
  | "topology-edge"
  | "property"
  | "relation"
  | "projection"
  | "struct"
  | "field"
  | "asset"
  | "binding"
  | "step"
  | "instruction"
  | "workflow-component";

export interface SearchRecord {
  id: string;
  kind: SearchKind;
  name: string;
  label: string;
  detail: string;
  tokens: string[];
  /** Optional route information for the UI. */
  stepId?: StepId;
  component?: string;
  property?: string;
  entityKind?: EntityKind;
  ref?: Ref;
  bindingIndex?: number;
  instructionKind?: InstructionKind;
}

export interface SearchResult extends SearchRecord {
  score: number;
}

export interface SearchOptions {
  limit?: number;
  kinds?: SearchKind[];
}

// ---------------------------------------------------------------------------
// Annotations
// ---------------------------------------------------------------------------

export interface FlattenedAnnotation {
  key: string;
  namespace: string;
  id: string;
  label: string;
  arguments: Record<string, unknown>;
  argumentList: Array<{ key: string; value: unknown }>;
  text: string;
  source: AnnotationDTO;
}

export interface EnrichedAnnotation extends FlattenedAnnotation {
  description?: string;
  examples: unknown[];
  counts?: MetaGraphCounts;
  metaComponent?: MetaGraphComponent;
  metaProperty?: MetaGraphProperty;
}

export interface AnnotationContext {
  component?: string;
  kind?: EntityKind;
  property?: string;
}

// ---------------------------------------------------------------------------
// Lineage
// ---------------------------------------------------------------------------

export type LineageLane =
  | "asset"
  | "source"
  | "transformation"
  | "binding"
  | "post"
  | "target";

export type LineageNodeKind =
  | "asset"
  | "relation"
  | "table"
  | "projection"
  | "field"
  | "binding"
  | "aggregate"
  | "deduplication"
  | "merging"
  | "conflict"
  | "target"
  | "property"
  | "step";

export interface PropertySelection {
  kind: EntityKind;
  component: string;
  property: string;
  propertyRef: Ref;
}

export interface LineageNodeMetadata {
  artifacts: ArtifactType[];
  step?: WorkflowStep;
  payload?: unknown;
  annotations: AnnotationDTO[];
  annotationViews: EnrichedAnnotation[];
  description?: string;
  sourceLocation?: string;
  sqlPreview?: string;
  expression?: Expression;
  examples?: unknown[];
  counts?: MetaGraphCounts;
}

export interface LineageNode {
  id: string;
  label: string;
  lane: LineageLane;
  category: "semantic" | "workflow";
  kind: LineageNodeKind;
  component?: string;
  property?: string;
  stepId?: StepId;
  ref?: Ref;
  metadata: LineageNodeMetadata;
}

export interface LineageEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  branchKey: string;
}

export interface LineageBranch {
  key: string;
  propertyRef: Ref;
  propertyName: string;
  binding: IndexedBinding;
  expression?: Expression;
  fieldRefs: Ref[];
  fieldKeys: string[];
  relationNames: string[];
  sourceRelations: string[];
  assetNames: string[];
  bindingStep?: WorkflowStep;
  transformationSteps: WorkflowStep[];
  sourceSteps: WorkflowStep[];
  postSteps: WorkflowStep[];
  targetSteps: WorkflowStep[];
  upstreamSteps: WorkflowStep[];
  downstreamSteps: WorkflowStep[];
  nodeIds: string[];
  edgeIds: string[];
}

export interface LineageGraph {
  selection: PropertySelection;
  branches: LineageBranch[];
  nodes: LineageNode[];
  edges: LineageEdge[];
  lanes: Array<{ id: LineageLane; label: string }>;
  terminalNodeId: string;
}

export const LINEAGE_LANES: Array<{ id: LineageLane; label: string }> = [
  { id: "asset", label: "Asset" },
  { id: "source", label: "Source / Table" },
  { id: "transformation", label: "Transformation / Projection" },
  { id: "binding", label: "Binding" },
  { id: "post", label: "Post-processing" },
  { id: "target", label: "Target" },
];
