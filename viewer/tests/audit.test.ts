import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { buildAudit } from "../lib/audit";
import { buildViewerIndex } from "../lib/indexes";
import { loadSnapshotFromObject, normalizeReviewSidecar } from "../lib/load";
import { index } from "./fixtures";

function referenceReview() {
  const review = normalizeReviewSidecar(
    JSON.parse(
      readFileSync(
        new URL("../public/data/reference.review.json", import.meta.url),
        "utf8",
      ),
    ),
  );
  if (!review) throw new Error("reference review sidecar did not normalise");
  return review;
}

const review = referenceReview();
const audit = buildAudit(index, review);

function findingsFor(rule: string) {
  return audit.findings.filter((finding) => finding.rule === rule);
}

describe("audit engine", () => {
  it("is deterministic and exposes a transparent weighted rubric", () => {
    expect(buildAudit(index, review)).toEqual(audit);
    expect(audit.score.value).toBeGreaterThanOrEqual(0);
    expect(audit.score.value).toBeLessThanOrEqual(100);

    const ids = audit.score.components.map((component) => component.id);
    expect(ids).toEqual([
      "traceability",
      "documentation",
      "determinism",
      "verification",
      "cohesion",
    ]);
    for (const component of audit.score.components) {
      expect(component.value).toBeGreaterThanOrEqual(0);
      expect(component.value).toBeLessThanOrEqual(100);
      expect(component.weight).toBeGreaterThan(0);
      expect(component.detail.length).toBeGreaterThan(0);
    }
    const weight = audit.score.components.reduce(
      (total, component) => total + component.weight,
      0,
    );
    expect(weight).toBeCloseTo(1);

    const counted = Object.values(audit.counts).reduce(
      (total, value) => total + value,
      0,
    );
    expect(counted).toBe(audit.findings.length);
    expect(new Set(audit.findings.map((finding) => finding.id)).size).toBe(
      audit.findings.length,
    );
    for (const finding of audit.findings) {
      expect(finding.id).toMatch(/^finding:[a-z-]+:[0-9a-f]{8}$/);
      expect(finding.evidence.length).toBeGreaterThan(0);
    }
  });

  it("reports the two reference multi-source components with binding evidence", () => {
    const multiSource = findingsFor("multi-source-component");
    const reading = multiSource.find((finding) => finding.subject?.name === "reading");
    const measures = multiSource.find((finding) => finding.subject?.name === "measures");

    expect(reading).toBeDefined();
    expect(reading?.evidence.map((entry) => entry.jsonPointer)).toEqual(
      expect.arrayContaining(["/bindings/4", "/bindings/5"]),
    );
    expect(reading?.question).toContain("intentionally one entity");

    expect(measures).toBeDefined();
    expect(measures?.subject?.kind).toBe("edge");
    expect(measures?.evidence.map((entry) => entry.jsonPointer)).toEqual(
      expect.arrayContaining(["/bindings/12", "/bindings/13"]),
    );
  });

  it("reports hard-coded fallback with the literal value Unrated", () => {
    const finding = findingsFor("hard-coded-fallback").find(
      (candidate) =>
        candidate.subject?.component === "defect" &&
        candidate.subject.property === "condition_rating",
    );
    expect(finding).toBeDefined();
    expect(`${finding?.title} ${finding?.detail}`).toContain("Unrated");
    expect(finding?.evidence[0].jsonPointer).toBe(
      "/bindings/0/properties/condition_rating",
    );
    expect(finding?.question).toContain("Unrated");
  });

  it("aggregates fallbacks by property across multi-source bindings", () => {
    const summaryFindings = findingsFor("hard-coded-fallback").filter(
      (finding) =>
        finding.subject?.component === "reading" &&
        finding.subject.property === "summary",
    );
    expect(summaryFindings).toHaveLength(1);

    const summary = summaryFindings[0];
    expect(summary.evidence).toHaveLength(2);
    expect(summary.evidence.map((entry) => entry.jsonPointer)).toEqual([
      "/bindings/4/properties/summary",
      "/bindings/5/properties/summary",
    ]);
    expect(summary.subject?.bindingIndex).toBeUndefined();
    expect(summary.title).toContain("Unidentified sample");

    const condition = findingsFor("hard-coded-fallback").find(
      (finding) =>
        finding.subject?.component === "defect" &&
        finding.subject.property === "condition_rating",
    );
    expect(condition?.subject?.bindingIndex).toBe(0);
    expect(`${condition?.title} ${condition?.detail}`).toContain("Unrated");
  });

  it("does not classify the defect identity as nullable", () => {
    const nullable = findingsFor("nullable-identity");
    expect(nullable).toHaveLength(0);
    expect(
      nullable.some(
        (finding) =>
          finding.subject?.component === "defect" ||
          finding.subject?.name === "defect",
      ),
    ).toBe(false);
  });

  it("reports no build failures for the reference report", () => {
    expect(findingsFor("build-failure")).toHaveLength(0);
    expect(findingsFor("recovered-failure")).toHaveLength(0);
  });

  it("keeps questions exactly equal to findings that carry one", () => {
    expect(audit.questions).toEqual(
      audit.findings.filter((finding) => Boolean(finding.question)),
    );
    const questionRules = new Set(audit.questions.map((finding) => finding.rule));
    expect(questionRules).toEqual(
      new Set(["multi-source-component", "hard-coded-fallback", "open-decision"]),
    );
  });

  it("turns every open sidecar decision into a review question", () => {
    const open = review.decisions.filter((decision) => decision.status === "open");
    expect(open.length).toBeGreaterThan(0);
    for (const decision of open) {
      const question = audit.questions.find(
        (finding) =>
          finding.rule === "open-decision" &&
          finding.subject?.name === decision.subject?.name &&
          finding.question?.includes(decision.title),
      );
      expect(question).toBeDefined();
      expect(question?.evidence).toEqual(decision.evidence);
    }
  });

  it("covers literal-only properties, documentation and runtime contracts", () => {
    const literal = findingsFor("literal-only-property").find(
      (finding) =>
        finding.subject?.component === "defect" &&
        finding.subject.property === "source_version",
    );
    expect(literal).toBeDefined();

    const undocumented = findingsFor("missing-description").find(
      (finding) => finding.subject?.kind === "relation",
    );
    expect(undocumented).toBeDefined();

    const runtime = findingsFor("runtime-contract").map(
      (finding) => finding.subject?.component,
    );
    expect(runtime).toEqual(expect.arrayContaining(["file", "neo4j"]));
  });

  it("implements rules the reference snapshot does not exercise", () => {
    const synthetic = loadSnapshotFromObject({
      format: "kg-viewer-snapshot",
      version: 1,
      name: "synthetic",
      title: "Synthetic audit fixture",
      blueprint: {
        graph: {
          nodes: [
            {
              name: "A",
              description: "bound node",
              properties: [
                {
                  name: "p",
                  ref: ["topology", "property", "A.p"],
                  logical_type: { kind: "unit", name: "str" },
                  description: "a property",
                },
              ],
            },
            {
              name: "Unbound",
              description: "unbound node",
              properties: [
                {
                  name: "q",
                  ref: ["topology", "property", "Unbound.q"],
                  logical_type: { kind: "unit", name: "str" },
                  description: "an unbound property",
                },
              ],
            },
          ],
          edges: [
            {
              name: "E",
              description: "edge",
              source: ["topology", "node", "A"],
              target: ["topology", "node", "A"],
              properties: [
                {
                  name: "p",
                  ref: ["topology", "property", "E.p"],
                  logical_type: { kind: "unit", name: "str" },
                  description: "edge property",
                },
              ],
            },
          ],
        },
        data: {
          relations: [
            {
              name: "r",
              asset: ["asset", "asset", "usedAsset"],
              columns: [
                {
                  name: "x",
                  ref: ["data", "field", "r.x"],
                  logical_type: { kind: "unit", name: "str" },
                },
              ],
            },
            {
              name: "unusedRelation",
              asset: ["asset", "asset", "usedAsset"],
              columns: [],
            },
          ],
          projections: [],
          structs: [],
        },
        assets: [
          { name: "usedAsset", annotations: [{ namespace: "test", id: "used" }] },
          { name: "unusedAsset" },
        ],
        bindings: [
          {
            kind: "node",
            node: ["topology", "node", "A"],
            identity: {
              kind: "field",
              field: ["data", "field", "r.x"],
              logical_type: { kind: "nullable", value: { kind: "unit", name: "str" } },
            },
            properties: {
              p: {
                kind: "field",
                field: ["data", "field", "r.x"],
                logical_type: { kind: "unit", name: "str" },
              },
            },
            rows: { kind: "scan", relation: ["data", "relation", "r"] },
          },
          {
            kind: "node",
            node: ["topology", "node", "A"],
            identity: {
              kind: "field",
              field: ["data", "field", "r.x"],
              logical_type: { kind: "nullable", value: { kind: "unit", name: "str" } },
            },
            properties: {
              p: {
                kind: "field",
                field: ["data", "field", "r.x"],
                logical_type: { kind: "unit", name: "str" },
              },
            },
            rows: { kind: "scan", relation: ["data", "relation", "r"] },
          },
          {
            kind: "edge",
            edge: ["topology", "edge", "E"],
            identity: {
              kind: "operation",
              operator: ["expressions", "operation", "drop_null"],
              arguments: [
                {
                  kind: "field",
                  field: ["data", "field", "r.x"],
                  logical_type: { kind: "nullable", value: { kind: "unit", name: "str" } },
                },
              ],
              logical_type: { kind: "unit", name: "str" },
            },
            source_identity: {
              kind: "field",
              field: ["data", "field", "r.x"],
              logical_type: { kind: "nullable", value: { kind: "unit", name: "str" } },
            },
            target_identity: {
              kind: "field",
              field: ["data", "field", "r.x"],
              logical_type: { kind: "nullable", value: { kind: "unit", name: "str" } },
            },
            properties: {
              p: {
                kind: "field",
                field: ["data", "field", "r.x"],
                logical_type: { kind: "unit", name: "str" },
              },
            },
            rows: { kind: "scan", relation: ["data", "relation", "r"] },
          },
        ],
      },
      workflow: {
        components: [{ id: "x", version: "2" }],
        steps: [
          {
            id: ["x", "orphan"],
            instruction: { kind: ["sql", "duckdb"], payload: {} },
            outputs: [{ opening_name: ["output"], type: ["x", "thing"] }],
          },
        ],
        connections: [],
      },
      report: {
        published_artifacts: [],
        recovered_failures: [{ message: "recovered one" }],
        unresolved_failures: [{ message: "unresolved one" }],
        provenance: { component_versions: { x: "1" } },
      },
      metaGraph: {
        nodes: [
          {
            name: "A",
            kind: "node",
            properties: [
              { name: "p", nullable: true, type: "str | None" },
            ],
          },
        ],
        edges: [],
      },
    });

    const syntheticAudit = buildAudit(buildViewerIndex(synthetic));
    const rules = new Set(syntheticAudit.findings.map((finding) => finding.rule));

    expect([...rules]).toEqual(
      expect.arrayContaining([
        "duplicate-target",
        "nullable-identity",
        "shared-nullable-key",
        "unused-relation",
        "unused-asset",
        "orphan-step",
        "unconsumed-output",
        "build-failure",
        "recovered-failure",
        "unreachable-lineage",
        "observe-vs-declare",
        "version-drift",
      ]),
    );
    expect(syntheticAudit.counts.critical).toBe(1);
    expect(syntheticAudit.score.value).toBeGreaterThanOrEqual(0);
    expect(syntheticAudit.score.value).toBeLessThanOrEqual(100);
  });
});
