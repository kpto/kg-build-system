import { describe, expect, it } from "vitest";
import { buildLineage, propertySelection } from "../lib/lineage";
import type { DiagnosisInput } from "../shared/model/builders";
import type {
  CampaignCommands,
  CampaignRecord,
  CampaignView,
} from "../shared/model/campaign";
import type { InspectorSelection } from "../shared/types/selection";
import {
  buildSemanticsModel,
  type SemanticsModel,
} from "../diagnosis/semantics/model/SemanticsModel";
import { buildProvenanceModel } from "../diagnosis/provenance/model/ProvenanceModel";
import { index, snapshot } from "./fixtures";

function commands(): CampaignCommands {
  const noop = () => {};
  return {
    setTask: noop,
    setRepresentation: noop,
    setQuery: noop,
    importFile: noop,
    select: noop,
    selectProperty: noop,
    selectStep: noop,
    selectLineageNode: noop,
    openReview: noop,
    openReviewForStep: noop,
    selectFinding: noop,
    focusStep: noop,
    clearFocus: noop,
    clearReviewSubject: noop,
    setLineageSourceFilter: noop,
    clearLineageSource: noop,
    setReviewStatus: noop,
    pinBaseline: noop,
    clearBaseline: noop,
    compareSnapshot: noop,
    exportDossier: noop,
    copyDossier: noop,
  };
}

const record: CampaignRecord = {
  snapshot,
  index,
  review: { format: "kg-viewer-review", version: 1, decisions: [] },
  audit: null,
  coverage: null,
  decisions: [],
  queue: {},
  queueSummary: {
    total: 0,
    open: 0,
    acknowledged: 0,
    waived: 0,
    resolved: 0,
  },
  baseline: null,
  diff: null,
};

function campaign(selection: InspectorSelection | null = null): CampaignView {
  return {
    record,
    task: "explore",
    representation: "blueprint",
    selection,
    counts: {
      assets: index.stats.assets,
      tables: index.stats.tables,
      projections: index.stats.projections,
      nodes: index.stats.topologyNodes,
      edges: index.stats.topologyEdges,
      bindings: index.stats.bindings,
      steps: index.stats.steps,
      connections: index.stats.connections,
    },
    commands: commands(),
  };
}

function diagnosisInput(overrides: Partial<DiagnosisInput> = {}): DiagnosisInput {
  return {
    representation: "lineage",
    setRepresentation: () => {},
    grouping: "component",
    setGrouping: () => {},
    collapsedGroups: new Set(),
    onToggleGroup: () => {},
    onToggleAll: () => {},
    onClearSourceFilter: () => {},
    ...overrides,
  };
}

const conditionRating = propertySelection(
  "node",
  "defect",
  "condition_rating",
);
const conditionRatingSelection: InspectorSelection = {
  kind: "property",
  selection: conditionRating,
  lineage: buildLineage(index, conditionRating),
};

const readingValue = propertySelection("node", "reading", "value");
const readingValueSelection: InspectorSelection = {
  kind: "property",
  selection: readingValue,
  lineage: buildLineage(index, readingValue),
};

describe("semantics model", () => {
  it("builds one deterministic index shared by Cards and Graph", () => {
    const model = buildSemanticsModel(campaign());

    expect(model.id).toBe("semantics");
    expect(model.overlay.defaultMode).toBe("graph");
    expect(model.cards.groups.map((group) => group.parent)).toEqual([
      "documented",
      "monitored_relation",
      "uncategorized",
    ]);
    expect(model.cards.entityCount).toBe(
      index.stats.topologyNodes + index.stats.topologyEdges,
    );
    expect(model.graph.entityCards).toHaveLength(index.stats.topologyNodes);
    expect(model.graph.edgeCards).toHaveLength(index.stats.topologyEdges);
    expect(model.graph.focus?.groupId).toBe("documented");

    const defect = model.cards.groups
      .flatMap((group) => group.entities)
      .find((entity) => entity.kind === "node" && entity.name === "defect");
    expect(defect).toBeDefined();
    const rating = defect?.properties.find(
      (property) => property.name === "condition_rating",
    );
    expect(rating?.source.value).toBe("surveys");
    expect(rating?.actions.map((action) => action.id)).toContain(
      "open-lineage",
    );
    expect(rating?.badges.map((badge) => badge.kind)).toContain("traced");
  });

  it("marks the selected property on its entity and property row", () => {
    const model = buildSemanticsModel(campaign(conditionRatingSelection));
    const defect = model.cards.groups
      .flatMap((group) => group.entities)
      .find((entity) => entity.kind === "node" && entity.name === "defect");
    const rating = defect?.properties.find(
      (property) => property.name === "condition_rating",
    );

    expect(model.graph.selectedSubject?.kind).toBe("property");
    expect(defect?.highlighted).toBe(true);
    expect(defect?.selected).toBe(false);
    expect(rating?.selected).toBe(true);
    expect(
      model.graph.edges.some((edge) => edge.active && !edge.dimmed),
    ).toBe(true);
  });

  it("opens a large index on one group but keeps every header", () => {
    const model: SemanticsModel = buildSemanticsModel(campaign());
    const groupIds = model.cards.groups.map((group) => group.id);
    const collapsed = new Set(model.cards.defaultCollapsedGroupIds);

    expect(model.cards.defaultCollapsedGroupIds.length).toBe(0);
    expect(groupIds.every((id) => !collapsed.has(id))).toBe(true);
  });
});

describe("provenance model", () => {
  it("builds the proof receipt, impact and questions for a property", () => {
    const model = buildProvenanceModel(
      campaign(conditionRatingSelection),
      diagnosisInput(),
    );

    expect(model.graph?.selectionLabel).toBe("defect.condition_rating");
    expect(model.graph?.nodes.length).toBeGreaterThan(0);
    expect(model.receipt?.rows).toHaveLength(
      conditionRatingSelection.lineage.branches.length,
    );
    expect(model.receipt?.rows[0]?.bindingIndex).toBe(0);
    expect(model.impact?.fields.map((field) => field.id)).toEqual([
      "upstream",
      "downstream",
      "targets",
      "records",
      "nodes",
      "edges",
    ]);
    expect(model.sourceFilter.visible).toBe(false);
  });

  it("compares branches and carries the source filter", () => {
    const model = buildProvenanceModel(
      campaign(readingValueSelection),
      diagnosisInput({ lineageSourceFilter: "temperature" }),
    );

    expect(model.branchComparison?.branches).toHaveLength(
      readingValueSelection.lineage.branches.length,
    );
    expect(model.sourceFilter.visible).toBe(true);
    expect(model.sourceFilter.active).toBe("temperature");
    expect(model.sourceFilter.activeBranches).toBeGreaterThan(0);
    expect(
      model.graph?.nodes.some((node) => node.dimmed),
    ).toBe(true);
  });

  it("returns the empty provenance body without a selection", () => {
    const model = buildProvenanceModel(campaign(null), diagnosisInput());

    expect(model.graph).toBeNull();
    expect(model.receipt).toBeNull();
    expect(model.empty.examples.map((example) => example.id)).toEqual([
      "lineage-example-defect-condition-rating",
      "lineage-example-reading-value",
    ]);
    expect(model.empty.openBlueprint.id).toBe("lineage-empty-open-blueprint");
  });
});
