import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import { buildAudit } from "@/lib/audit";
import { buildCoverage } from "@/lib/coverage";
import { deriveDecisions } from "@/lib/decisions";
import { normalizeReviewSidecar } from "@/lib/load";
import { summarizeQueue } from "@/lib/reviewQueue";
import type {
  CampaignCommands,
  CampaignRecord,
  CampaignView,
} from "@/shared/model/campaign";
import {
  buildAuditModel,
  type AuditCoverageSection,
  type AuditDecisionsSection,
  type AuditDiffSection,
  type AuditDossierSection,
  type AuditFindingsSection,
  type AuditQuestionsSection,
  type AuditSummarySection,
} from "@/audit/model/AuditModel";
import { index, snapshot } from "./fixtures";

const review = (() => {
  const value = normalizeReviewSidecar(
    JSON.parse(
      readFileSync(
        new URL("../public/data/reference.review.json", import.meta.url),
        "utf8",
      ),
    ),
  );
  if (!value) throw new Error("reference review sidecar did not normalise");
  return value;
})();

const audit = buildAudit(index, review);
const coverage = buildCoverage(index);
const decisions = deriveDecisions(index, review);
const queueSummary = summarizeQueue(audit, {});

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

function section<T extends { kind: string }>(
  model: ReturnType<typeof buildAuditModel>,
  kind: T["kind"],
): T {
  const found = model.sections.find((candidate) => candidate.kind === kind);
  if (!found) throw new Error(`missing ${kind} section`);
  return found as unknown as T;
}

describe("audit model", () => {
  it("exposes the panel header and the eight-question rail", () => {
    const model = buildAuditModel(campaign, {
      onClearSubjectFilter: noop,
    });

    expect(model.panel.title).toBe("Audit");
    expect(model.panel.meta).toContain("findings");
    expect(model.rails.map((rail) => rail.label)).toEqual([
      "Summary",
      "Findings",
      "Questions",
      "Coverage",
      "Decisions",
      "Build",
      "Diff",
      "Dossier",
    ]);
    expect(model.rails.every((rail) => rail.question.length > 0)).toBe(true);
    expect(model.rails.map((rail) => rail.testId)).toEqual([
      "review-rail-summary",
      "review-rail-findings",
      "review-rail-questions",
      "review-rail-coverage",
      "review-rail-decisions",
      "review-rail-build",
      "review-rail-diff",
      "review-rail-dossier",
    ]);
    expect(model.sections.map((entry) => entry.testId)).toEqual([
      "review-summary",
      "findings-panel",
      "design-questions",
      "coverage-matrix",
      "decision-ledger",
      "build-health",
      "snapshot-diff",
      "dossier-panel",
    ]);
  });

  it("builds score, rubric, verification, legend and queue evidence", () => {
    const model = buildAuditModel(campaign, {
      onClearSubjectFilter: noop,
    });
    const summary = section<AuditSummarySection>(model, "summary");

    expect(summary.score).toBe(audit.score.value);
    expect(summary.components.map((row) => row.testId)).toEqual(
      audit.score.components.map((component) => `rubric-${component.id}`),
    );
    expect(summary.verification.label.length).toBeGreaterThan(0);
    expect(summary.legend.map((entry) => entry.testId)).toEqual([
      "severity-critical",
      "severity-high",
      "severity-medium",
      "severity-low",
      "severity-info",
    ]);
    expect(summary.queue.total).toBe(audit.findings.length);
  });

  it("keeps finding test ids and binds acknowledge and waive", () => {
    const setReviewStatus = vi.fn();
    const interactive: CampaignView = {
      ...campaign,
      commands: { ...commands, setReviewStatus },
    };
    const model = buildAuditModel(interactive, {
      onClearSubjectFilter: noop,
    });
    const findings = section<AuditFindingsSection>(model, "findings");

    expect(findings.rows.length).toBeGreaterThan(0);
    for (const row of findings.rows) {
      expect(row.testId).toBe(`finding-${row.findingId}`);
      expect(row.acknowledge.testId).toBe(`ack-${row.findingId}`);
      expect(row.waive.testId).toBe(`waive-${row.findingId}`);
      expect(row.waive.kind).toBe("waive");
    }

    const first = findings.rows[0];
    first.acknowledge.run?.();
    expect(setReviewStatus).toHaveBeenCalledWith(first.findingId, "acknowledged");
  });

  it("marks the selected finding without exposing a view", () => {
    const base = buildAuditModel(campaign, {
      onClearSubjectFilter: noop,
    });
    const findings = section<AuditFindingsSection>(base, "findings");
    const selectedFindingId = findings.rows[0].findingId;
    const model = buildAuditModel(campaign, {
      selectedFindingId,
      onClearSubjectFilter: noop,
    });
    const selected = section<AuditFindingsSection>(model, "findings");

    expect(model.selectedFindingId).toBe(selectedFindingId);
    expect(selected.rows.filter((row) => row.selected)).toHaveLength(1);
    expect(selected.rows.find((row) => row.selected)?.findingId).toBe(
      selectedFindingId,
    );
  });

  it("filters findings and questions by the campaign subject", () => {
    const base = buildAuditModel(campaign, {
      onClearSubjectFilter: noop,
    });
    const baseFindings = section<AuditFindingsSection>(base, "findings");
    const subject = baseFindings.rows.find((row) => row.subject)?.subject;
    if (!subject) throw new Error("reference audit has no subject");

    const model = buildAuditModel(campaign, {
      subjectFilter: subject,
      onClearSubjectFilter: noop,
    });
    const findings = section<AuditFindingsSection>(model, "findings");
    const questions = section<AuditQuestionsSection>(model, "questions");

    expect(model.subject.subject).toEqual(subject);
    expect(model.subject.clear?.testId).toBe("clear-subject-filter");
    expect(findings.rows.length).toBeLessThanOrEqual(baseFindings.rows.length);
    expect(findings.rows.every((row) => row.subject)).toBe(true);
    expect(questions.rows.every((row) => row.subject)).toBe(true);
  });

  it("exposes coverage cells, decisions and their stable test ids", () => {
    const model = buildAuditModel(campaign, {
      onClearSubjectFilter: noop,
    });
    const coverageSection = section<AuditCoverageSection>(model, "coverage");
    const decisionSection = section<AuditDecisionsSection>(model, "decisions");

    if (coverageSection.rows[0]?.cells[0]) {
      const cell = coverageSection.rows[0].cells[0];
      expect(cell.open.testId).toBe(
        `coverage-cell-${coverageSection.rows[0].component}-${coverageSection.rows[0].property}-${cell.source}`,
      );
    }
    expect(decisionSection.counts.sidecar + decisionSection.counts.derived).toBe(
      decisions.length,
    );
    expect(decisionSection.showAll.testId).toBe("decision-show-all");
    expect(decisionSection.showLess.testId).toBe("decision-show-less");
  });

  it("binds the diff and dossier actions", () => {
    const model = buildAuditModel(campaign, {
      onClearSubjectFilter: noop,
    });
    const diff = section<AuditDiffSection>(model, "diff");
    const dossier = section<AuditDossierSection>(model, "dossier");

    expect(diff.pin.testId).toBe("pin-baseline");
    expect(diff.clear.testId).toBe("clear-baseline");
    expect(diff.compare.testId).toBe("compare-input");
    expect(diff.compare.kind).toBe("compare");
    expect(dossier.actions.map((action) => action.testId)).toEqual([
      "dossier-export-markdown",
      "dossier-export-json",
      "dossier-copy-markdown",
      "dossier-copy-json",
    ]);
    expect(dossier.count).toBe("4 outputs");
  });
});
