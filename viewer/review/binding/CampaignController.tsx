"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import type {
  AuditInput,
  DiagnosisInput,
  NavigatorInput,
} from "@/shared/model/builders";
import type {
  CampaignCommands,
  CampaignCounts,
  CampaignRecord,
  Representation,
  Task,
} from "@/shared/model/campaign";
import type { InspectorSelection } from "@/shared/types/selection";
import { buildAudit } from "@/lib/audit";
import { buildCoverage } from "@/lib/coverage";
import { deriveDecisions } from "@/lib/decisions";
import { diffSnapshots } from "@/lib/diff";
import {
  buildDossierJson,
  buildDossierMarkdown,
  downloadDossier,
} from "@/lib/dossier";
import { computeImpact } from "@/lib/impact";
import { buildViewerIndex, stepKey } from "@/lib/indexes";
import { searchIndex } from "@/lib/search";
import { buildLineage, propertySelection } from "@/lib/lineage";
import {
  loadDefaultSnapshot,
  loadReferenceReview,
  loadReferenceSnapshot,
  loadReviewSidecar,
  loadSnapshotFromFile,
  loadSnapshotFromObject,
} from "@/lib/load";
import {
  loadReviewQueue,
  saveReviewQueue,
  setReviewStatus,
  summarizeQueue,
} from "@/lib/reviewQueue";
import { readUrlState, writeUrlState, type ReviewView } from "@/lib/urlState";
import type {
  AuditReport,
  AuditSubject,
  CoverageMatrix,
  DecisionView,
  ReviewQueueSummary,
  ReviewRecord,
  ReviewSidecar,
  ReviewStatus,
  SnapshotDiff,
} from "@/lib/reviewTypes";
import type {
  EntityKind,
  LineageNode,
  PropertySelection,
  SearchResult,
  StepId,
  ViewerIndex,
  ViewerSnapshot,
  WorkflowStep,
} from "@/lib/types";
import { buildAppModel } from "@/review/model/buildAppModel";
import { CampaignFrameView } from "@/review/view/CampaignFrameView";

const EMPTY_SUMMARY: ReviewQueueSummary = {
  total: 0,
  open: 0,
  acknowledged: 0,
  waived: 0,
  resolved: 0,
};

const EMPTY_REVIEW: ReviewSidecar = {
  format: "kg-viewer-review",
  version: 1,
  decisions: [],
};

const ZERO_COUNTS: CampaignCounts = {
  assets: 0,
  tables: 0,
  projections: 0,
  nodes: 0,
  edges: 0,
  bindings: 0,
  steps: 0,
  connections: 0,
};

const BASELINE_PREFIX = "kg-viewer:baseline:";

/** Run expensive read-only analysis after the shell has painted. */
function scheduleIdle(task: () => void): () => void {
  if (typeof window === "undefined") {
    task();
    return () => undefined;
  }
  const idle = window.requestIdleCallback;
  if (typeof idle === "function") {
    const id = idle(task, { timeout: 1800 });
    return () => window.cancelIdleCallback?.(id);
  }
  const id = window.setTimeout(task, 60);
  return () => window.clearTimeout(id);
}

function sameSubject(
  left: AuditSubject | undefined,
  right: AuditSubject | undefined,
): boolean {
  if (!left || !right) return false;
  return (
    left.kind === right.kind &&
    left.name === right.name &&
    left.component === right.component &&
    left.property === right.property &&
    left.entityKind === right.entityKind &&
    left.bindingIndex === right.bindingIndex
  );
}

function subjectLabel(subject: AuditSubject): string {
  const name = subject.component ?? subject.name;
  return subject.property
    ? `${subject.kind} ${name}.${subject.property}`
    : `${subject.kind} ${name}`;
}

function isDiagnosisView(
  view: ReviewView,
): view is Extract<ReviewView, "workflow" | "blueprint" | "lineage"> {
  return view === "workflow" || view === "blueprint" || view === "lineage";
}

function groupKeys(index: ViewerIndex, grouping: "component" | "emitter"): string[] {
  const keys = new Set<string>();
  for (const step of index.steps) {
    keys.add(
      grouping === "component"
        ? `component:${step.id[0]}`
        : `emitter:${step.instruction.kind.join(":")}`,
    );
  }
  return [...keys];
}

function campaignCounts(index: ViewerIndex): CampaignCounts {
  return {
    assets: index.stats.assets,
    tables: index.stats.tables,
    projections: index.stats.projections,
    nodes: index.stats.topologyNodes,
    edges: index.stats.topologyEdges,
    bindings: index.stats.bindings,
    steps: index.stats.steps,
    connections: index.stats.connections,
  };
}

/**
 * The React binding for the campaign.
 *
 * It owns the evidence record (loading, analysis, queue, baseline, URL,
 * selection, import, shortcuts) and the presentation state shared across
 * panels (representation, grouping, collapsed groups, focus step, lineage
 * source filter, selected finding, review subject). It projects that state
 * through the pure model builders and injects the result into the frame view.
 *
 * Views own nothing here; they receive the `AppModel` and render it.
 */
export function CampaignController() {
  const [snapshot, setSnapshot] = useState<ViewerSnapshot | null>(null);
  const [index, setIndex] = useState<ViewerIndex | null>(null);
  const [review, setReview] = useState<ReviewSidecar | undefined>();
  const [loadError, setLoadError] = useState<string | undefined>();
  const [importError, setImportError] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ReviewView>("map");
  const [query, setQuery] = useState("");
  const [selection, setSelection] = useState<InspectorSelection | null>(null);
  const [propertySelectionState, setPropertySelectionState] =
    useState<PropertySelection | null>(null);
  const [queue, setQueue] = useState<Record<string, ReviewRecord>>({});
  const [baseline, setBaseline] = useState<ViewerSnapshot | null>(null);
  const [diff, setDiff] = useState<SnapshotDiff | null>(null);
  const [selectedFindingId, setSelectedFindingId] = useState<string | undefined>();
  const [reviewSubjectFilter, setReviewSubjectFilter] = useState<
    AuditSubject | undefined
  >();
  const [focusStepId, setFocusStepId] = useState<StepId | undefined>();
  const [lineageSourceFilter, setLineageSourceFilter] = useState<
    string | undefined
  >();
  const [grouping, setGroupingState] = useState<"component" | "emitter">(
    "component",
  );
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [toast, setToast] = useState<string | undefined>();
  const [bootstrapped, setBootstrapped] = useState(false);
  const bootstrappedRef = useRef(false);
  const indexRef = useRef<ViewerIndex | null>(null);

  useEffect(() => {
    let active = true;
    const requested =
      typeof window === "undefined"
        ? null
        : new URLSearchParams(window.location.search).get("snapshot");
    const reference = requested === "reference";
    Promise.all([
      reference ? loadReferenceSnapshot() : loadDefaultSnapshot(),
      (reference ? loadReferenceReview() : loadReviewSidecar()).catch(
        () => undefined,
      ),
    ])
      .then(([loaded, sidecar]) => {
        if (!active) return;
        const nextIndex = buildViewerIndex(loaded);
        setSnapshot(loaded);
        setIndex(nextIndex);
        setReview(loaded.review ?? sidecar);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setLoadError(error instanceof Error ? error.message : String(error));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // Review state is per snapshot: the queue and the pinned baseline both use the
  // snapshot name as their storage key.
  useEffect(() => {
    if (!snapshot) return;
    setQueue(loadReviewQueue(snapshot.name));
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(`${BASELINE_PREFIX}${snapshot.name}`);
    if (!stored) {
      setBaseline(null);
      setDiff(null);
      return;
    }
    try {
      const base = loadSnapshotFromObject(JSON.parse(stored));
      setBaseline(base);
      setDiff(diffSnapshots(base, snapshot));
    } catch {
      setBaseline(null);
      setDiff(null);
    }
  }, [snapshot]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(undefined), 2800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const [audit, setAudit] = useState<AuditReport | null>(null);
  const [decisions, setDecisions] = useState<DecisionView[]>([]);
  const [coverage, setCoverage] = useState<CoverageMatrix | null>(null);

  useEffect(() => {
    setAudit(null);
    setDecisions([]);
    setCoverage(null);
    if (!index) return;

    let cancelled = false;
    const cancel = scheduleIdle(() => {
      if (cancelled) return;
      setAudit(buildAudit(index, review));
    });
    return () => {
      cancelled = true;
      cancel();
    };
  }, [index, review]);

  // Decisions and coverage are only needed by the audit task. Compute them when
  // it opens instead of spending the first seconds after the map paints.
  useEffect(() => {
    if (!index || view !== "review" || coverage) return;
    let cancelled = false;
    const cancel = scheduleIdle(() => {
      if (cancelled) return;
      setDecisions(deriveDecisions(index, review));
      setCoverage(buildCoverage(index));
    });
    return () => {
      cancelled = true;
      cancel();
    };
  }, [index, review, view, coverage]);

  // A new index is a new presentation problem: reset grouping and fit.
  useEffect(() => {
    if (!index) return;
    if (indexRef.current === index) return;
    indexRef.current = index;
    if (index.steps.length > 200) {
      setGroupingState("emitter");
      setCollapsedGroups(new Set(groupKeys(index, "emitter")));
    } else {
      setGroupingState("component");
      setCollapsedGroups(new Set());
    }
  }, [index]);

  const queueSummary = useMemo(
    () => (audit ? summarizeQueue(audit, queue) : EMPTY_SUMMARY),
    [audit, queue],
  );

  const counts = useMemo(
    () => (index ? campaignCounts(index) : ZERO_COUNTS),
    [index],
  );

  const lineage = useMemo(() => {
    if (!index || !propertySelectionState) return null;
    return buildLineage(index, propertySelectionState);
  }, [index, propertySelectionState]);

  const selectedSubject = useMemo<AuditSubject | undefined>(() => {
    if (!selection) return undefined;
    switch (selection.kind) {
      case "property":
        return {
          kind: "property",
          name: selection.selection.component,
          component: selection.selection.component,
          property: selection.selection.property,
          entityKind: selection.selection.kind,
        };
      case "topology":
        return {
          kind: selection.entityKind,
          name: selection.name,
          component: selection.name,
        };
      case "step":
        return {
          kind: "step",
          name: `${selection.step.id[0]}/${selection.step.id[1]}`,
          component: selection.step.id[0],
          stepId: selection.step.id,
        };
      case "binding":
        return {
          kind: "binding",
          name: selection.binding.component,
          component: selection.binding.component,
          bindingIndex: selection.binding.index,
        };
      case "asset":
        return { kind: "asset", name: selection.name, component: selection.name };
      case "data":
        return {
          kind: selection.entityType === "projection" ? "projection" : "relation",
          name: selection.name,
          component: selection.name,
        };
      case "field": {
        const location = index?.fieldsByKey.get(selection.fieldKey);
        if (!location) return undefined;
        return {
          kind: location.ownerKind === "projection" ? "projection" : "relation",
          name: location.ownerName,
          component: location.ownerName,
        };
      }
      case "lineage-node": {
        const node = selection.node;
        if (node.stepId) {
          return {
            kind: "step",
            name: `${node.stepId[0]}/${node.stepId[1]}`,
            component: node.stepId[0],
            stepId: node.stepId,
          };
        }
        if (node.component && node.property) {
          return {
            kind: "property",
            name: node.component,
            component: node.component,
            property: node.property,
          };
        }
        return undefined;
      }
    }
  }, [selection, index]);

  const impact = useMemo(
    () => (index && selectedSubject ? computeImpact(index, selectedSubject) : null),
    [index, selectedSubject],
  );

  const searchMatches = useMemo(() => {
    if (!index || !query.trim()) return [];
    return searchIndex(index.searchRecords, query, { limit: 24 });
  }, [index, query]);

  const handleSelectProperty = useCallback(
    (kind: EntityKind, component: string, property: string, source?: string) => {
      if (!index) return;
      const nextSelection = propertySelection(kind, component, property);
      const nextLineage = buildLineage(index, nextSelection);
      setPropertySelectionState(nextSelection);
      setSelection({ kind: "property", selection: nextSelection, lineage: nextLineage });
      setLineageSourceFilter(source);
      setReviewSubjectFilter(undefined);
      setSelectedFindingId(undefined);
      setView("lineage");
    },
    [index],
  );

  const handleSelect = useCallback((next: InspectorSelection) => {
    setSelection(next);
    if (next.kind === "step") {
      setView("workflow");
    } else if (next.kind === "topology" || next.kind === "data" || next.kind === "asset") {
      setView("blueprint");
    }
  }, []);

  const handleSelectStep = useCallback((step: WorkflowStep) => {
    setSelection({ kind: "step", step });
    setView("workflow");
  }, []);

  const handleSelectLineageNode = useCallback(
    (node: LineageNode) => {
      if (!lineage) return;
      setSelection({ kind: "lineage-node", node, lineage });
    },
    [lineage],
  );

  const handleOpenSubject = useCallback(
    (subject: AuditSubject) => {
      if (!index) return;
      switch (subject.kind) {
        case "property":
          if (subject.component && subject.property && subject.entityKind) {
            handleSelectProperty(
              subject.entityKind,
              subject.component,
              subject.property,
            );
          }
          return;
        case "node":
        case "edge":
          setView("blueprint");
          setSelection({ kind: "topology", entityKind: subject.kind, name: subject.name });
          return;
        case "step": {
          const step = subject.stepId
            ? index.stepsById.get(stepKey(subject.stepId))
            : subject.component
              ? index.steps.find((candidate) => candidate.id[0] === subject.component)
              : undefined;
          if (step) handleSelectStep(step);
          return;
        }
        case "binding": {
          const binding = index.bindings.find(
            (candidate) =>
              candidate.component === subject.component &&
              (subject.bindingIndex === undefined ||
                candidate.index === subject.bindingIndex),
          );
          if (binding) setSelection({ kind: "binding", binding });
          return;
        }
        case "asset":
          setView("blueprint");
          setSelection({ kind: "asset", name: subject.name });
          return;
        case "relation":
        case "projection":
          setView("blueprint");
          setSelection({ kind: "data", entityType: subject.kind, name: subject.name });
          return;
      }
    },
    [index, handleSelectProperty, handleSelectStep],
  );

  const handleOpenReview = useCallback(
    (subject: AuditSubject) => {
      setView("review");
      setReviewSubjectFilter(subject);
      setFocusStepId(undefined);
      const match = audit?.findings.find((finding) =>
        sameSubject(finding.subject, subject),
      );
      setSelectedFindingId(match?.id);
    },
    [audit],
  );

  const handleOpenReviewForStep = useCallback(
    (step: WorkflowStep) => {
      handleOpenReview({
        kind: "step",
        name: `${step.id[0]}/${step.id[1]}`,
        component: step.id[0],
        stepId: step.id,
      });
    },
    [handleOpenReview],
  );

  const handleFocusStep = useCallback((step: WorkflowStep) => {
    setFocusStepId(step.id);
    setView("workflow");
  }, []);

  const handleSetStatus = useCallback(
    (id: string, status: ReviewStatus, note?: string) => {
      if (!snapshot) return;
      try {
        setQueue((current) => {
          const next = setReviewStatus(current, id, status, note);
          saveReviewQueue(snapshot.name, next);
          return next;
        });
        setToast(
          status === "waived"
            ? "Finding waived with note"
            : status === "acknowledged"
              ? "Finding acknowledged"
              : "Review status updated",
        );
      } catch (error) {
        setToast(error instanceof Error ? error.message : String(error));
      }
    },
    [snapshot],
  );

  const handlePinBaseline = useCallback(() => {
    if (!snapshot || typeof window === "undefined") return;
    try {
      window.localStorage.setItem(
        `${BASELINE_PREFIX}${snapshot.name}`,
        JSON.stringify(snapshot),
      );
      setBaseline(snapshot);
      setDiff(diffSnapshots(snapshot, snapshot));
      setToast("Baseline pinned");
    } catch {
      setToast("Could not pin the baseline in this browser");
    }
  }, [snapshot]);

  const handleClearBaseline = useCallback(() => {
    if (!snapshot || typeof window === "undefined") return;
    window.localStorage.removeItem(`${BASELINE_PREFIX}${snapshot.name}`);
    setBaseline(null);
    setDiff(null);
    setToast("Baseline cleared");
  }, [snapshot]);

  const handleCompareSnapshot = useCallback(
    async (file: File) => {
      if (!baseline) {
        setToast("Pin a baseline before comparing");
        return;
      }
      try {
        const next = await loadSnapshotFromFile(file);
        setDiff(diffSnapshots(baseline, next));
        setToast(`Compared ${file.name}`);
      } catch (error) {
        setToast(
          `Compare failed: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    },
    [baseline],
  );

  const handleExportDossier = useCallback(
    (format: "markdown" | "json") => {
      if (!index || !audit) return;
      const input = {
        index,
        audit,
        decisions,
        queue,
        ...(propertySelectionState ? { selection: propertySelectionState } : {}),
        ...(lineage ? { lineage } : {}),
        ...(diff ? { diff } : {}),
      };
      if (format === "markdown") {
        downloadDossier(
          `${snapshot?.name ?? "snapshot"}-review.md`,
          buildDossierMarkdown(input),
          "text/markdown",
        );
      } else {
        downloadDossier(
          `${snapshot?.name ?? "snapshot"}-review.json`,
          buildDossierJson(input),
          "application/json",
        );
      }
      setToast(`Exported ${format} dossier`);
    },
    [index, audit, decisions, queue, propertySelectionState, lineage, diff, snapshot],
  );

  const handleCopyDossier = useCallback(
    (format: "markdown" | "json") => {
      if (!index || !audit) return;
      const input = {
        index,
        audit,
        decisions,
        queue,
        ...(propertySelectionState ? { selection: propertySelectionState } : {}),
        ...(lineage ? { lineage } : {}),
        ...(diff ? { diff } : {}),
      };
      const text =
        format === "markdown" ? buildDossierMarkdown(input) : buildDossierJson(input);
      if (typeof navigator === "undefined" || !navigator.clipboard) {
        setToast("Clipboard is unavailable in this browser");
        return;
      }
      navigator.clipboard
        .writeText(text)
        .then(() => setToast(`Copied ${format} dossier`))
        .catch(() => setToast("Could not copy the dossier"));
    },
    [index, audit, decisions, queue, propertySelectionState, lineage, diff],
  );

  const handleSearchSelect = useCallback(
    (result: SearchResult) => {
      if (!index) return;
      setQuery("");
      switch (result.kind) {
        case "property":
          if (result.component && result.property && result.entityKind) {
            handleSelectProperty(result.entityKind, result.component, result.property);
          }
          return;
        case "step": {
          const step = result.stepId
            ? index.stepsById.get(stepKey(result.stepId))
            : undefined;
          if (step) handleSelectStep(step);
          return;
        }
        case "binding": {
          const binding = index.bindings.find(
            (candidate) =>
              candidate.component === result.component &&
              candidate.index === result.bindingIndex,
          );
          if (binding) handleSelect({ kind: "binding", binding });
          return;
        }
        case "asset":
          setView("blueprint");
          handleSelect({ kind: "asset", name: result.name });
          return;
        case "relation":
          setView("blueprint");
          handleSelect({ kind: "data", entityType: "relation", name: result.name });
          return;
        case "projection":
          setView("blueprint");
          handleSelect({ kind: "data", entityType: "projection", name: result.name });
          return;
        case "struct":
          handleSelect({ kind: "data", entityType: "struct", name: result.name });
          return;
        case "field":
          handleSelect({ kind: "field", fieldKey: result.name });
          return;
        case "topology-node":
          setView("blueprint");
          handleSelect({ kind: "topology", entityKind: "node", name: result.name });
          return;
        case "topology-edge":
          setView("blueprint");
          handleSelect({ kind: "topology", entityKind: "edge", name: result.name });
          return;
        case "instruction": {
          const step = index.steps.find(
            (candidate) => candidate.instruction.kind.join(":") === result.name,
          );
          if (step) handleSelectStep(step);
          return;
        }
        case "workflow-component": {
          const step = index.steps.find((candidate) => candidate.id[0] === result.name);
          if (step) handleSelectStep(step);
          return;
        }
      }
    },
    [index, handleSelect, handleSelectProperty, handleSelectStep],
  );

  const handleImport = useCallback(async (file: File) => {
    setImportError(undefined);
    try {
      const loaded = await loadSnapshotFromFile(file);
      const nextIndex = buildViewerIndex(loaded);
      setSnapshot(loaded);
      setIndex(nextIndex);
      setReview(loaded.review);
      setSelection(null);
      setPropertySelectionState(null);
      setView("workflow");
      setQuery("");
      setFocusStepId(undefined);
      setLineageSourceFilter(undefined);
      setReviewSubjectFilter(undefined);
      setSelectedFindingId(undefined);
      setToast(`Loaded ${loaded.name}`);
    } catch (error) {
      setImportError(error instanceof Error ? error.message : String(error));
    }
  }, []);

  // Restore a deep link once the index can resolve it.
  useEffect(() => {
    if (!index || bootstrappedRef.current) return;
    bootstrappedRef.current = true;
    const state = readUrlState();
    setView(state.view);
    if (state.component && state.property) {
      const kind: EntityKind = state.kind ?? "node";
      const nextSelection = propertySelection(kind, state.component, state.property);
      const nextLineage = buildLineage(index, nextSelection);
      setPropertySelectionState(nextSelection);
      setSelection({ kind: "property", selection: nextSelection, lineage: nextLineage });
      if (state.source) setLineageSourceFilter(state.source);
    } else if (state.step) {
      const step = index.stepsById.get(stepKey(state.step));
      if (step) {
        setSelection({ kind: "step", step });
      }
    }
    if (state.finding) setSelectedFindingId(state.finding);
    setBootstrapped(true);
  }, [index]);

  // Keep the address bar in sync with the review context.
  useEffect(() => {
    if (!bootstrapped) return;
    writeUrlState({
      view,
      ...(propertySelectionState
        ? {
            component: propertySelectionState.component,
            property: propertySelectionState.property,
            kind: propertySelectionState.kind,
          }
        : {}),
      ...(selection?.kind === "step" ? { step: selection.step.id } : {}),
      ...(selectedFindingId ? { finding: selectedFindingId } : {}),
      ...(lineageSourceFilter ? { source: lineageSourceFilter } : {}),
    });
  }, [
    bootstrapped,
    view,
    propertySelectionState,
    selection,
    selectedFindingId,
    lineageSourceFilter,
  ]);

  const nextFinding = useCallback(
    (direction: 1 | -1) => {
      if (!audit || audit.findings.length === 0) return;
      const ordered = audit.findings;
      const current = ordered.findIndex((finding) => finding.id === selectedFindingId);
      const nextIndex =
        current < 0
          ? direction > 0
            ? 0
            : ordered.length - 1
          : (current + direction + ordered.length) % ordered.length;
      const next = ordered[nextIndex];
      setSelectedFindingId(next.id);
      setView("review");
    },
    [audit, selectedFindingId],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const textEntry =
        target?.closest("input, textarea, select, [contenteditable='true']") ?? null;
      if (textEntry) {
        if (event.key === "Escape") (textEntry as HTMLElement).blur();
        return;
      }
      if (event.metaKey || event.ctrlKey || event.altKey) return;

      switch (event.key) {
        case "/": {
          event.preventDefault();
          document
            .querySelector<HTMLInputElement>('[data-testid="search-input"]')
            ?.focus();
          break;
        }
        case "m":
          setView("map");
          break;
        case "w":
          setView("workflow");
          break;
        case "b":
          setView("blueprint");
          break;
        case "l":
          setView("lineage");
          break;
        case "r":
          setView("review");
          break;
        case "j":
          event.preventDefault();
          nextFinding(1);
          break;
        case "k":
          event.preventDefault();
          nextFinding(-1);
          break;
        case "Enter": {
          const finding = audit?.findings.find(
            (candidate) => candidate.id === selectedFindingId,
          );
          if (finding?.subject) handleOpenSubject(finding.subject);
          break;
        }
        case "?":
          setShortcutsOpen((value) => !value);
          break;
        case "Escape":
          setShortcutsOpen(false);
          setFocusStepId(undefined);
          break;
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [audit, handleOpenSubject, nextFinding, selectedFindingId]);

  const handleGrouping = useCallback(
    (next: "component" | "emitter") => {
      setGroupingState(next);
      if (index && index.steps.length > 200) {
        setCollapsedGroups(new Set(groupKeys(index, next)));
      }
    },
    [index],
  );

  const toggleGroup = useCallback((key: string) => {
    setCollapsedGroups((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleAll = useCallback(
    (collapse: boolean) => {
      setCollapsedGroups(
        collapse && index ? new Set(groupKeys(index, grouping)) : new Set(),
      );
    },
    [index, grouping],
  );

  const task: Task =
    view === "map" ? "map" : view === "review" ? "review" : "explore";
  const representation: Representation = isDiagnosisView(view) ? view : "workflow";

  const commands = useMemo<CampaignCommands>(
    () => ({
      setTask: (next) => {
        if (next === "map") setView("map");
        else if (next === "review") setView("review");
        else setView(isDiagnosisView(view) ? view : "workflow");
      },
      setRepresentation: (next) => setView(next),
      setQuery,
      importFile: (file) => {
        void handleImport(file);
      },
      select: (next) => {
        if (next) handleSelect(next);
        else setSelection(null);
      },
      selectProperty: handleSelectProperty,
      selectStep: handleSelectStep,
      selectLineageNode: handleSelectLineageNode,
      openReview: handleOpenReview,
      openReviewForStep: handleOpenReviewForStep,
      selectFinding: (findingId) => {
        setSelectedFindingId(findingId);
        setView("review");
      },
      focusStep: handleFocusStep,
      clearFocus: () => setFocusStepId(undefined),
      clearReviewSubject: () => setReviewSubjectFilter(undefined),
      setLineageSourceFilter: (source) => setLineageSourceFilter(source),
      clearLineageSource: () => setLineageSourceFilter(undefined),
      setReviewStatus: handleSetStatus,
      pinBaseline: handlePinBaseline,
      clearBaseline: handleClearBaseline,
      compareSnapshot: (file) => {
        void handleCompareSnapshot(file);
      },
      exportDossier: handleExportDossier,
      copyDossier: handleCopyDossier,
    }),
    [
      view,
      handleSelect,
      handleSelectProperty,
      handleSelectStep,
      handleSelectLineageNode,
      handleOpenReview,
      handleOpenReviewForStep,
      handleFocusStep,
      handleSetStatus,
      handlePinBaseline,
      handleClearBaseline,
      handleCompareSnapshot,
      handleExportDossier,
      handleCopyDossier,
      handleImport,
    ],
  );

  const navigatorInput = useMemo<NavigatorInput>(
    () => ({ grouping, collapsedGroups, onToggleGroup: toggleGroup }),
    [grouping, collapsedGroups, toggleGroup],
  );

  const diagnosisInput = useMemo<DiagnosisInput>(
    () => ({
      representation,
      setRepresentation: (next) => setView(next),
      grouping,
      setGrouping: handleGrouping,
      collapsedGroups,
      onToggleGroup: toggleGroup,
      onToggleAll: toggleAll,
      ...(focusStepId ? { focusStepId } : {}),
      ...(lineageSourceFilter ? { lineageSourceFilter } : {}),
      onClearSourceFilter: () => setLineageSourceFilter(undefined),
    }),
    [
      representation,
      grouping,
      collapsedGroups,
      toggleGroup,
      toggleAll,
      focusStepId,
      lineageSourceFilter,
      handleGrouping,
    ],
  );

  const auditInput = useMemo<AuditInput>(
    () => ({
      ...(selectedFindingId ? { selectedFindingId } : {}),
      ...(reviewSubjectFilter ? { subjectFilter: reviewSubjectFilter } : {}),
      onClearSubjectFilter: () => setReviewSubjectFilter(undefined),
    }),
    [selectedFindingId, reviewSubjectFilter],
  );

  const appModel = useMemo(() => {
    if (!snapshot || !index) return null;
    const record: CampaignRecord = {
      snapshot,
      index,
      review: review ?? EMPTY_REVIEW,
      audit,
      coverage,
      decisions,
      queue,
      queueSummary,
      baseline,
      diff,
      ...(loadError ? { loadError } : {}),
      ...(importError ? { importError } : {}),
    };
    return buildAppModel({
      record,
      task,
      representation,
      selection,
      counts,
      commands,
      query,
      searchResults: searchMatches,
      onSearchSelect: handleSearchSelect,
      ...(audit ? { score: audit.score.value } : {}),
      ...(impact
        ? { impact: `${impact.upstream.length}/${impact.downstream.length}` }
        : {}),
      navigator: navigatorInput,
      diagnosis: diagnosisInput,
      audit: auditInput,
    });
  }, [
    snapshot,
    index,
    review,
    audit,
    coverage,
    decisions,
    queue,
    queueSummary,
    baseline,
    diff,
    loadError,
    importError,
    task,
    representation,
    selection,
    counts,
    commands,
    query,
    searchMatches,
    handleSearchSelect,
    impact,
    navigatorInput,
    diagnosisInput,
    auditInput,
  ]);

  if (loading) {
    return (
      <div
        data-testid="loading"
        className="flex h-screen flex-col items-center justify-center gap-3 bg-abyss text-muted"
      >
        <Loader2 className="size-4 animate-spin text-accent" aria-hidden />
        <span className="text-xs">Loading viewer snapshot…</span>
        <span className="font-mono text-[10px] text-faint">
          Open Targets is server-gzipped; the reference sample is bundled
        </span>
      </div>
    );
  }

  if (loadError || !index || !snapshot || !appModel) {
    return (
      <div className="flex h-screen items-center justify-center bg-abyss p-8">
        <div className="max-w-lg rounded-sm border border-critical/40 bg-panel p-6 text-center">
          <AlertTriangle className="mx-auto size-6 text-critical" aria-hidden />
          <h1 className="mt-3 text-sm font-semibold text-ink">
            Could not load the viewer
          </h1>
          <p className="mt-2 text-xs leading-relaxed text-muted">
            {loadError ?? "No snapshot loaded."}
          </p>
          <p className="mt-2 text-[10px] text-faint">
            Retry the bundled snapshot, or import a snapshot, blueprint or
            workflow plan JSON file directly.
          </p>
          <div className="mt-4 flex items-center justify-center gap-2">
            <button
              type="button"
              data-testid="retry-load"
              onClick={() => window.location.reload()}
              className="rounded-sm border border-accent/50 bg-accent-soft px-3 py-1.5 text-[11px] text-accent-strong hover:text-ink"
            >
              Retry
            </button>
            <label className="cursor-pointer rounded-sm border border-line px-3 py-1.5 text-[11px] text-muted hover:border-line-strong">
              Import snapshot
              <input
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void handleImport(file);
                  event.target.value = "";
                }}
              />
            </label>
          </div>
        </div>
      </div>
    );
  }

  return (
    <CampaignFrameView
      model={appModel}
      toast={toast}
      shortcutsOpen={shortcutsOpen}
      onCloseShortcuts={() => setShortcutsOpen(false)}
      {...(reviewSubjectFilter
        ? { activeSubjectFilter: subjectLabel(reviewSubjectFilter) }
        : {})}
    />
  );
}
