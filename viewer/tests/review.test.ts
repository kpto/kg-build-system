import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { buildAudit } from "../lib/audit";
import { buildCoverage } from "../lib/coverage";
import { decisionCoverage, deriveDecisions } from "../lib/decisions";
import { diffSnapshots, hasChanges } from "../lib/diff";
import { buildDossierJson, buildDossierMarkdown } from "../lib/dossier";
import { computeImpact } from "../lib/impact";
import { buildLineage, propertySelection } from "../lib/lineage";
import {
  loadReviewSidecar,
  loadSnapshotFromObject,
  normalizeReviewSidecar,
} from "../lib/load";
import {
  KEY_PREFIX,
  loadReviewQueue,
  queueKey,
  saveReviewQueue,
  setReviewStatus,
  summarizeQueue,
} from "../lib/reviewQueue";
import {
  formatReviewUrlState,
  parseReviewUrlState,
  readUrlState,
} from "../lib/urlState";
import type { ReviewUrlState } from "../lib/urlState";
import { index, snapshot } from "./fixtures";

const reviewText = readFileSync(
  new URL("../public/data/reference.review.json", import.meta.url),
  "utf8",
);

function referenceReview() {
  const review = normalizeReviewSidecar(JSON.parse(reviewText));
  if (!review) throw new Error("reference review sidecar did not normalise");
  return review;
}

const review = referenceReview();
const audit = buildAudit(index, review);
const decisions = deriveDecisions(index, review);

function cloneSnapshot() {
  return loadSnapshotFromObject(JSON.parse(JSON.stringify(snapshot)));
}

describe("coverage matrix", () => {
  it("traces defect.condition_rating to the surveys relation", () => {
    const coverage = buildCoverage(index);
    const row = coverage.rows.find(
      (candidate) =>
        candidate.component === "defect" &&
        candidate.property === "condition_rating",
    );
    expect(row).toBeDefined();
    expect(row?.kind).toBe("node");
    expect(row?.sourceRelations).toEqual(["surveys"]);
    expect(row?.cells).toEqual([
      { source: "surveys", fields: 1, literals: 1, bindings: 1 },
    ]);
    expect(row?.tracedFields).toBe(1);
    expect(row?.steps).toEqual([["core", "binding.0"]]);
    expect(coverage.sources).toContain("surveys");
  });

  it("keeps literal-only rows with zero source columns", () => {
    const coverage = buildCoverage(index);
    const row = coverage.rows.find(
      (candidate) =>
        candidate.component === "defect" &&
        candidate.property === "source_version",
    );
    expect(row).toBeDefined();
    expect(row?.sourceRelations).toEqual([]);
    expect(row?.cells).toEqual([]);
    expect(row?.literals).toBeGreaterThan(0);
    expect(row?.steps).toEqual([["core", "binding.0"]]);
  });

  it("sorts rows and sources deterministically", () => {
    const first = buildCoverage(index);
    const second = buildCoverage(index);
    expect(first).toEqual(second);
    expect(first.sources).toEqual([...first.sources].sort());
    const keys = first.rows.map(
      (row) => `${row.kind}:${row.component}.${row.property}`,
    );
    expect(keys).toEqual([...keys].sort());
  });
});

describe("impact radius", () => {
  it("includes the full defect.condition_rating chain", () => {
    const impact = computeImpact(index, {
      kind: "property",
      name: "defect",
      component: "defect",
      property: "condition_rating",
      entityKind: "node",
    });
    const steps = [...impact.upstream, ...impact.downstream];
    expect(steps).toEqual(
      expect.arrayContaining([
        ["duckdb", "source.surveys"],
        ["core", "projection.defect"],
        ["core", "binding.0"],
        ["core", "aggregate.defect"],
        ["deduplication", "defect"],
        ["file", "write"],
        ["meta_graph", "document"],
      ]),
    );
    expect(
      steps.some(
        (step) =>
          step[0] === "neo4j" && step[1].startsWith("export.node.defect"),
      ),
    ).toBe(true);
    expect(impact.targets).toEqual(["file", "meta_graph", "neo4j"]);
    expect(impact.nodes).toEqual(["defect"]);
    expect(impact.records).toBe(3);
  });

  it("unions property impacts for a node subject", () => {
    const impact = computeImpact(index, {
      kind: "node",
      name: "defect",
      component: "defect",
      entityKind: "node",
    });
    expect(impact.upstream).toEqual(
      expect.arrayContaining([["core", "binding.0"]]),
    );
    expect(impact.nodes).toEqual(["defect"]);
    expect(impact.records).toBe(3);
  });
});

describe("decision ledger", () => {
  it("keeps sidecar decisions first and adds derived cards", () => {
    const sidecar = decisions.filter((decision) => decision.source === "sidecar");
    expect(sidecar).toHaveLength(review.decisions.length);
    expect(sidecar.map((decision) => decision.id)).toEqual(
      review.decisions.map((decision) => decision.id),
    );
    expect(sidecar.every((decision) => decision.rationaleSupplied)).toBe(true);

    const derived = decisions.filter((decision) => decision.source === "derived");
    expect(derived.length).toBeGreaterThan(0);
    expect(derived.some((decision) => decision.id === "derived:asset:estate")).toBe(
      true,
    );
    expect(decisions.some((decision) => !decision.rationaleSupplied)).toBe(true);

    const coverage = decisionCoverage(decisions);
    expect(coverage.total).toBe(decisions.length);
    expect(coverage.sidecar).toBe(review.decisions.length);
    expect(coverage.derived).toBe(derived.length);
    expect(coverage.rationaleSupplied + coverage.rationaleMissing).toBe(
      coverage.total,
    );
  });

  it("turns every open sidecar decision into a question", () => {
    const open = review.decisions.filter((decision) => decision.status === "open");
    expect(open.length).toBeGreaterThan(0);
    for (const decision of open) {
      expect(
        audit.questions.some(
          (finding) =>
            finding.rule === "open-decision" &&
            finding.question?.includes(decision.title),
        ),
      ).toBe(true);
    }
  });
});

describe("snapshot diff", () => {
  it("returns an empty diff for an identical snapshot", () => {
    const diff = diffSnapshots(snapshot, snapshot);
    expect(hasChanges(diff)).toBe(false);
    expect(diff.summary).toEqual({
      stepsAdded: 0,
      stepsRemoved: 0,
      connectionsAdded: 0,
      connectionsRemoved: 0,
      nodesAdded: 0,
      nodesRemoved: 0,
      edgesAdded: 0,
      edgesRemoved: 0,
      bindingsAdded: 0,
      bindingsRemoved: 0,
      propertiesChanged: 0,
    });
    expect(diff.steps).toEqual({ added: [], removed: [], changed: [] });
  });

  it("detects an added workflow step", () => {
    const next = cloneSnapshot();
    next.workflow.steps.push({
      id: ["x", "added"],
      instruction: { kind: ["sql", "duckdb"], payload: {} },
      outputs: [{ opening_name: ["output"], type: ["x", "thing"] }],
    });

    const diff = diffSnapshots(snapshot, next);
    expect(diff.summary.stepsAdded).toBe(1);
    expect(diff.steps.added).toEqual([["x", "added"]]);
    expect(hasChanges(diff)).toBe(true);
  });

  it("detects a changed binding property without reordering arrays", () => {
    const next = cloneSnapshot();
    const properties = next.blueprint.bindings[0]?.properties;
    expect(properties).toBeDefined();
    if (properties) {
      properties.condition_rating = { kind: "literal", value: "Changed" };
    }

    const diff = diffSnapshots(snapshot, next);
    expect(diff.bindings.changed).toContain(0);
    expect(diff.summary.propertiesChanged).toBeGreaterThan(0);
    expect(diff.bindings.changed).toEqual(
      [...diff.bindings.changed].sort((left, right) => left - right),
    );
  });
});

describe("review queue", () => {
  it("refuses a waiver without a note", () => {
    const records = {
      "finding:one": { findingId: "finding:one", status: "open" as const },
    };
    expect(() => setReviewStatus(records, "finding:one", "waived")).toThrow(
      /note/i,
    );
    expect(() =>
      setReviewStatus(records, "finding:one", "waived", "   "),
    ).toThrow(/note/i);

    const waived = setReviewStatus(
      records,
      "finding:one",
      "waived",
      "accepted by the reviewer",
    );
    expect(waived["finding:one"].status).toBe("waived");
    expect(waived["finding:one"].note).toBe("accepted by the reviewer");
    expect(records["finding:one"].status).toBe("open");
  });

  it("summarizes progress against the audit findings", () => {
    const first = audit.findings[0];
    const second = audit.findings[1];
    const records = setReviewStatus(
      setReviewStatus({}, first.id, "acknowledged"),
      second.id,
      "waived",
      "reviewed deliberately",
    );
    const summary = summarizeQueue(audit, records);
    expect(summary.total).toBe(audit.findings.length);
    expect(summary.acknowledged).toBe(1);
    expect(summary.waived).toBe(1);
    expect(summary.resolved).toBe(0);
    expect(summary.open).toBe(audit.findings.length - 2);
  });

  it("is inert when no browser storage is available", () => {
    expect(queueKey("reference-estate")).toBe(
      `${KEY_PREFIX}reference-estate`,
    );
    expect(loadReviewQueue("reference-estate")).toEqual({});
    expect(() => saveReviewQueue("reference-estate", {})).not.toThrow();
  });
});

describe("review dossier", () => {
  it("includes the required Markdown sections and finding ids", () => {
    const selection = propertySelection("node", "defect", "condition_rating");
    const lineage = buildLineage(index, selection);
    const markdown = buildDossierMarkdown({
      index,
      audit,
      decisions,
      queue: setReviewStatus({}, audit.findings[0].id, "acknowledged"),
      selection,
      lineage,
    });

    expect(markdown).toContain("## Audit findings");
    expect(markdown).toContain("## Design questions");
    expect(markdown).toContain("## Decision ledger");
    expect(markdown).toContain("## Build health");
    expect(markdown).toContain("## Selected property receipt");
    expect(markdown).toContain("defect.condition_rating");
    expect(markdown).toContain(audit.findings[0].id);
    expect(markdown).toContain("Findings are deterministic observations");
    expect(markdown).toContain("Unrated");
  });

  it("produces valid JSON with the selected impact", () => {
    const selection = propertySelection("node", "defect", "condition_rating");
    const parsed = JSON.parse(
      buildDossierJson({
        index,
        audit,
        decisions,
        queue: {},
        selection,
      }),
    );
    expect(parsed.format).toBe("kg-viewer-dossier");
    expect(parsed.version).toBe(1);
    expect(parsed.snapshot.name).toBe(snapshot.name);
    expect(parsed.health.value).toBe(audit.score.value);
    expect(parsed.findings.length).toBe(audit.findings.length);
    expect(parsed.impact.records).toBe(3);
    expect(parsed.impact.upstream).toEqual(
      expect.arrayContaining([["core", "binding.0"]]),
    );
  });
});

describe("URL state", () => {
  it("round trips known state and preserves unknown parameters", () => {
    const state = parseReviewUrlState(
      "?view=lineage&kind=node&component=defect&property=condition_rating&source=surveys&step=core,binding.0&finding=f1&embed=1&debug=true",
    );
    expect(state.view).toBe("lineage");
    expect(state.kind).toBe("node");
    expect(state.component).toBe("defect");
    expect(state.property).toBe("condition_rating");
    expect(state.source).toBe("surveys");
    expect(state.step).toEqual(["core", "binding.0"]);
    expect(state.finding).toBe("f1");
    expect(state.params).toEqual({ embed: "1", debug: "true" });

    const roundTrip = parseReviewUrlState(`?${formatReviewUrlState(state)}`);
    expect(roundTrip).toEqual(state);
  });

  it("round trips an edge/source filter and rejects an invalid kind as state", () => {
    const state: ReviewUrlState = {
      view: "review",
      kind: "edge",
      component: "measures",
      property: "as_at",
      source: "temperature",
      params: {},
    };
    const formatted = formatReviewUrlState(state);
    expect(formatted).toContain("kind=edge");
    expect(formatted).toContain("source=temperature");
    expect(parseReviewUrlState(`?${formatted}`)).toEqual(state);

    const invalid = parseReviewUrlState("?view=review&kind=property&source=surveys");
    expect(invalid.kind).toBeUndefined();
    expect(invalid.source).toBe("surveys");
    expect(invalid.params).toEqual({});
  });

  it("defaults an unknown view and is safe without a window", () => {
    expect(parseReviewUrlState("?view=unknown").view).toBe("map");
    expect(readUrlState().view).toBe("map");
    expect(readUrlState().params).toEqual({});
  });
});

describe("review sidecar loading", () => {
  it("loads and validates the bundled sidecar without failing", async () => {
    const original = globalThis.fetch;
    try {
      globalThis.fetch = (async () =>
        new Response(reviewText, { status: 200 })) as typeof fetch;
      const loaded = await loadReviewSidecar();
      expect(loaded?.format).toBe("kg-viewer-review");
      expect(loaded?.decisions).toHaveLength(review.decisions.length);

      globalThis.fetch = (async () =>
        new Response("missing", { status: 404 })) as typeof fetch;
      expect(await loadReviewSidecar()).toBeUndefined();
    } finally {
      globalThis.fetch = original;
    }
  });

  it("drops malformed sidecars instead of throwing", () => {
    expect(normalizeReviewSidecar({ format: "other" })).toBeUndefined();
    expect(normalizeReviewSidecar(JSON.parse('{"format":"kg-viewer-review"}'))).toEqual({
      format: "kg-viewer-review",
      version: 1,
      decisions: [],
    });
  });
});
