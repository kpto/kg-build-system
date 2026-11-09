import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { buildAudit } from "@/lib/audit";
import { buildCoverage } from "@/lib/coverage";
import { deriveDecisions } from "@/lib/decisions";
import { loadReviewSidecar, normalizeReviewSidecar } from "@/lib/load";
import type { CampaignCommands, CampaignRecord } from "@/shared/model/campaign";
import { buildCampaignModel } from "@/review/model/buildCampaignModel";
import { buildNavigatorModel } from "@/navigation/model/buildNavigatorModel";
import { buildPropertiesModel } from "@/properties/model/buildPropertiesModel";
import { buildTopologyModel } from "@/topology/model/buildTopologyModel";
import { buildDiagnosisModel } from "@/diagnosis/model/buildDiagnosisModel";
import { buildAppModel } from "@/review/model/buildAppModel";
import { index, snapshot } from "./fixtures";

const reviewText = readFileSync(
  new URL("../public/data/reference.review.json", import.meta.url),
  "utf8",
);

const review = (() => {
  const value = normalizeReviewSidecar(JSON.parse(reviewText));
  if (!value) throw new Error("reference review sidecar did not normalise");
  return value;
})();

const noop = () => {};
const commands: CampaignCommands = {
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

const record: CampaignRecord = {
  snapshot,
  index,
  review,
  audit: buildAudit(index, review),
  coverage: buildCoverage(index),
  decisions: deriveDecisions(index, review),
  queue: {},
  queueSummary: { resolved: 0, pending: 0, waived: 0 } as never,
  baseline: null,
  diff: null,
};

const counts = {
  assets: index.stats.assets,
  tables: index.stats.tables,
  projections: index.stats.projections,
  nodes: index.stats.topologyNodes,
  edges: index.stats.topologyEdges,
  bindings: index.stats.bindings,
  steps: index.stats.steps,
  connections: index.stats.connections,
};

function campaign(overrides: Partial<Parameters<typeof buildCampaignModel>[0]> = {}) {
  return buildCampaignModel({
    record,
    task: "explore",
    representation: "workflow",
    selection: null,
    counts,
    commands,
    query: "",
    searchResults: [],
    onSearchSelect: noop,
    ...overrides,
  });
}

const program = {
  representation: "workflow" as const,
  grouping: "emitter" as const,
  collapsedGroups: new Set<string>(),
  setRepresentation: noop,
  setGrouping: noop,
  onToggleGroup: noop,
  onToggleAll: noop,
  focusStepId: undefined,
  lineageSourceFilter: undefined,
  onClearSourceFilter: noop,
};

describe("campaign model", () => {
  it("is the window level: identity, three tasks, counts", () => {
    const model = campaign();
    expect(model.header.tabs.map((tab) => tab.label)).toEqual([
      "Map",
      "Explore",
      "Review",
    ]);
    expect(model.header.task).toBe("explore");
    expect(model.view.record.index).toBe(index);
    expect(model.status.counts.steps).toBe(index.stats.steps);
  });
});

describe("diagnose task hierarchy", () => {
  it("builds navigator, diagnosis and properties as peer panels", () => {
    const view = campaign().view;
    const navigator = buildNavigatorModel(view, program);
    const diagnosis = buildDiagnosisModel(view, program);
    const properties = buildPropertiesModel(view);

    expect(navigator.title).toBe("Outliner");
    expect(navigator.sections.length).toBeGreaterThan(0);
    expect(navigator.sections.every((section) => section.question)).toBe(true);
    expect(navigator.meta).toBe(`${index.stats.steps} steps`);
    expect(navigator.groupingLabel).toBe("instruction");

    expect(diagnosis.tabs.map((tab) => tab.label)).toEqual([
      "Workflow",
      "Blueprint",
      "Lineage",
    ]);
    expect(diagnosis.header.question).toBeTruthy();
    expect(diagnosis.child.id).toBe("workflow");

    expect(properties.rails.map((rail) => rail.question)).toEqual([
      "What is this?",
      "How is it produced?",
      "What does it emit?",
      "What depends on it?",
      "What else is recorded?",
    ]);
    expect(properties.empty).toBe(true);
  });

  it("answers every properties rail for a selected subject", () => {
    const view = campaign({
      selection: { kind: "topology", entityKind: "node", name: "target" },
    }).view;
    const properties = buildPropertiesModel(view);
    expect(properties.empty).toBe(false);
    expect(properties.subjectTitle).toBe("target");
    const answered = properties.rails.flatMap(
      (rail) => properties.sectionsFor[rail.id],
    );
    expect(answered.length).toBeGreaterThan(0);
    expect(answered.every((section) => section.question.length > 0)).toBe(true);
    // Every section belongs to at least one rail: no evidence is unreachable.
    for (const section of answered) {
      expect(
        properties.rails.some((rail) =>
          properties.sectionsFor[rail.id].some((entry) => entry.id === section.id),
        ),
      ).toBe(true);
    }
  });
});

describe("representation models", () => {
  it("execution owns groups, steps and the grouping overlay", () => {
    const view = campaign().view;
    const diagnosis = buildDiagnosisModel(view, program);
    if (diagnosis.child.id !== "workflow") throw new Error("expected workflow");
    const execution = diagnosis.child.model;
    expect(execution.graph.groups.length).toBeGreaterThan(0);
    expect(execution.graph.steps.length).toBe(index.stats.steps);
    expect(execution.graph.grouping).toBe("emitter");
    expect(execution.overlay.grouping.options.map((option) => option.id)).toEqual([
      "component",
      "emitter",
    ]);
    expect(execution.question).toBeTruthy();
  });

  it("semantics owns the cards model and the audit legend", () => {
    const view = campaign({ representation: "blueprint" }).view;
    const diagnosis = buildDiagnosisModel(view, {
      ...program,
      representation: "blueprint",
    });
    if (diagnosis.child.id !== "blueprint") throw new Error("expected blueprint");
    const semantics = diagnosis.child.model;
    expect(semantics.overlay.auditKey.legend.length).toBeGreaterThan(0);
    expect(semantics.overlay.counts.totalEntities).toBe(
      semantics.cards.entityCount,
    );
    expect(semantics.cards.groups.length).toBeGreaterThan(0);
    expect(semantics.cards.groups.every((group) => group.question)).toBe(true);
  });

  it("topology owns the map and the navigator panel", () => {
    const view = campaign({ task: "map" }).view;
    const topology = buildTopologyModel(view);
    expect(topology.stats.nodes).toBe(index.stats.topologyNodes);
    expect(topology.navigator.sections.map((section) => section.id)).toEqual([
      "selection",
      "groups",
      "properties",
      "neighbours",
    ]);
  });
});

describe("app model", () => {
  it("builds exactly one task", () => {
    const model = buildAppModel({
      record,
      task: "map",
      representation: "workflow",
      selection: null,
      counts,
      commands,
      query: "",
      searchResults: [],
      onSearchSelect: noop,
      navigator: program,
      diagnosis: program,
      audit: {
        selectedFindingId: undefined,
        subjectFilter: undefined,
        onClearSubjectFilter: noop,
      },
    });
    expect(model.campaign.header.title).toBeTruthy();
    expect(model.task.kind).toBe("map");
  });
});
