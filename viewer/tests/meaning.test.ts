import { describe, expect, it } from "vitest";

import {
  buildMeaningModel,
  filterMeaningSubjects,
  MEANING_KIND_LABELS,
  visibleFrameLimitations,
} from "@/meaning/MeaningModel";
import { contractIndex } from "./fixtures";

const model = buildMeaningModel(contractIndex);

describe("meaning model", () => {
  it("exposes the graph purpose, claims, frames and limitations", () => {
    expect(model.graph.name).toBe("fixture_graph");
    expect(model.graph.description).toBe(
      "A small graph used by the viewer contract tests.",
    );
    expect(model.graph.purpose).toBe(
      "Exercise the viewer data contract without loading a release.",
    );

    expect(model.graph.claims.map((claim) => claim.text)).toEqual([
      "The fixture graph contains one observed estate.",
    ]);
    expect(model.graph.frames.map((frame) => frame.text)).toEqual([
      "The fixture is synthetic.",
      "Only one asset is represented.",
    ]);
    expect(
      model.graph.frames.map((frame) =>
        frame.limitations.map((limitation) => limitation.text),
      ),
    ).toEqual([
      ["It is not production data."],
      ["No cross-asset joins are exercised."],
    ]);
    expect(model.graph.counts).toEqual({
      claims: 1,
      frames: 2,
      limitations: 2,
      units: 5,
    });
  });

  it("groups attached semantics by subject kind in canonical order", () => {
    expect(model.groups.map((group) => group.kind)).toEqual([
      "asset",
      "relation",
      "projection",
      "struct",
      "field",
      "node",
      "edge",
      "property",
      "binding",
    ]);
    expect(model.subjects.some((subject) => subject.kind === "graph")).toBe(
      false,
    );
    expect(model.subjectCount).toBe(model.subjects.length);
    expect(
      model.subjects.every(
        (subject) => subject.counts.units > 0 || Boolean(subject.profile),
      ),
    ).toBe(true);
  });

  it("filters the subject browser by text and by kind", () => {
    const searched = filterMeaningSubjects(model.groups, { query: "survey" });
    const paths = searched.flatMap((group) =>
      group.subjects.map((subject) => subject.path),
    );
    expect(paths).toContain("relation/surveys");
    expect(paths).toContain("surveys.title");
    expect(paths.every((path) => path.toLowerCase().includes("survey"))).toBe(
      true,
    );

    const assets = filterMeaningSubjects(model.groups, { kinds: ["asset"] });
    expect(assets).toHaveLength(1);
    expect(assets[0].kind).toBe("asset");
    expect(assets[0].label).toBe(MEANING_KIND_LABELS.asset);
    expect(assets[0].subjects.map((subject) => subject.path)).toEqual([
      "asset/estate",
    ]);

    const everything = filterMeaningSubjects(model.groups, { kinds: [] });
    expect(everything.map((group) => group.kind)).toEqual(
      model.groups.map((group) => group.kind),
    );
    expect(filterMeaningSubjects(model.groups, { query: "no such subject" })).toEqual(
      [],
    );
  });

  it("reveals limitations only when a frame is expanded", () => {
    const frame = model.graph.frames[0];
    expect(frame.limitations).toHaveLength(1);
    expect(visibleFrameLimitations(frame, false)).toEqual([]);
    expect(visibleFrameLimitations(frame, true)).toEqual(frame.limitations);

    const asset = model.groups.find((group) => group.kind === "asset");
    const assetFrame = asset?.subjects[0]?.frames[0];
    expect(assetFrame?.limitations).toHaveLength(1);
    expect(visibleFrameLimitations(assetFrame!, false)).toEqual([]);
    expect(visibleFrameLimitations(assetFrame!, true)).toHaveLength(1);
  });

  it("carries no review, decision or audit field", () => {
    const forbidden = [
      "review",
      "decision",
      "decisions",
      "status",
      "signoff",
      "audit",
      "ledger",
      "required",
      "approved",
      "open",
    ];

    expect(Object.keys(model).filter((key) => forbidden.includes(key))).toEqual(
      [],
    );
    for (const subject of model.subjects) {
      expect(
        Object.keys(subject).filter((key) => forbidden.includes(key)),
      ).toEqual([]);
    }
    expect(JSON.stringify(model.graph)).not.toMatch(
      /"(review|decision|status|signoff|audit|ledger)"/,
    );
  });
});
