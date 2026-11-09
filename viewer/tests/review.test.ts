import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { buildAudit } from "../lib/audit";
import type { ReviewSidecar } from "../lib/reviewTypes";
import {
  KEY_PREFIX,
  loadReviewQueue,
  queueKey,
  saveReviewQueue,
  setReviewStatus,
  setSemanticDecision,
  summarizeQueue,
} from "../lib/reviewQueue";
import {
  assessSignoff,
  buildRequiredDecisions,
  buildSemanticLedger,
  buildSignoffApproval,
  collectSemanticUnits,
  fnv1a64,
  semanticReviewExport,
  semanticUnitKey,
  shortKey,
  snapshotDigest,
} from "../semantics/model";
import { buildViewerIndex } from "../lib/indexes";
import { loadSnapshotFromObject } from "../lib/load";
import { contractIndex } from "./fixtures";

const openTargetsText = readFileSync(
  new URL("../public/data/opentargets.snapshot.json", import.meta.url),
  "utf8",
);
const openTargetsSnapshot = loadSnapshotFromObject(JSON.parse(openTargetsText));
const openTargetsIndex = buildViewerIndex(openTargetsSnapshot);

const fixtureLedger = buildSemanticLedger(contractIndex);

describe("stable semantic identity", () => {
  it("uses 64-bit FNV-1a for keys and the snapshot digest", () => {
    expect(fnv1a64("")).toBe("cbf29ce484222325");
    expect(fnv1a64("a")).toBe("af63dc4c8601ec8c");

    const key = semanticUnitKey({
      graphName: "fixture_graph",
      subjectPath: "property:node:defect.title",
      kind: "claim",
      text: "The title is the defect's display name.",
    });
    expect(key).toMatch(/^[0-9a-f]{16}$/);
    expect(shortKey(key)).toBe(key.slice(0, 8));

    const same = semanticUnitKey({
      graphName: "fixture_graph",
      subjectPath: "property:node:defect.title",
      kind: "claim",
      text: "The title is the defect's display name.",
    });
    expect(same).toBe(key);

    const framed = semanticUnitKey({
      graphName: "fixture_graph",
      subjectPath: "property:node:defect.title",
      kind: "claim",
      text: "The title is the defect's display name.",
      frameText: "another frame",
    });
    expect(framed).not.toBe(key);

    expect(snapshotDigest(contractIndex.snapshot)).toBe(
      snapshotDigest(contractIndex.snapshot),
    );
    expect(snapshotDigest(contractIndex.snapshot)).toMatch(/^[0-9a-f]{16}$/);
  });
});

describe("semantic ledger", () => {
  it("includes the graph purpose, 9 claims, 5 frames and their limitations", () => {
    const units = collectSemanticUnits(openTargetsIndex);
    const graph = units.filter((unit) => unit.subject.kind === "graph");
    expect(graph.filter((unit) => unit.kind === "purpose")).toHaveLength(1);
    expect(graph.filter((unit) => unit.kind === "claim")).toHaveLength(9);
    expect(graph.filter((unit) => unit.kind === "frame")).toHaveLength(5);
    expect(graph.filter((unit) => unit.kind === "limitation")).toHaveLength(5);

    const ledger = buildSemanticLedger(openTargetsIndex);
    expect(ledger.units).toHaveLength(units.length);
    expect(ledger.unitsByKey.size).toBe(units.length);
    expect(ledger.counts.subjects).toBeGreaterThan(0);
    expect(ledger.counts.units).toBeGreaterThan(graph.length);
  });

  it("collects every attached subject kind exactly once", () => {
    const ledger = buildSemanticLedger(contractIndex);
    const paths = ledger.units.map((unit) => unit.subjectPath);
    expect(paths).toContain("graph:fixture_graph");
    expect(paths).toContain("asset:estate");
    expect(paths).toContain("relation:surveys");
    expect(paths).toContain("projection:defect");
    expect(paths).toContain("struct:reading");
    expect(paths).toContain("field:surveys.title");
    expect(paths).toContain("node:defect");
    expect(paths).toContain("edge:has_observation");
    expect(paths).toContain("property:node:defect.title");
    expect(paths).toContain("binding:0");
    expect(new Set(paths).size).toBe(
      new Set(ledger.units.map((unit) => unit.subjectKey)).size,
    );
    expect(ledger.counts.limitations).toBe(
      ledger.units.filter((unit) => unit.kind === "limitation").length,
    );
  });

  it("groups units by subject and preserves the attached-only rule", () => {
    expect(fixtureLedger.groups.length).toBe(fixtureLedger.counts.subjects);
    const attached = fixtureLedger.units.find(
      (unit) => unit.subjectPath === "property:node:defect.title",
    );
    expect(attached?.attached).toBe(true);
    expect(fixtureLedger.units.find((unit) => unit.kind === "purpose")?.attached).toBe(
      false,
    );
  });
});

describe("required decision policy", () => {
  it("requires every limitation", () => {
    const required = buildRequiredDecisions(
      contractIndex,
      fixtureLedger.units,
    );
    const limitations = required.filter((entry) => entry.reason === "limitation");
    expect(limitations).toHaveLength(fixtureLedger.counts.limitations);
    expect(
      limitations.some((entry) => entry.detail === "It is not production data."),
    ).toBe(true);
  });

  it("requires properties with no traced source and abstract producers", () => {
    const required = fixtureLedger.required;
    expect(
      required.some(
        (entry) =>
          entry.reason === "untraced-property" &&
          entry.subjectPath === "property:node:documented.summary",
      ),
    ).toBe(true);
    expect(
      required.some(
        (entry) =>
          entry.reason === "untraced-property" &&
          entry.subjectPath === "property:edge:has_observation.as_at",
      ),
    ).toBe(true);
    expect(
      required.some(
        (entry) =>
          entry.reason === "abstract-producer" &&
          entry.subjectPath === "node:documented",
      ),
    ).toBe(true);
    expect(
      required.some(
        (entry) =>
          entry.reason === "untraced-property" &&
          entry.subjectPath === "property:node:defect.title",
      ),
    ).toBe(false);
  });

  it("requires identity and type findings reported by the audit", () => {
    const required = buildRequiredDecisions(
      openTargetsIndex,
      collectSemanticUnits(openTargetsIndex),
      openTargetsSnapshot.review,
    );
    const audit = buildAudit(openTargetsIndex, openTargetsSnapshot.review);
    const identityOrType = audit.findings.filter(
      (finding) =>
        /^(identity|type)\./.test(finding.rule) ||
        finding.tags.some((tag) =>
          ["identity", "type", "nullability", "presence", "shape"].includes(tag),
        ),
    );
    if (identityOrType.length) {
      expect(
        required.some((entry) => entry.reason === "identity" || entry.reason === "type"),
      ).toBe(true);
    }
    for (const finding of identityOrType) {
      expect(
        required.some((entry) => entry.findingId === finding.id),
      ).toBe(true);
    }
  });
});

describe("coverage and sign-off", () => {
  it("removes a required item once its decision is resolved", () => {
    const first = fixtureLedger.required[0];
    const local = setSemanticDecision({}, first.key, "accepted", {
      rationale: "Reviewed against the declaration.",
      reviewer: "Fixture reviewer",
    });
    const next = buildSemanticLedger(contractIndex, undefined, local);
    expect(next.coverage.total).toBe(fixtureLedger.coverage.total);
    expect(next.coverage.resolved).toBe(fixtureLedger.coverage.resolved + 1);
    expect(next.coverage.open).toBe(fixtureLedger.coverage.open - 1);
    const entry = next.coverage.required.find((candidate) => candidate.key === first.key);
    expect(entry?.status).toBe("accepted");
    expect(entry?.resolved).toBe(true);
    if (first.unitKey) {
      expect(next.statusByKey.get(first.unitKey)).toBe("accepted");
    }
  });

  it("lists unresolved subjects and exports the ledger as JSON", () => {
    const first = fixtureLedger.required[0];
    const local = setSemanticDecision({}, first.key, "rejected", {
      rationale: "The declaration is wrong.",
      reviewer: "Fixture reviewer",
    });
    const next = buildSemanticLedger(contractIndex, undefined, local);
    expect(next.coverage.subjects.length).toBeGreaterThan(0);
    const exported = JSON.parse(
      JSON.stringify(semanticReviewExport(next, { approvals: [] })),
    );
    expect(exported.format).toBe("kg-viewer-semantic-review");
    expect(exported.snapshot.digest).toBe(next.digest);
    expect(exported.coverage.total).toBe(next.coverage.total);
    expect(exported.coverage.resolved).toBe(next.coverage.resolved);
    expect(exported.units.length).toBe(next.units.length);
  });

  it("blocks sign-off until coverage is empty and a reviewer signs", () => {
    const blocked = assessSignoff(fixtureLedger.coverage, fixtureLedger.digest);
    expect(blocked.ready).toBe(false);
    expect(blocked.blockers).toContain("No reviewer");
    expect(blocked.coverageOpen).toBeGreaterThan(0);

    const empty = {
      required: [],
      total: 0,
      resolved: 0,
      open: 0,
      subjects: [],
    };
    const ready = assessSignoff(empty, fixtureLedger.digest, {
      reviewer: "Reviewer One",
      at: "2026-11-09T12:00:00.000Z",
    });
    expect(ready.ready).toBe(true);
    expect(ready.approved).toBe(false);

    const approval = buildSignoffApproval(
      fixtureLedger.digest,
      empty,
      "Reviewer One",
      "2026-11-09T12:00:00.000Z",
      "All required decisions resolved.",
    );
    expect(approval.scope).toEqual([]);
    const approved = assessSignoff(empty, fixtureLedger.digest, {
      approvals: [approval],
    });
    expect(approved.ready).toBe(true);
    expect(approved.approved).toBe(true);
    expect(approved.approval?.reviewer).toBe("Reviewer One");
  });

  it("becomes ready after every required decision is resolved", () => {
    let local = {};
    for (const entry of fixtureLedger.required) {
      local = setSemanticDecision(local, entry.key, "accepted", {
        rationale: `Resolved ${entry.title}.`,
        reviewer: "Fixture reviewer",
      });
    }
    const resolved = buildSemanticLedger(contractIndex, undefined, local);
    expect(resolved.coverage.open).toBe(0);
    expect(resolved.coverage.resolved).toBe(resolved.coverage.total);
    const readiness = assessSignoff(resolved.coverage, resolved.digest, {
      reviewer: "Fixture reviewer",
      at: "2026-11-09T12:00:00.000Z",
    });
    expect(readiness.ready).toBe(true);
    expect(readiness.blockers).toEqual([]);
  });
});

describe("review sidecar and queue", () => {
  it("round-trips waived decisions and an approval", () => {
    const sidecar: ReviewSidecar = {
      format: "kg-viewer-review",
      version: 1,
      decisions: [
        {
          id: "waive-fixture-purpose",
          title: "The fixture purpose is synthetic",
          status: "waived",
          rationale: "The fixture exists only for contract tests.",
          evidence: [],
          subject: { kind: "graph", name: "fixture_graph" },
          tags: ["fixture"],
        },
      ],
      approvals: [
        {
          id: "approval:fixture",
          scope: [{ kind: "graph", name: "fixture_graph" }],
          digest: fixtureLedger.digest,
          reviewer: "Fixture reviewer",
          at: "2026-11-09T12:00:00.000Z",
          status: "signed-off",
        },
      ],
    };
    const roundTrip = JSON.parse(JSON.stringify(sidecar)) as ReviewSidecar;
    expect(roundTrip).toEqual(sidecar);
    expect(roundTrip.decisions[0].status).toBe("waived");
    expect(roundTrip.approvals?.[0].status).toBe("signed-off");

    const ledger = buildSemanticLedger(contractIndex, sidecar);
    const graphLimitation = ledger.coverage.required.find(
      (entry) => entry.reason === "limitation" && entry.subject.kind === "graph",
    );
    expect(graphLimitation?.resolved).toBe(true);
    expect(graphLimitation?.status).toBe("waived");
  });

  it("requires a rationale for a semantic waiver", () => {
    expect(() => setSemanticDecision({}, "unit:one", "waived")).toThrow(/rationale/i);
    const records = setSemanticDecision({}, "unit:one", "waived", {
      rationale: "Accepted as a documented limit.",
      reviewer: "Reviewer One",
      at: "2026-11-09T12:00:00.000Z",
    });
    expect(records["unit:one"]).toMatchObject({
      key: "unit:one",
      status: "waived",
      rationale: "Accepted as a documented limit.",
      reviewer: "Reviewer One",
    });
  });

  it("keeps the audit review queue contract and SSR behaviour", () => {
    const audit = buildAudit(contractIndex, undefined);
    const first = audit.findings[0];
    if (first) {
      const records = setReviewStatus({}, first.id, "acknowledged");
      expect(summarizeQueue(audit, records).acknowledged).toBe(1);
      expect(() => setReviewStatus(records, first.id, "waived")).toThrow(/note/i);
    }
    expect(queueKey("fixture-estate")).toBe(`${KEY_PREFIX}fixture-estate`);
    expect(loadReviewQueue("fixture-estate")).toEqual({});
    expect(() => saveReviewQueue("fixture-estate", {})).not.toThrow();
  });
});
