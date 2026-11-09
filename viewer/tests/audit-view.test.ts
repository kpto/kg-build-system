// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { buildAudit } from "@/lib/audit";
import { buildCoverage } from "@/lib/coverage";
import { deriveDecisions } from "@/lib/decisions";
import { buildViewerIndex } from "@/lib/indexes";
import {
  loadSnapshotFromObject,
  normalizeReviewSidecar,
} from "@/lib/load";
import { summarizeQueue } from "@/lib/reviewQueue";
import type {
  CampaignCommands,
  CampaignRecord,
  CampaignView,
} from "@/shared/model/campaign";
import {
  buildAuditModel,
  type AuditFindingsSection,
} from "@/audit/model/AuditModel";
import { BuildAuditView } from "@/audit/view/BuildAuditView";

const snapshot = loadSnapshotFromObject(
  JSON.parse(readFileSync("public/data/reference.snapshot.json", "utf8")),
);
const index = buildViewerIndex(snapshot);

const review = (() => {
  const value = normalizeReviewSidecar(
    JSON.parse(readFileSync("public/data/reference.review.json", "utf8")),
  );
  if (!value) throw new Error("reference review sidecar did not normalise");
  return value;
})();

const audit = buildAudit(index, review);
const coverage = buildCoverage(index);
const decisions = deriveDecisions(index, review);
const queueSummary = summarizeQueue(audit, {});

const noop = () => {};
const setReviewStatus = vi.fn();
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
  setReviewStatus,
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
  audit,
  coverage,
  decisions,
  queue: {},
  queueSummary,
  baseline: null,
  diff: null,
};

const campaign: CampaignView = {
  record,
  task: "review",
  representation: "workflow",
  selection: null,
  counts: {
    assets: 0,
    tables: 0,
    projections: 0,
    nodes: 0,
    edges: 0,
    bindings: 0,
    steps: 0,
    connections: 0,
  },
  commands,
};

afterEach(() => {
  cleanup();
  setReviewStatus.mockClear();
});

function model() {
  return buildAuditModel(campaign, { onClearSubjectFilter: noop });
}

describe("audit view", () => {
  it("renders the panel header, rail and every section", () => {
    render(createElement(BuildAuditView, { model: model() }));

    expect(screen.getByTestId("review-tab-content")).toBeTruthy();
    expect(screen.getByTestId("review-section-rail")).toBeTruthy();
    expect(screen.getAllByTestId(/^review-rail-/)).toHaveLength(8);
    for (const testId of [
      "review-summary",
      "findings-panel",
      "design-questions",
      "coverage-matrix",
      "decision-ledger",
      "build-health",
      "snapshot-diff",
      "dossier-panel",
    ]) {
      expect(screen.getByTestId(testId)).toBeTruthy();
    }
  });

  it("keeps the selected finding blue and mounts a waiver draft", () => {
    const base = model();
    const findings = base.sections.find(
      (section): section is AuditFindingsSection =>
        section.kind === "findings",
    );
    if (!findings) throw new Error("missing findings");
    const first = findings.rows[0];
    const selected = buildAuditModel(campaign, {
      selectedFindingId: first.findingId,
      onClearSubjectFilter: noop,
    });
    render(createElement(BuildAuditView, { model: selected }));

    const row = screen.getByTestId(`finding-${first.findingId}`);
    expect(row.getAttribute("data-selected")).toBe("true");

    fireEvent.click(screen.getByTestId(`waive-${first.findingId}`));
    const note = screen.getByTestId(`waive-note-${first.findingId}`);
    fireEvent.change(note, { target: { value: "Accepted for the review" } });
    fireEvent.click(screen.getByTestId(`waive-save-${first.findingId}`));

    expect(setReviewStatus).toHaveBeenCalledWith(
      first.findingId,
      "waived",
      "Accepted for the review",
    );
  });

  it("owns open sections: a closed section does not mount its body", () => {
    render(createElement(BuildAuditView, { model: model() }));

    expect(screen.getByTestId("findings-filter-severity")).toBeTruthy();
    fireEvent.click(screen.getByTestId("findings-section-toggle"));
    expect(screen.queryByTestId("findings-filter-severity")).toBeNull();
    fireEvent.click(screen.getByTestId("findings-section-toggle"));
    expect(screen.getByTestId("findings-filter-severity")).toBeTruthy();
  });

  it("filters findings from view state without rebuilding the model", () => {
    const base = model();
    const findings = base.sections.find(
      (section): section is AuditFindingsSection =>
        section.kind === "findings",
    );
    if (!findings) throw new Error("missing findings");
    const rule = findings.rows[0].rule;
    const matching = findings.rows.filter((row) => row.rule === rule);
    const nonMatching = findings.rows
      .filter((row) => row.rule !== rule)
      .slice(0, 5);

    render(createElement(BuildAuditView, { model: base }));
    fireEvent.click(screen.getByTestId(`rule-${rule}`));

    expect(
      screen.getByTestId(`finding-${matching[0].findingId}`),
    ).toBeTruthy();
    for (const row of nonMatching) {
      expect(screen.queryByTestId(`finding-${row.findingId}`)).toBeNull();
    }
  });
});
