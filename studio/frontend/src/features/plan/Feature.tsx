"use client";

/**
 * Plan — the compiled workflow, drawn as a compositor graph.
 *
 * PROP CONTRACT (`FeatureProps`, see `src/lib/types.ts`):
 *   document      The plan's steps are matched back to `table:` / `component:` /
 *                 `projection:` refs so a node can light the entity it was compiled
 *                 from, and a table's declared-column count comes from here (the plan
 *                 projection names the payload key but does not send its value).
 *                 Module colours and chips come from the plan's own `modules`, not
 *                 `document.modules`: a compiled contract records the modules that
 *                 actually took part.
 *   index         Unused: the DAG comes from the contract, not the index.
 *   problems      Read from the problem store by ref (not the pre-filtered list) so a
 *                 build problem on `component:site` badges the aggregate that emitted
 *                 it, wherever its tier lands.
 *   selectedRef   The IR ref the rest of the studio has selected; drives the "only
 *                 steps that touch it" filter and the selected node ring.
 *   onSelectRef   Clicking a node publishes its ref — the plan → topology link.
 *   apply         Unused: the plan is compiled output, never edited here.
 *
 * The plan itself is fetched by this area (`GET /api/plan`) and cached in
 * `planStore.ts`, because it is not document state and the shell does not pass it.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button, Chip, EmptyState, Panel, Skeleton } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { entityRef } from "@/lib/ids";
import type { FeatureProps, PlanModule } from "@/lib/types";
import type { StepKind } from "./types";
import { useConnectionStore, notify } from "@/stores/connectionStore";
import { useDocumentStore } from "@/stores/documentStore";
import { useProblemStore } from "@/stores/problemStore";
import { useSelectionStore } from "@/stores/selectionStore";

import type { PlanFilters } from "./types";
import { EMPTY_FILTERS, shortFingerprint } from "./filters";
import { buildPlanModel, problemsForStep } from "./model";
import { stepRef } from "./detail";
import { traceSubDag } from "./subdag";
import { spacingFor } from "./spacing";
import { usePlanStore } from "./planStore";
import { PlanCanvas } from "./PlanCanvas";
import { FilterStrip } from "./FilterStrip";
import { SqlSheet } from "./SqlSheet";
import { StaleBanner } from "./StaleBanner";
import { Legend } from "./Legend";

const NO_MODULES: readonly PlanModule[] = [];

export default function PlanFeature({ document, selectedRef, onSelectRef }: FeatureProps) {
  const mock = useDocumentStore((state) => state.mock);
  const status = useConnectionStore((state) => state.status);
  const generation = useConnectionStore((state) => state.generation);
  const lastPlanEvent = useConnectionStore((state) => (state.lastEventType === "plan" ? state.lastEventAt : null));
  const byRefIndex = useProblemStore((state) => state.byRefIndex);

  const nodes = usePlanStore((state) => state.nodes);
  const edges = usePlanStore((state) => state.edges);
  // A selector must hand back the same reference when nothing changed: `?? []`
  // would build a new array per snapshot and `useSyncExternalStore` would spin.
  const plan = usePlanStore((state) => state.plan);
  const modules = (plan?.modules ?? NO_MODULES) as readonly PlanModule[];
  const fingerprint = usePlanStore((state) => state.fingerprint);
  const loading = usePlanStore((state) => state.loading);
  const refreshing = usePlanStore((state) => state.refreshing);
  const error = usePlanStore((state) => state.error);
  const source = usePlanStore((state) => state.source);
  const load = usePlanStore((state) => state.load);
  const refresh = usePlanStore((state) => state.refresh);

  const setArea = useSelectionStore((state) => state.setArea);
  const [filters, setFilters] = useState<PlanFilters>(EMPTY_FILTERS);
  const [building, setBuilding] = useState(false);

  // Executing the plan is the one thing here the backend cannot do on its own: the
  // watcher keeps the code and the compiled contract current, but only an author
  // decides when to spend a DuckDB run. Problems come back on the `build` event.
  const runBuild = useCallback(async () => {
    if (building) return;
    setBuilding(true);
    try {
      const result = await api.build();
      const artifacts = result.artifacts ?? [];
      notify({
        level: result.ok ? "info" : "error",
        text: result.ok
          ? `build finished · ${artifacts.length} artifact${artifacts.length === 1 ? "" : "s"}`
          : "the build failed — see the Problems panel",
      });
    } catch (cause: unknown) {
      notify({
        level: "error",
        text: cause instanceof ApiError ? `build failed: ${cause.reason}` : `build failed: ${String(cause)}`,
      });
    } finally {
      setBuilding(false);
    }
  }, [building]);
  const [stayOnPlan, setStayOnPlan] = useState(true);
  const [spacing, setSpacing] = useState(32);
  const [hovered, setHovered] = useState<string | null>(null);
  const [sqlStep, setSqlStep] = useState<string | null>(null);
  const [fitToken, setFitToken] = useState(0);

  // The plan is compiled output: fetch once, and again whenever the backend pushes
  // a `plan` event (the shell notes the event, so its timestamp is the signal).
  useEffect(() => {
    void load(Boolean(mock));
  }, [mock, load, lastPlanEvent]);

  const model = useMemo(
    () =>
      buildPlanModel({
        nodes,
        edges,
        modules,
        fingerprint,
        filters,
        selectedRef,
        document,
        spacing: spacingFor(spacing),
        generationState: generation ?? status?.generation?.state ?? null,
        mock: Boolean(mock),
      }),
    [nodes, edges, modules, fingerprint, filters, selectedRef, document, spacing, generation, status, mock],
  );

  const trace = useMemo(
    () => traceSubDag(hovered, model.visibleNodes, model.visibleEdges),
    [hovered, model.visibleNodes, model.visibleEdges],
  );

  const kindCounts = useMemo(() => {
    const counts = new Map<StepKind, number>();
    for (const node of nodes) counts.set(node.kind, (counts.get(node.kind) ?? 0) + 1);
    return counts;
  }, [nodes]);
  // Most numerous first: the kinds a reader is most likely hunting for are the ones
  // with the most steps, and the order is total (count, then id).
  const kinds = useMemo(
    () =>
      [...kindCounts.entries()]
        .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
        .map(([kind]) => kind),
    [kindCounts],
  );

  const moduleCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const node of nodes) counts.set(node.module_id, (counts.get(node.module_id) ?? 0) + 1);
    return counts;
  }, [nodes]);

  const openStep = sqlStep ? nodes.find((node) => node.id === sqlStep) ?? null : null;
  const openDetail = openStep ? model.details.get(openStep.id) ?? null : null;

  const relayout = useCallback(() => setFitToken((value) => value + 1), []);

  /**
   * Select through the shell's `onSelectRef` — that is the contract, and it is what
   * lights the ref in the inspector and in every other tab. The shell's
   * implementation also moves the visible area to whichever tab owns the ref, which
   * for a canvas area means losing the view you were reading on the first click, so
   * the selection is kept and the tab is put back. Turn "stay on plan" off to let it
   * navigate, which is what the shell alone would do.
   */
  const selectRef = useCallback(
    (ref: string | null) => {
      onSelectRef(ref);
      if (stayOnPlan && ref && useSelectionStore.getState().area !== "plan") setArea("plan");
    },
    [onSelectRef, stayOnPlan, setArea],
  );

  const selectedProblems = useMemo(() => {
    if (!openStep) return [];
    return problemsForStep(byRefIndex, openStep);
  }, [byRefIndex, openStep]);

  const componentCount = useMemo(() => {
    const refs = new Set<string>();
    for (const node of nodes) {
      const ref = stepRef(node);
      if (ref) refs.add(entityRef(ref) ?? ref);
    }
    return refs;
  }, [nodes]);

  const compileErrors = usePlanStore((state) => state.errors.length);

  if (loading && nodes.length === 0) {
    return (
      <Panel title="Plan — workflow DAG" subtitle="loading compiled contract…">
        <Skeleton lines={10} height={16} />
      </Panel>
    );
  }

  if (error && nodes.length === 0) {
    return (
      <Panel title="Plan — workflow DAG">
        <EmptyState
          title="The compiled plan could not be read"
          body={error}
          actions={
            <Button variant="primary" onClick={() => void refresh()}>
              try again
            </Button>
          }
        />
      </Panel>
    );
  }

  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <Panel
          id="panel-plan"
          role="region"
          title="Plan — workflow DAG"
          subtitle={`${model.totals.steps} steps · ${model.totals.connections} connections`}
          padded={false}
          className="min-w-0 flex-1"
          bodyClassName="flex min-h-0 flex-col"
          actions={
            <>
              {source === "mock" && (
                <Chip tone="template" title="src/lib/mock.ts ships no plan fixture, so this is a captured real plan">
                  captured plan
                </Chip>
              )}
              <Chip
                title={`plan fingerprint ${fingerprint ?? "unknown"}`}
                tone={model.stale.level === "stale" ? "warn" : "neutral"}
              >
                {shortFingerprint(fingerprint)}
              </Chip>
              <span className="font-mono text-[10px] text-faint">{componentCount.size} refs</span>
            </>
          }
        >
          <StaleBanner
            stale={model.stale}
            refreshing={refreshing}
            errors={compileErrors}
            onRefresh={() => void refresh()}
          />
          <FilterStrip
            modules={modules}
            kinds={kinds}
            kindCounts={kindCounts}
            moduleCounts={moduleCounts}
            filters={filters}
            counts={model.counts}
            totals={model.totals}
            colors={model.colors}
            selectedRef={selectedRef}
            stayOnPlan={stayOnPlan}
            onStayOnPlan={setStayOnPlan}
            spacing={spacing}
            loading={loading || refreshing}
            onFilters={setFilters}
            onSpacing={setSpacing}
            onRelayout={relayout}
            onFit={relayout}
            onRefresh={() => void refresh()}
            onBuild={mock ? undefined : runBuild}
            building={building || status?.build?.state === "running"}
            buildState={status?.build?.state ?? "never"}
          />
          <PlanCanvas
            model={model}
            trace={trace}
            hovered={hovered}
            byRefIndex={byRefIndex}
            fitToken={fitToken}
            onHover={setHovered}
            onSelectRef={selectRef}
            onOpenSql={(id) => setSqlStep(id)}
          />
          <Legend />
        </Panel>
      </div>

      {openStep && (
        <SqlSheet
          step={openStep}
          detail={openDetail}
          nodes={nodes}
          edges={edges}
          problems={selectedProblems}
          onClose={() => setSqlStep(null)}
          onSelectRef={selectRef}
        />
      )}
    </div>
  );
}
