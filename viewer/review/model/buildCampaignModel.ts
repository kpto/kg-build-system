import type {
  CampaignCounts,
  CampaignRecord,
  CampaignView,
  CampaignCommands,
  Representation,
  Task,
} from "@/shared/model/campaign";
import type { InspectorSelection } from "@/shared/types/selection";
import type { SearchResult } from "@/lib/types";
import type {
  CampaignHeaderModel,
  CampaignModel,
  CampaignStatusModel,
  CampaignTaskTabModel,
} from "./CampaignModel";

/**
 * The controller state the campaign model is projected from.
 *
 * It is plain data plus commands: the builder reads the evidence record, the
 * active task and the campaign selection; it never reads a React hook.
 */
export interface CampaignModelInput {
  record: CampaignRecord;
  task: Task;
  representation: Representation;
  selection: InspectorSelection | null;
  counts: CampaignCounts;
  commands: CampaignCommands;
  query: string;
  searchResults: SearchResult[];
  onSearchSelect: (result: SearchResult) => void;
  /** Weighted audit score, when the audit has been built. */
  score?: number;
  /** Upstream/downstream pair for the selected subject, when there is one. */
  impact?: string;
}

const TASK_TABS: CampaignTaskTabModel[] = [
  {
    id: "map",
    task: "map",
    label: "Map",
    hint: "Topology workspace (M)",
    icon: "map",
  },
  {
    id: "explorer",
    task: "explore",
    label: "Explore",
    hint: "Workflow, blueprint and lineage (B)",
    icon: "explore",
  },
  {
    id: "review",
    task: "review",
    label: "Review",
    hint: "Findings, coverage and decisions (R)",
    icon: "review",
  },
];

function buildHeader(input: CampaignModelInput): CampaignHeaderModel {
  const { record, task, commands } = input;
  return {
    title: record.snapshot.title,
    snapshot: `${record.snapshot.name} · ${record.snapshot.workflow.steps.length} steps`,
    task,
    tabs: TASK_TABS,
    onTask: commands.setTask,
    review: {
      open: record.queueSummary.open,
      total: record.queueSummary.total,
    },
    search: {
      query: input.query,
      results: input.searchResults,
      onQuery: commands.setQuery,
      onSelect: input.onSearchSelect,
    },
    import: {
      ...(record.importError ? { error: record.importError } : {}),
      onFile: commands.importFile,
    },
  };
}

function isCompileOnly(record: CampaignRecord): boolean {
  const provenance = record.snapshot.report.provenance;
  return (
    provenance !== null &&
    typeof provenance === "object" &&
    (provenance as Record<string, unknown>).mode === "compile-only"
  );
}

function buildStatus(input: CampaignModelInput): CampaignStatusModel {
  const { record } = input;
  const total = record.queueSummary.total;
  const open = record.queueSummary.open;
  return {
    counts: input.counts,
    review: {
      resolved: Math.max(0, total - open),
      total,
    },
    ...(input.score !== undefined ? { score: input.score } : {}),
    ...(input.impact ? { impact: input.impact } : {}),
    build: {
      failures:
        record.snapshot.report.unresolved_failures.length +
        record.snapshot.report.recovered_failures.length,
      compileOnly: isCompileOnly(record),
      metaComponents: record.index.metaGraph.components.length,
    },
  };
}

/**
 * Project the current controller state onto the campaign model.
 *
 * Pure: the same input produces the same model, and no view is referenced.
 */
export function buildCampaignModel(input: CampaignModelInput): CampaignModel {
  const view: CampaignView = {
    record: input.record,
    task: input.task,
    representation: input.representation,
    selection: input.selection,
    counts: input.counts,
    commands: input.commands,
  };
  return {
    header: buildHeader(input),
    status: buildStatus(input),
    view,
  };
}
