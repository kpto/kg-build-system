import type { InspectorSelection } from "@/shared/types/selection";
import type {
  AuditReport,
  AuditSubject,
  CoverageMatrix,
  DecisionView,
  ReviewQueueSummary,
  ReviewRecord,
  ReviewSidecar,
  ReviewStatus,
  SnapshotDiff,
} from "@/lib/reviewTypes";
import type {
  EntityKind,
  LineageGraph,
  LineageNode,
  PropertySelection,
  StepId,
  ViewerIndex,
  ViewerSnapshot,
  WorkflowStep,
} from "@/lib/types";

export type Task = "map" | "explore" | "review";
export type Representation = "workflow" | "blueprint" | "lineage";
export type Grouping = "component" | "emitter";

export interface CampaignCounts {
  assets: number;
  tables: number;
  projections: number;
  nodes: number;
  edges: number;
  bindings: number;
  steps: number;
  connections: number;
}

/** The evidence record owned by the campaign/viewer. */
export interface CampaignRecord {
  snapshot: ViewerSnapshot;
  index: ViewerIndex;
  review: ReviewSidecar;
  audit: AuditReport | null;
  coverage: CoverageMatrix | null;
  decisions: DecisionView[];
  queue: Record<string, ReviewRecord>;
  queueSummary: ReviewQueueSummary;
  baseline: ViewerSnapshot | null;
  diff: SnapshotDiff | null;
  loadError?: string;
  importError?: string;
}

/**
 * What every domain model may read from the campaign. It contains the record,
 * the selected subject and the commands; it does not contain React state.
 */
export interface CampaignView {
  record: CampaignRecord;
  task: Task;
  representation: Representation;
  selection: InspectorSelection | null;
  counts: CampaignCounts;
  commands: CampaignCommands;
}

export interface CampaignCommands {
  setTask: (task: Task) => void;
  setRepresentation: (representation: Representation) => void;
  setQuery: (query: string) => void;
  importFile: (file: File) => void;
  select: (selection: InspectorSelection | null) => void;
  selectProperty: (
    kind: EntityKind,
    component: string,
    property: string,
    source?: string,
  ) => void;
  selectStep: (step: WorkflowStep) => void;
  selectLineageNode: (node: LineageNode) => void;
  openReview: (subject: AuditSubject) => void;
  openReviewForStep: (step: WorkflowStep) => void;
  selectFinding: (findingId?: string) => void;
  focusStep: (step: WorkflowStep) => void;
  clearFocus: () => void;
  clearReviewSubject: () => void;
  setLineageSourceFilter: (source?: string) => void;
  clearLineageSource: () => void;
  setReviewStatus: (
    findingId: string,
    status: ReviewStatus,
    note?: string,
  ) => void;
  pinBaseline: () => void;
  clearBaseline: () => void;
  compareSnapshot: (file: File) => void;
  exportDossier: (format: "markdown" | "json") => void;
  copyDossier: (format: "markdown" | "json") => void;
}

export interface DomainState {
  /** Domain-specific filter/selection that is not campaign-wide. */
  focusStepId?: StepId;
  reviewSubjectFilter?: AuditSubject;
  selectedFindingId?: string;
  lineageSourceFilter?: string;
  selectedLineageNodeId?: string;
  propertySelection?: PropertySelection;
  lineage?: LineageGraph;
  changed?: boolean;
}
