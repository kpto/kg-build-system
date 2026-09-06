import { describe, expect, it } from "vitest";

import { EMPTY_FILTERS } from "./filters";
import { buildPlanModel, problemsForStep } from "./model";
import { SAMPLE_PLAN } from "./samplePlan";
import { DEFAULT_SPACING } from "./layout";
import { spacingFor } from "./spacing";
import type { Problem } from "@/lib/types";

const model = buildPlanModel({
  nodes: SAMPLE_PLAN.nodes ?? [],
  edges: SAMPLE_PLAN.edges ?? [],
  modules: SAMPLE_PLAN.modules ?? [],
  fingerprint: SAMPLE_PLAN.fingerprint ?? null,
});

describe("view model", () => {
  it("draws every step of the real plan and reports the totals it counted", () => {
    expect(model.layout.placed).toHaveLength(60);
    expect(model.counts).toEqual({
      steps: 60,
      connections: 90,
      materialised: 0,
      withSql: 16,
      components: 19,
    });
    // No generation state at all is not "fresh": a plan with nothing behind it is
    // reported as stale-by-unknown, and the banner says so.
    expect(model.stale.level).toBe("stale");
    expect(model.stale.state).toBe("never");
    expect(model.fingerprint).toBe(SAMPLE_PLAN.fingerprint);
  });

  it("marks every step of the selected component, in every lane", () => {
    const selected = buildPlanModel({
      nodes: SAMPLE_PLAN.nodes ?? [],
      edges: SAMPLE_PLAN.edges ?? [],
      modules: SAMPLE_PLAN.modules ?? [],
      selectedRef: "component:site",
    });
    expect([...selected.selectedSteps].sort()).toEqual([
      "collapse_exact_duplicates::site",
      "core::aggregate.site",
      "core::binding.11",
      "neo4j::export.node.site-e29c0d4f",
    ]);
  });

  it("routes problems to the step that compiled them", () => {
    const problems: Record<string, Problem[]> = {
      "component:has_defect": [
        {
          id: "p1",
          tier: "build",
          severity: "error",
          message: "boom",
          ref: "component:has_defect",
        },
      ],
    };
    const binding = (SAMPLE_PLAN.nodes ?? []).find((node) => node.id === "core::binding.0");
    expect(binding).toBeDefined();
    // The binding step carries no `component`; the ref recovered from its role is
    // what attaches the problem to it.
    expect(problemsForStep(problems, binding!).map((problem) => problem.id)).toEqual(["p1"]);
  });

  it("shrinks the drawn graph and recomputes the counts when a filter applies", () => {
    const filtered = buildPlanModel({
      nodes: SAMPLE_PLAN.nodes ?? [],
      edges: SAMPLE_PLAN.edges ?? [],
      modules: SAMPLE_PLAN.modules ?? [],
      filters: { ...EMPTY_FILTERS, kinds: ["aggregate"] },
    });
    expect(filtered.layout.placed).toHaveLength(12);
    expect(filtered.visibleEdges).toHaveLength(0);
    expect(filtered.counts.steps).toBe(12);
    expect(filtered.totals.steps).toBe(60);
  });
});

describe("spacing control", () => {
  it("maps the slider to gaps that bracket the default", () => {
    const tight = spacingFor(0);
    const wide = spacingFor(100);
    expect(tight.columnGap).toBeLessThan(DEFAULT_SPACING.columnGap);
    expect(wide.columnGap).toBeGreaterThan(DEFAULT_SPACING.columnGap);
    expect(wide.rowGap).toBeGreaterThan(tight.rowGap);
    // One vertical field, so one vertical gap: no lane band to space any more.
    expect(Object.keys(wide).sort()).toEqual(["columnGap", "rowGap"]);
  });

  it("clamps out-of-range slider values", () => {
    expect(spacingFor(-20)).toEqual(spacingFor(0));
    expect(spacingFor(400)).toEqual(spacingFor(100));
  });
});
