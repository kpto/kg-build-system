"use client";

/**
 * Detail document view: one design subject read in full.
 *
 * Every record detail renders the same band order: Meaning, Constitution,
 * Members, Connections and Bindings. The binding document carries the
 * Expression and Build steps. A kind includes or omits a band; it never
 * invents a second section grammar. The content contract is
 * `DETAIL_CONTENT.md`.
 */

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
} from "react";
import {
  ArrowRight,
  BadgeCheck,
  ChevronDown,
  ChevronRight,
  Search,
  Waypoints,
} from "lucide-react";

import type { ConceptKind, ConceptReference } from "@/lib/concepts";
import type { WorkspaceProps, SubjectSelection } from "@/workbench/types";
import { documentTitle } from "@/workbench/types";
import {
  findComponentPropertyBindings,
  relationNamesFromRowSource,
  stepKey,
} from "@/lib/indexes";
import {
  buildWorkflowModel,
  groupWorkflowRows,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";
import {
  getWorkflowUiStore,
  useWorkflowUi,
} from "@/workflow/view/workflowUi";
import {
  effectiveLicense,
  effectiveLicenseForModel,
  type EffectiveLicense,
} from "@/proof/license";
import { ConceptGlyph, ConceptMark } from "@/shared/ui/ConceptMark";
import {
  BindingPill,
  EdgePill,
  NodePill,
  PropertyPill,
} from "@/detail/view/ConceptPill";
import { activeDocument, documentSelection } from "@/workbench/types";
import type {
  LineageLane,
  ViewerIndex,
} from "@/lib/types";
import { LINEAGE_LANES } from "@/lib/types";
import { collectFieldRefs, logicalTypeName } from "@/lib/expressions";
import {
  DetailBand,
  DetailDocument,
  DetailEmptyState,
  MemberTable,
  type DetailFact,
  type MemberRow,
} from "./view/DetailChrome";
import { DataItemEditor } from "./DataItemFeature";
import { BindingEditor } from "./BindingFeature";
import { CollectionEditor } from "./CollectionFeature";
import { COLLECTIONS, type CollectionId } from "@/workbench/collections";
import { ContextMenu } from "@/shared/ui/ContextMenu";
import { laneColor } from "@/shared/ui/theme";
import {
  branchLaneNodes,
  buildProof,
  defaultProofSubject,
  traceArtifactLabel,
  type ProofBranch,
  type ProofLevel,
  type ProofModel,
  type ProofNode,
  type ProofPropertySummary,
  type ProofSubject,
  type ProofTrace,
  type ProofTypeChain,
} from "@/proof/model";
import { Constitution } from "@/detail/view/Constitution";
import { ContributionSection } from "@/detail/view/Contribution";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import {
  constitutionModel,
  contributionModel,
} from "@/detail/model/constitution";
import {
  attachedMeaning,
  componentMeaning,
  propertyMeaning,
  type DesignMeaningValue,
} from "@/shared/design/meaning";
import styles from "./detail.module.css";
import { profileSummary, recordSummary } from "@/lib/summary";

// ---------------------------------------------------------------------------
// Selection plumbing
// ---------------------------------------------------------------------------

function toWorkbenchSelection(subject: ProofSubject): SubjectSelection {
  const base: SubjectSelection = {
    name:
      subject.level === "property"
        ? `${subject.component}.${subject.property ?? ""}`
        : subject.component,
    component: subject.component,
    level: subject.level,
  };
  switch (subject.level) {
    case "property":
      return {
        ...base,
        kind: "property",
        property: subject.property,
      };
    case "node":
      return { ...base, kind: "node" };
    case "edge":
      return { ...base, kind: "edge", abstract: subject.abstract };
    case "asset":
      return { ...base, kind: "asset" };
    case "abstract":
      return { ...base, kind: "node" };
  }
}

function useProofModel(props: WorkspaceProps): ProofModel {
  const selection = documentSelection(activeDocument(props.state));
  return useMemo(
    () => buildProof(props.state.index, selection),
    [props.state.index, selection],
  );
}


function levelTitle(model: ProofModel): string {
  switch (model.level) {
    case "property":
      return `${model.subject.component}.${model.subject.property ?? ""}`;
    case "node":
    case "edge":
      return model.subject.component;
    case "abstract":
      return model.abstract?.name ?? model.subject.component;
    case "asset":
      return model.asset?.name ?? model.subject.component;
  }
}


// ---------------------------------------------------------------------------
// Small shared pieces
// ---------------------------------------------------------------------------

function Badge({
  children,
  tone,
}: {
  children: ReactNode;
  tone?: "lane" | "muted" | "warn" | "ok";
}) {
  return (
    <span className={styles.badge} data-tone={tone ?? "muted"}>
      {children}
    </span>
  );
}

function EmptyState({ children }: { children: ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}

function TypeChainView({ chain }: { chain: ProofTypeChain }) {
  return (
    <div className={styles.subBlock}>
      <p className={styles.subHead}>
        <span>Type &amp; presence</span>
        <span className={styles.chainMeta}>
          {chain.mismatch ? (
            <Badge tone="warn">type mismatch</Badge>
          ) : (
            <Badge tone="ok">types agree</Badge>
          )}
          {chain.narrowed ? (
            <Badge tone="warn">present · source nullable</Badge>
          ) : null}
        </span>
      </p>
      <div className={styles.chain}>
        {chain.steps.map((step, index) => (
          <div key={step.id} className={styles.chainItem}>
            <div
              className={styles.chainStep}
              data-stage={step.stage}
              data-presence={step.presence}
              data-mismatch={step.mismatch ? "true" : undefined}
            >
              <span className={styles.chainStage}>{step.stage}</span>
              <span className={styles.chainType}>{step.typeName ?? "—"}</span>
              <span className={styles.chainLabel}>{step.label}</span>
              {step.detail ? (
                <span className={styles.chainDetail}>{step.detail}</span>
              ) : null}
              <span className={styles.chainPresence}>{step.presence}</span>
            </div>
            {index < chain.steps.length - 1 ? (
              <ArrowRight aria-hidden className={styles.chainArrow} />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

function matches(query: string, ...values: Array<string | undefined>): boolean {
  if (!query) return true;
  return values.some((value) => value?.toLowerCase().includes(query));
}

function SideSection({
  id,
  title,
  count,
  open,
  active,
  onToggle,
  onOpen,
  children,
}: {
  id: string;
  title: string;
  count: number;
  open: boolean;
  active?: boolean;
  onToggle(id: string): void;
  onOpen(id: string): void;
  children: ReactNode;
}) {
  return (
    <section className={styles.sideSection}>
      <div
        className={styles.sideSectionHead}
        data-active={active ? "true" : undefined}
      >
        <button
          type="button"
          className={styles.sideSectionToggle}
          aria-expanded={open}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          onClick={() => onToggle(id)}
          data-testid={`explorer-group-${id}-toggle`}
        >
          {open ? (
            <ChevronDown aria-hidden className={styles.sideChevron} />
          ) : (
            <ChevronRight aria-hidden className={styles.sideChevron} />
          )}
        </button>
        <button
          type="button"
          className={styles.sideSectionTitle}
          onClick={() => onOpen(id)}
          data-testid={`explorer-group-${id}`}
          title={`Open the ${title} collection`}
        >
          <span>{title}</span>
          <span className={styles.sideCount}>{count}</span>
        </button>
      </div>
      {open ? <div className={styles.sideSectionBody}>{children}</div> : null}
    </section>
  );
}

interface SidebarRowProps {
  label: string;
  meta?: ReactNode;
  concept?: ConceptKind;
  active?: boolean;
  abstract?: boolean;
  testId?: string;
  onSelect(): void;
  onOpenPermanent?(): void;
  onContextMenu?(event: ReactMouseEvent): void;
}

function SidebarRow({
  label,
  meta,
  concept,
  active,
  abstract,
  testId,
  onSelect,
  onOpenPermanent,
  onContextMenu,
}: SidebarRowProps) {
  return (
    <button
      type="button"
      className={styles.sideRow}
      data-active={active ? "true" : undefined}
      data-testid={testId}
      onClick={onSelect}
      onDoubleClick={onOpenPermanent ?? onSelect}
      onContextMenu={onContextMenu}
      title={label}
    >
      {concept ? (
        <ConceptGlyph concept={concept} className={styles.sideRowIcon} />
      ) : null}
      <span className={styles.sideRowLabel}>{label}</span>
      {abstract ? <span className={styles.sideAbstract}>abstract</span> : null}
      {meta ? <span className={styles.sideRowMeta}>{meta}</span> : null}
    </button>
  );
}

export function ExplorerSidebar(props: WorkspaceProps) {
  const { index } = props.state;
  const document = activeDocument(props.state);
  const active = documentSelection(document);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<Set<string>>(() => new Set());
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [menu, setMenu] = useState<
    | {
        x: number;
        y: number;
        label: string;
        items: Array<{ label: string; hint?: string; run(): void }>;
      }
    | undefined
  >(undefined);
  const normalized = query.trim().toLowerCase();
  const workflowRows = useMemo(() => buildWorkflowModel(index).rows, [index]);
  const filteredWorkflowRows = useMemo(
    () =>
      workflowRows.filter((row) =>
        matches(normalized, row.name, row.component, row.kindLabel),
      ),
    [workflowRows, normalized],
  );
  const workflowGroups = useMemo(
    () => groupWorkflowRows(filteredWorkflowRows),
    [filteredWorkflowRows],
  );
  const activeStepKey =
    active?.kind === "step" && active.stepId ? stepKey(active.stepId) : undefined;
  const activeStepComponent =
    active?.kind === "step"
      ? active.component ?? active.stepId?.[0]
      : undefined;
  const { state: workflowUi } = useWorkflowUi(props.state.snapshot.name);
  const focusedComponent = workflowUi.filters.component;
  const sectionOpen = (id: string) => open.has(id);
  const workflowSectionOpen = sectionOpen("workflow");

  // Reveal the active workflow context once when it changes. The reveal is a
  // one-shot state change, not a forced open: once the reader collapses the
  // section or group it stays collapsed until the context changes again.
  useEffect(() => {
    if (normalized) return;
    if (focusedComponent === "all" && !activeStepComponent) return;
    setOpen((current) => {
      if (current.has("workflow")) return current;
      const next = new Set(current);
      next.add("workflow");
      return next;
    });
    const component =
      activeStepComponent ??
      (focusedComponent !== "all" ? focusedComponent : undefined);
    if (!component) return;
    const groupKey = `wf:${component}`;
    setExpanded((current) => {
      if (current.has(groupKey)) return current;
      const next = new Set(current);
      next.add(groupKey);
      return next;
    });
  }, [normalized, focusedComponent, activeStepKey, activeStepComponent]);

  // Opening a binding from a pill should reveal its Explorer group once.
  useEffect(() => {
    if (normalized || active?.kind !== "binding") return;
    setOpen((current) => {
      if (current.has("bindings")) return current;
      const next = new Set(current);
      next.add("bindings");
      return next;
    });
  }, [normalized, active?.kind, active?.bindingIndex]);

  // Single-click navigation reuses one preview tab; an explicit open is permanent.
  const select = (next: ProofSubject) => {
    props.actions.openTab({ selection: toWorkbenchSelection(next), preview: true });
  };
  const openPermanent = (next: ProofSubject) => {
    props.actions.openTab({ selection: toWorkbenchSelection(next) });
  };
  const openActions = (
    event: ReactMouseEvent,
    label: string,
    items: Array<{ label: string; hint?: string; run(): void }>,
  ) => {
    event.preventDefault();
    event.stopPropagation();
    setMenu({ x: event.clientX, y: event.clientY, label, items });
  };
  const openMenu = (
    event: ReactMouseEvent,
    label: string,
    run: () => void,
  ) => {
    openActions(event, label, [
      { label: "Go to Detail", hint: "Open document", run },
    ]);
  };
  const goToGraph = (selection: SubjectSelection) => {
    props.actions.showGraph(selection);
  };
  const goToWorkflow = (component: string) => {
    getWorkflowUiStore(props.state.snapshot.name).setComponent(component);
    props.actions.showWorkflow();
  };
  const openStep = (row: WorkflowStepRow, preview: boolean) => {
    props.actions.openTab({
      selection: {
        kind: "step",
        component: row.component,
        name: row.name,
        stepId: row.id,
      },
      preview,
    });
  };
  const openDataItem = (
    kind: "relation" | "projection",
    name: string,
    preview: boolean,
  ) => {
    props.actions.openTab({
      selection: { kind, name, component: name },
      preview,
    });
  };
  const openBinding = (
    binding: ViewerIndex["bindings"][number],
    preview: boolean,
  ) => {
    props.actions.openTab({
      selection: {
        kind: "binding",
        component: binding.component,
        name: binding.binding.name ?? `binding #${binding.index}`,
        bindingIndex: binding.index,
      },
      preview,
    });
  };
  const sectionCollection = (id: string): CollectionId =>
    id === "tables"
      ? "sourceRelations"
      : id === "projections"
        ? "derivedRelations"
        : (id as CollectionId);
  const openCollection = (id: string, component?: string) => {
    const collection = sectionCollection(id);
    props.actions.openTab({
      selection: {
        kind: "collection",
        collection,
        component,
        name: component ?? COLLECTIONS[collection].title,
      },
      preview: true,
    });
  };
  const collectionActive = (id: string) => {
    const collection = sectionCollection(id);
    return (
      active?.kind === "collection" &&
      active.collection === collection &&
      !active.component
    );
  };
  const toggle = (id: string) => {
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const toggleNode = (name: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const assets = index.assets.filter((asset) => matches(normalized, asset.name));
  const tables = index.relations.filter((relation) =>
    matches(normalized, relation.name, recordSummary(relation)),
  );
  const projections = index.projections.filter((projection) =>
    matches(normalized, projection.name, recordSummary(projection)),
  );
  const nodes = index.topologyNodes.filter((node) =>
    matches(normalized, node.name) ||
    (node.properties ?? []).some((property) => matches(normalized, property.name)),
  );
  const edges = index.topologyEdges.filter((edge) =>
    matches(normalized, edge.name) ||
    (edge.properties ?? []).some((property) => matches(normalized, property.name)),
  );
  const bindings = index.bindings.filter((binding) =>
    matches(
      normalized,
      binding.binding.name,
      binding.component,
      binding.kind,
      `binding #${binding.index}`,
      String(binding.index),
    ),
  );
  const concreteNodes = nodes.filter((node) => !node.abstract);
  const abstractNodes = nodes.filter((node) => node.abstract);
  const concreteEdges = edges.filter((edge) => !edge.abstract);
  const abstractEdges = edges.filter((edge) => edge.abstract);

  // A filter reveals matching sections and rows once and records the folding
  // state it replaced. Clearing the filter restores that state, so a filter is
  // a temporary reading lens rather than a change to the tree.
  const filterFoldState = useRef<{
    open: Set<string>;
    expanded: Set<string>;
  } | null>(null);
  useEffect(() => {
    if (!normalized) {
      if (!filterFoldState.current) return;
      setOpen(new Set(filterFoldState.current.open));
      setExpanded(new Set(filterFoldState.current.expanded));
      filterFoldState.current = null;
      return;
    }
    if (!filterFoldState.current) {
      filterFoldState.current = {
        open: new Set(open),
        expanded: new Set(expanded),
      };
    }
    setOpen((current) => {
      const next = new Set(current);
      if (assets.length) next.add("assets");
      if (tables.length) next.add("tables");
      if (projections.length) next.add("projections");
      if (concreteNodes.length) next.add("nodes");
      if (abstractNodes.length || abstractEdges.length) next.add("abstract");
      if (concreteEdges.length) next.add("edges");
      if (bindings.length) next.add("bindings");
      if (filteredWorkflowRows.length) next.add("workflow");
      return next;
    });
    setExpanded((current) => {
      const next = new Set(current);
      for (const node of nodes) next.add(`node:${node.name}`);
      for (const edge of edges) next.add(`edge:${edge.name}`);
      for (const group of workflowGroups) next.add(`wf:${group.component}`);
      return next;
    });
  }, [normalized]);

  const isActive = (
    level: ProofLevel,
    component: string,
    property?: string,
  ): boolean =>
    active?.level === level &&
    active.component === component &&
    (property === undefined || active.property === property);

  const renderNode = (node: (typeof nodes)[number]) => {
    const nodeOpen = expanded.has(`node:${node.name}`);
    const properties = (node.properties ?? []).filter((property) =>
      matches(normalized, property.name, node.name),
    );
    const nodeLevel: ProofLevel = node.abstract ? "abstract" : "node";
    const nodeKind: ProofSubject["kind"] = node.abstract ? "abstract" : "node";
    return (
      <div key={`node:${node.name}`} className={styles.treeBlock}>
        <div
          className={styles.treeRow}
          data-active={
            isActive(nodeLevel, node.name) ? "true" : undefined
          }
        >
          <button
            type="button"
            className={styles.treeToggle}
            aria-label={`${nodeOpen ? "Collapse" : "Expand"} ${node.name}`}
            aria-expanded={nodeOpen}
            onClick={() => toggleNode(`node:${node.name}`)}
          >
            {nodeOpen ? (
              <ChevronDown aria-hidden className={styles.sideChevron} />
            ) : (
              <ChevronRight aria-hidden className={styles.sideChevron} />
            )}
          </button>
          <button
            type="button"
            className={styles.treeLabel}
            data-testid={node.abstract ? "detail-tree-abstract" : "detail-tree-node"}
            data-concept={node.abstract ? "abstractNode" : "node"}
            onClick={() =>
              select({
                level: nodeLevel,
                kind: nodeKind,
                component: node.name,
              })
            }
            onDoubleClick={() =>
              openPermanent({
                level: nodeLevel,
                kind: nodeKind,
                component: node.name,
              })
            }
            onContextMenu={(event) =>
              openActions(event, node.name, [
                {
                  label: "Go to Detail",
                  hint: "Open document",
                  run: () =>
                    openPermanent({
                      level: nodeLevel,
                      kind: nodeKind,
                      component: node.name,
                    }),
                },
                {
                  label: "Go to Graph",
                  hint: "Inspect",
                  run: () =>
                    goToGraph({
                      kind: "node",
                      level: nodeLevel,
                      component: node.name,
                      name: node.name,
                    }),
                },
              ])
            }
            title={node.name}
          >
            <ConceptGlyph
              concept={node.abstract ? "abstractNode" : "node"}
              className={styles.sideRowIcon}
            />
            <span>{node.name}</span>
            <span className={styles.treeMeta}>
              {node.properties?.length ?? 0}
            </span>
          </button>
        </div>
        {nodeOpen && properties.length ? (
          <div className={styles.treeChildren}>
            {properties.map((property) => (
              <button
                key={`${node.name}.${property.name}`}
                type="button"
                className={styles.propertyRow}
                data-testid="detail-tree-property"
                data-active={
                  isActive("property", node.name, property.name)
                    ? "true"
                    : undefined
                }
                onClick={() =>
                  select({
                    level: "property",
                    kind: "node",
                    component: node.name,
                    property: property.name,
                    propertyRef: property.ref,
                  })
                }
                onDoubleClick={() =>
                  openPermanent({
                    level: "property",
                    kind: "node",
                    component: node.name,
                    property: property.name,
                    propertyRef: property.ref,
                  })
                }
                onContextMenu={(event) =>
                  openActions(event, `${node.name}.${property.name}`, [
                    {
                      label: "Go to Detail",
                      hint: "Open document",
                      run: () =>
                        openPermanent({
                          level: "property",
                          kind: "node",
                          component: node.name,
                          property: property.name,
                          propertyRef: property.ref,
                        }),
                    },
                    {
                      label: "Go to Graph",
                      hint: "Inspect",
                      run: () =>
                        goToGraph({
                          kind: "property",
                          level: "property",
                          component: node.name,
                          property: property.name,
                          name: `${node.name}.${property.name}`,
                        }),
                    },
                  ])
                }
              >
                <ConceptGlyph concept="property" className={styles.conceptDot} />
                <span>{property.name}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  };

  const renderEdge = (edge: (typeof edges)[number]) => {
    const edgeOpen = expanded.has(`edge:${edge.name}`);
    const edgeConcept = edge.abstract ? "abstractEdge" : "edge";
    const properties = (edge.properties ?? []).filter((property) =>
      matches(normalized, property.name, edge.name),
    );
    return (
      <div key={`edge:${edge.name}`} className={styles.treeBlock}>
        <div
          className={styles.treeRow}
          data-active={
            isActive("edge", edge.name) ? "true" : undefined
          }
        >
          <button
            type="button"
            className={styles.treeToggle}
            aria-label={`${edgeOpen ? "Collapse" : "Expand"} ${edge.name}`}
            aria-expanded={edgeOpen}
            onClick={() => toggleNode(`edge:${edge.name}`)}
          >
            {edgeOpen ? (
              <ChevronDown aria-hidden className={styles.sideChevron} />
            ) : (
              <ChevronRight aria-hidden className={styles.sideChevron} />
            )}
          </button>
          <button
            type="button"
            className={styles.treeLabel}
            data-testid="detail-tree-edge"
            data-concept={edgeConcept}
            onClick={() =>
              select({
                level: "edge",
                kind: "edge",
                component: edge.name,
                abstract: edge.abstract,
              })
            }
            onDoubleClick={() =>
              openPermanent({
                level: "edge",
                kind: "edge",
                component: edge.name,
                abstract: edge.abstract,
              })
            }
            onContextMenu={(event) =>
              openActions(event, edge.name, [
                {
                  label: "Go to Detail",
                  hint: "Open document",
                  run: () =>
                    openPermanent({
                      level: "edge",
                      kind: "edge",
                      component: edge.name,
                      abstract: edge.abstract,
                    }),
                },
                {
                  label: "Go to Graph",
                  hint: "Inspect",
                  run: () =>
                    goToGraph({
                      kind: "edge",
                      level: "edge",
                      component: edge.name,
                      name: edge.name,
                      abstract: edge.abstract,
                    }),
                },
              ])
            }
            title={edge.name}
          >
            <ConceptGlyph concept={edgeConcept} className={styles.sideRowIcon} />
            <span>{edge.name}</span>
            <span className={styles.treeMeta}>
              {edge.properties?.length ?? 0}
            </span>
          </button>
        </div>
        {edgeOpen && properties.length ? (
          <div className={styles.treeChildren}>
            {properties.map((property) => (
              <button
                key={`${edge.name}.${property.name}`}
                type="button"
                className={styles.propertyRow}
                data-active={
                  isActive("property", edge.name, property.name)
                    ? "true"
                    : undefined
                }
                onClick={() =>
                  select({
                    level: "property",
                    kind: "edge",
                    component: edge.name,
                    property: property.name,
                    propertyRef: property.ref,
                  })
                }
                onDoubleClick={() =>
                  openPermanent({
                    level: "property",
                    kind: "edge",
                    component: edge.name,
                    property: property.name,
                    propertyRef: property.ref,
                  })
                }
                onContextMenu={(event) =>
                  openActions(event, `${edge.name}.${property.name}`, [
                    {
                      label: "Go to Detail",
                      hint: "Open document",
                      run: () =>
                        openPermanent({
                          level: "property",
                          kind: "edge",
                          component: edge.name,
                          property: property.name,
                          propertyRef: property.ref,
                        }),
                    },
                    {
                      label: "Go to Graph",
                      hint: "Inspect",
                      run: () =>
                        goToGraph({
                          kind: "property",
                          level: "property",
                          component: edge.name,
                          property: property.name,
                          name: `${edge.name}.${property.name}`,
                        }),
                    },
                  ])
                }
              >
                <ConceptGlyph concept="property" className={styles.conceptDot} />
                <span>{property.name}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className={styles.sidebar} data-testid="explorer-sidebar">
      <div className={styles.search}>
        <Search aria-hidden className={styles.searchIcon} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter the design"
          aria-label="Filter the explorer"
          spellCheck={false}
        />
      </div>
      <div className={`${styles.sideScroll} thin-scrollbar`}>
        <SideSection
          id="assets"
          title="Assets"
          count={assets.length}
          open={sectionOpen("assets")}
          onToggle={toggle}
          onOpen={openCollection}
          active={collectionActive("assets")}
        >
          {assets.map((asset) => (
            <SidebarRow
              key={asset.name}
              label={asset.name}
              concept="asset"
              meta={index.assetProfilesByName.get(asset.name)?.subject}
              active={isActive("asset", asset.name)}
              onSelect={() =>
                select({ level: "asset", kind: "asset", component: asset.name })
              }
              onOpenPermanent={() =>
                openPermanent({
                  level: "asset",
                  kind: "asset",
                  component: asset.name,
                })
              }
              onContextMenu={(event) =>
                openMenu(event, asset.name, () =>
                  openPermanent({
                    level: "asset",
                    kind: "asset",
                    component: asset.name,
                  }),
                )
              }
            />
          ))}
        </SideSection>

        <SideSection
          id="tables"
          title="Source relations"
          count={tables.length}
          open={sectionOpen("tables")}
          onToggle={toggle}
          onOpen={openCollection}
          active={collectionActive("tables")}
        >
          {tables.map((table) => {
            return (
              <SidebarRow
                key={table.name}
                label={table.name}
                concept="table"
                meta={`${table.columns?.length ?? 0} columns`}
                active={
                  active?.kind === "relation" &&
                  active.component === table.name
                }
                onSelect={() => openDataItem("relation", table.name, true)}
                onOpenPermanent={() =>
                  openDataItem("relation", table.name, false)
                }
              />
            );
          })}
        </SideSection>

        <SideSection
          id="projections"
          title="Derived relations"
          count={projections.length}
          open={sectionOpen("projections")}
          onToggle={toggle}
          onOpen={openCollection}
          active={collectionActive("projections")}
        >
          {projections.map((projection) => {
            return (
              <SidebarRow
                key={projection.name}
                label={projection.name}
                concept="projection"
                meta={`${projection.columns?.length ?? 0} columns`}
                active={
                  active?.kind === "projection" &&
                  active.component === projection.name
                }
                onSelect={() =>
                  openDataItem("projection", projection.name, true)
                }
                onOpenPermanent={() =>
                  openDataItem("projection", projection.name, false)
                }
              />
            );
          })}
        </SideSection>

        <SideSection
          id="nodes"
          title="Nodes"
          count={concreteNodes.length}
          open={sectionOpen("nodes")}
          onToggle={toggle}
          onOpen={openCollection}
          active={collectionActive("nodes")}
        >
          {concreteNodes.map(renderNode)}
        </SideSection>

        <SideSection
          id="abstract"
          title="Abstract"
          count={abstractNodes.length + abstractEdges.length}
          open={sectionOpen("abstract")}
          onToggle={toggle}
          onOpen={openCollection}
          active={collectionActive("abstract")}
        >
          {abstractNodes.map(renderNode)}
          {abstractEdges.map(renderEdge)}
        </SideSection>

        <SideSection
          id="edges"
          title="Edges"
          count={concreteEdges.length}
          open={sectionOpen("edges")}
          onToggle={toggle}
          onOpen={openCollection}
          active={collectionActive("edges")}
        >
          {concreteEdges.map(renderEdge)}
        </SideSection>

        <SideSection
          id="bindings"
          title="Bindings"
          count={bindings.length}
          open={sectionOpen("bindings")}
          onToggle={toggle}
          onOpen={openCollection}
          active={collectionActive("bindings")}
        >
          {bindings.map((binding) => (
            <SidebarRow
              key={`binding:${binding.index}`}
              testId="explorer-binding"
              label={binding.binding.name ?? `binding #${binding.index}`}
              concept="binding"
              meta={`${binding.kind} · ${binding.component}`}
              active={
                active?.kind === "binding" &&
                active.bindingIndex === binding.index
              }
              onSelect={() => openBinding(binding, true)}
              onOpenPermanent={() => openBinding(binding, false)}
            />
          ))}
        </SideSection>

        <SideSection
          id="workflow"
          title="Workflow"
          count={filteredWorkflowRows.length}
          open={workflowSectionOpen}
          onToggle={toggle}
          onOpen={openCollection}
          active={collectionActive("workflow")}
        >
          {workflowGroups.length ? (
            workflowGroups.map((group) => {
              const groupKey = `wf:${group.component}`;
              const groupOpen = expanded.has(groupKey);
              return (
                <div key={groupKey} className={styles.treeBlock}>
                  <div className={styles.treeRow}>
                    <button
                      type="button"
                      className={styles.treeToggle}
                      aria-label={`${groupOpen ? "Collapse" : "Expand"} ${group.component}`}
                      aria-expanded={groupOpen}
                      data-testid="explorer-workflow-toggle"
                      data-component={group.component}
                      onClick={() => toggleNode(groupKey)}
                    >
                      {groupOpen ? (
                        <ChevronDown aria-hidden className={styles.sideChevron} />
                      ) : (
                        <ChevronRight aria-hidden className={styles.sideChevron} />
                      )}
                    </button>
                    <button
                      type="button"
                      className={styles.treeLabel}
                      data-testid="explorer-workflow-component"
                      data-component={group.component}
                      data-active={
                        active?.kind === "collection" &&
                        active.collection === "workflow" &&
                        active.component === group.component
                          ? "true"
                          : undefined
                      }
                      onClick={() =>
                        openCollection("workflow", group.component)
                      }
                      onContextMenu={(event) =>
                        openActions(event, group.component, [
                          {
                            label: "Go to Workflow",
                            hint: "Show component",
                            run: () => goToWorkflow(group.component),
                          },
                        ])
                      }
                      title={group.component}
                    >
                      <ConceptGlyph
                        concept="workflow"
                        className={styles.sideRowIcon}
                      />
                      <span>{group.component}</span>
                      <span className={styles.treeMeta}>
                        {group.rows.length}
                      </span>
                    </button>
                  </div>
                  {groupOpen ? (
                    <div className={styles.treeChildren}>
                      {group.rows.map((row) => (
                        <button
                          key={row.key}
                          type="button"
                          className={styles.propertyRow}
                          data-testid="explorer-step"
                          data-active={
                            activeStepKey === row.key ? "true" : undefined
                          }
                          onClick={() => openStep(row, true)}
                          onDoubleClick={() => openStep(row, false)}
                          onContextMenu={(event) =>
                            openActions(event, row.name, [
                              {
                                label: "Go to Detail",
                                hint: "Open document",
                                run: () => openStep(row, false),
                              },
                              {
                                label: "Go to Workflow",
                                hint: "Show component",
                                run: () => goToWorkflow(row.component),
                              },
                            ])
                          }
                          title={`${row.component} · ${row.name}`}
                        >
                          <ConceptGlyph
                            concept="step"
                            className={styles.conceptDot}
                          />
                          <span>{row.name}</span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })
          ) : (
            <p className={styles.sideEmpty}>
              No workflow steps match this filter.
            </p>
          )}
        </SideSection>
      </div>

      {menu ? (
        <ContextMenu
          x={menu.x}
          y={menu.y}
          label={menu.label}
          items={menu.items.map((item) => ({
            label: item.label,
            hint: item.hint,
            onSelect: item.run,
          }))}
          onClose={() => setMenu(undefined)}
        />
      ) : null}

      <footer className={styles.sideFooter}>
        <span className={styles.sideFooterLabel}>Selection</span>
        <span className={styles.sideFooterValue}>
          {document.kind === "graph" ? "Graph" : documentTitle(document)}
        </span>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor header
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Canvas
// ---------------------------------------------------------------------------

const LANE_WIDTH = 202;
const NODE_WIDTH = 176;
const NODE_HEIGHT = 64;
const ROW_GAP = 14;
const HEADER_HEIGHT = 28;
const PAD = 12;

interface NodePosition {
  x: number;
  y: number;
}

function LaneCanvas({ branch }: { branch: ProofBranch }) {
  const laneNodes = branchLaneNodes(branch);
  const rows = Math.max(
    1,
    ...LINEAGE_LANES.map((lane) => laneNodes.get(lane.id)?.length ?? 0),
  );
  const width = PAD * 2 + LANE_WIDTH * LINEAGE_LANES.length;
  const height = HEADER_HEIGHT + PAD * 2 + rows * (NODE_HEIGHT + ROW_GAP);
  const positions = new Map<string, NodePosition>();

  for (const [laneIndex, lane] of LINEAGE_LANES.entries()) {
    const nodes = laneNodes.get(lane.id) ?? [];
    for (const [rowIndex, node] of nodes.entries()) {
      positions.set(node.id, {
        x: PAD + laneIndex * LANE_WIDTH + (LANE_WIDTH - NODE_WIDTH) / 2,
        y: HEADER_HEIGHT + PAD + rowIndex * (NODE_HEIGHT + ROW_GAP),
      });
    }
  }

  const nodeById = new Map(branch.nodes.map((node) => [node.id, node]));

  return (
    <div className={styles.canvasShell}>
      <div className={`${styles.canvasScroll} thin-scrollbar`}>
        <div className={styles.canvas} style={{ width, height }}>
          {LINEAGE_LANES.map((lane, laneIndex) => (
            <div
              key={lane.id}
              className={styles.laneHeader}
              style={{
                left: PAD + laneIndex * LANE_WIDTH,
                width: NODE_WIDTH,
                top: 0,
              }}
            >
              <span>{lane.label}</span>
              <span>{laneNodes.get(lane.id)?.length ?? 0}</span>
            </div>
          ))}
          <svg
            className={styles.wires}
            width={width}
            height={height}
            aria-hidden
          >
            <defs>
              <marker
                id="proof-arrow"
                viewBox="0 0 8 8"
                refX="7"
                refY="4"
                markerWidth="7"
                markerHeight="7"
                orient="auto"
              >
                <path d="M0,0 L8,4 L0,8 z" fill="var(--color-edge)" />
              </marker>
            </defs>
            {branch.edges.map((edge) => {
              const source = positions.get(edge.source);
              const target = positions.get(edge.target);
              if (!source || !target) return null;
              const x1 = source.x + NODE_WIDTH;
              const y1 = source.y + NODE_HEIGHT / 2;
              const x2 = target.x;
              const y2 = target.y + NODE_HEIGHT / 2;
              const bend = Math.max(34, Math.abs(x2 - x1) * 0.45);
              const path =
                x2 >= x1
                  ? `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`
                  : `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`;
              return (
                <path
                  key={edge.id}
                  d={path}
                  className={styles.wire}
                  markerEnd="url(#proof-arrow)"
                >
                  {edge.label ? <title>{edge.label}</title> : null}
                </path>
              );
            })}
          </svg>
          {branch.nodes.map((node) => {
            const position = positions.get(node.id);
            if (!position) return null;
            return (
              <LaneNode
                key={node.id}
                node={node}
                position={position}
                selected={node.kind === "property"}
              />
            );
          })}
        </div>
      </div>
      <div className={styles.canvasLegend}>
        <span>
          <Waypoints aria-hidden className={styles.legendIcon} />
          {branch.edges.length} edges · {branch.nodes.length} nodes
        </span>
        <span className={styles.legendHint}>
          {nodeById.size} semantic and workflow nodes in this branch
        </span>
      </div>
    </div>
  );
}

function LaneNode({
  node,
  position,
  selected,
}: {
  node: ProofNode;
  position: NodePosition;
  selected: boolean;
}) {
  const style = {
    left: position.x,
    top: position.y,
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
    "--lane-color": laneColor[node.lane],
  } as CSSProperties;
  return (
    <div
      className={styles.node}
      style={style}
      data-kind={node.kind}
      data-selected={selected ? "true" : undefined}
      title={`${node.label}${node.metadata.description ? ` — ${node.metadata.description}` : ""}`}
    >
      <span className={styles.nodeStripe} aria-hidden />
      <div className={styles.nodeHead}>
        <span className={styles.nodeLane}>{node.lane}</span>
        <span className={styles.nodeKind}>{node.kind}</span>
        {node.semantics.length ? (
          <span
            className={styles.nodeEvidence}
            title={`${node.semantics.length} attached meaning units`}
          >
            {node.semantics.length}
          </span>
        ) : null}
      </div>
      <p className={styles.nodeLabel}>{node.label}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Property level
// ---------------------------------------------------------------------------

function BranchBar({
  branches,
  active,
  onChange,
}: {
  branches: ProofBranch[];
  active: number;
  onChange(index: number): void;
}) {
  return (
    <div className={styles.branchBar}>
      <span className={styles.toolLabel}>Branch</span>
      <div className={styles.branchPills}>
        {branches.map((branch, index) => (
          <button
            key={branch.key}
            type="button"
            className={styles.branchPill}
            data-active={index === active ? "true" : undefined}
            onClick={() => onChange(index)}
            title={branch.label}
          >
            <span className={styles.branchIndex}>
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className={styles.branchLabel}>{branch.label}</span>
          </button>
        ))}
      </div>
      <span className={styles.branchCount}>
        {branches.length} {branches.length === 1 ? "source" : "sources"}
      </span>
    </div>
  );
}

function ConnectionLedger({ branch }: { branch: ProofBranch }) {
  const labels = new Map(branch.nodes.map((node) => [node.id, node.label]));
  if (!branch.edges.length) {
    return <DetailEmptyState>No edges in this branch.</DetailEmptyState>;
  }
  return (
    <div className={styles.edgeList}>
      {branch.edges.map((edge) => (
        <div key={edge.id} className={styles.edgeRow}>
          <span className={styles.edgeEndpoint}>
            {labels.get(edge.source) ?? edge.source}
          </span>
          <ArrowRight aria-hidden className={styles.edgeArrow} />
          <span className={styles.edgeEndpoint}>
            {labels.get(edge.target) ?? edge.target}
          </span>
          {edge.label ? (
            <span className={styles.edgeLabel}>{edge.label}</span>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function identityFields(
  index: ViewerIndex,
  kind: "node" | "edge",
  component: string,
): string[] {
  const fields = new Set<string>();
  for (const binding of index.bindings) {
    if (binding.kind !== kind || binding.component !== component) continue;
    for (const ref of collectFieldRefs(binding.binding.identity)) {
      const name = ref[ref.length - 1];
      if (name) fields.add(name);
    }
  }
  return [...fields];
}

function componentBindings(
  index: ViewerIndex,
  kind: "node" | "edge",
  component: string,
) {
  return index.bindings.filter(
    (binding) => binding.kind === kind && binding.component === component,
  );
}

function BindingsSection({
  bindings,
}: {
  bindings: ViewerIndex["bindings"];
}) {
  const rows: MemberRow[] = bindings.map((binding) => {
    const fields = collectFieldRefs(binding.binding.identity)
      .map((ref) => ref[ref.length - 1])
      .filter(Boolean);
    const relations = relationNamesFromRowSource(binding.binding.rows);
    return {
      key: String(binding.index),
      cells: [
        <BindingPill
          name={binding.binding.name ?? `binding #${binding.index}`}
          component={binding.component}
          ownerConcept={binding.kind}
          bindingIndex={binding.index}
        />,
        `${Object.keys(binding.binding.properties ?? {}).length}`,
        fields.join(", ") || "not declared",
        relations.join(", ") || "no row source",
      ],
    };
  });
  return (
    <DetailBand
      title="Bindings"
      question="Which binding fulfils this subject?"
      testId="detail-bindings"
    >
      <MemberTable
        columns={["Binding", "Writes", "Identity", "Rows read"]}
        template="minmax(170px, 1.5fr) 64px minmax(120px, 1fr) minmax(130px, 1.2fr)"
        rows={rows}
        empty="No binding produces this subject."
      />
    </DetailBand>
  );
}

function ConnectionsSection({
  index,
  kind,
  component,
}: {
  index: ViewerIndex;
  kind: "node" | "edge";
  component: string;
}) {
  if (kind === "edge") {
    const edge = index.topologyEdgesByName.get(component);
    if (!edge) return null;
    const source = edge.source?.[2];
    const target = edge.target?.[2];
    return (
      <DetailBand
        title="Connections"
        question="Which records does this relation join?"
      >
        <div className={styles.connectionRow}>
          <span>source</span>
          {source ? (
            <NodePill name={source} />
          ) : (
            <span>not resolved</span>
          )}
          <ArrowRight aria-hidden className={styles.inlineArrow} />
          <span>target</span>
          {target ? (
            <NodePill name={target} />
          ) : (
            <span>not resolved</span>
          )}
          <span className={styles.connectionLabel}>
            {(edge.labels ?? []).join(" · ")}
          </span>
        </div>
      </DetailBand>
    );
  }
  const incident = index.topologyEdges.filter(
    (edge) => edge.source?.[2] === component || edge.target?.[2] === component,
  );
  return (
    <DetailBand
      title="Connections"
      question="Which relations touch this record?"
    >
      {incident.length ? (
        incident.map((edge) => {
          const source = edge.source?.[2] ?? "?";
          const target = edge.target?.[2] ?? "?";
          const other = source === component ? target : source;
          const outgoing = source === component;
          return (
            <div className={styles.connectionRow} key={edge.name}>
              <span>{outgoing ? "out" : "in"}</span>
              {outgoing ? (
                <NodePill name={component} />
              ) : (
                <NodePill name={other} />
              )}
              <ArrowRight aria-hidden className={styles.inlineArrow} />
              {outgoing ? (
                <NodePill name={other} />
              ) : (
                <NodePill name={component} />
              )}
              <span className={styles.connectionLabel}>
                <EdgePill name={edge.name} />
              </span>
            </div>
          );
        })
      ) : (
        <DetailEmptyState>No relation touches this record.</DetailEmptyState>
      )}
    </DetailBand>
  );
}

function PropertyProofView({ model }: { model: ProofModel }) {
  const [activeBranch, setActiveBranch] = useState(0);
  useEffect(() => {
    setActiveBranch(0);
  }, [model.property?.component, model.property?.property]);

  const branch = model.branches[activeBranch] ?? model.branches[0];

  if (!branch) {
    return (
      <DetailBand
        title="Branches"
        question="Which bindings resolve this property?"
      >
        <p className={styles.inlineEmpty}>
          The topology property is declared, but no blueprint binding resolves
          it to a source.
        </p>
      </DetailBand>
    );
  }

  return (
    <div className={styles.levelBody}>
      <DetailBand
        title="Branches"
        question="Which bindings resolve this property?"
        flush
      >
        <div className={styles.workToolbar}>
          <BranchBar
            branches={model.branches}
            active={activeBranch}
            onChange={setActiveBranch}
          />
        </div>

        <TypeChainView chain={branch.typeChain} />

        <LaneCanvas branch={branch} />
      </DetailBand>

      <DetailBand
        concept="edge"
        title="Connections"
        question="Which links does this branch assert?"
      >
        <ConnectionLedger branch={branch} />
      </DetailBand>
    </div>
  );
}

function ComponentProofView({
  index,
  model,
}: {
  index: ViewerIndex;
  model: ProofModel;
}) {
  const component = model.component;
  if (!component) {
    return (
      <DetailEmptyState>
        This component is not present in the blueprint.
      </DetailEmptyState>
    );
  }
  const rows: MemberRow[] = component.properties.map((property) => ({
    key: `${property.kind}:${property.component}.${property.property}`,
    testId: "detail-property",
    cells: [
      <PropertyPill
        name={property.property}
        component={property.component}
        property={property.property}
        ownerConcept={property.kind}
      />,
      logicalTypeName(property.logicalType),
      `${property.branchCount}`,
      property.sources.join(", ") || "—",
    ],
  }));
  return (
    <div className={styles.levelBody}>
      <DetailBand
        title="Members"
        question="Which properties does this record assert?"
        testId="detail-properties"
      >
        <MemberTable
          columns={["Property", "Type", "Branches", "Sources"]}
          template="minmax(160px, 1.3fr) minmax(110px, 1fr) 64px minmax(100px, 1fr)"
          rows={rows}
          empty="No properties are declared for this subject."
        />
      </DetailBand>
      <ConnectionsSection
        index={index}
        kind={component.kind}
        component={component.name}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor export
// ---------------------------------------------------------------------------

function subjectMeaning(
  index: WorkspaceProps["state"]["index"],
  model: ProofModel,
): DesignMeaningValue {
  switch (model.level) {
    case "property":
      if (
        model.subject.kind === "node" ||
        model.subject.kind === "edge"
      ) {
        return propertyMeaning(
          index,
          model.subject.kind,
          model.subject.component,
          model.subject.property ?? "",
        );
      }
      return attachedMeaning(undefined);
    case "node":
    case "edge":
      return componentMeaning(index, model.level, model.subject.component);
    case "abstract":
      return componentMeaning(index, "node", model.subject.component);
    case "asset":
      return attachedMeaning(
        index.assetsByName.get(model.subject.component)?.semantics,
      );
  }
}

export function DetailEditor(props: WorkspaceProps) {
  const selection = documentSelection(activeDocument(props.state));
  if (selection?.kind === "collection") {
    return <CollectionEditor {...props} />;
  }
  if (selection?.kind === "binding") {
    return <BindingEditor {...props} />;
  }
  if (selection?.kind === "relation" || selection?.kind === "projection") {
    return <DataItemEditor {...props} />;
  }
  return <SubjectDetailEditor {...props} />;
}

function subjectLicense(
  index: ViewerIndex,
  model: ProofModel,
): EffectiveLicense {
  if (model.level === "asset") {
    return effectiveLicense(index, [
      model.asset?.name ?? model.subject.component,
    ]);
  }
  if (model.level === "abstract") {
    return effectiveLicense(
      index,
      (model.abstract?.descendants ?? []).flatMap((descendant) =>
        descendant.properties.flatMap((property) => property.assets),
      ),
    );
  }
  return effectiveLicenseForModel(index, model);
}

function overviewFacts(
  index: ViewerIndex,
  model: ProofModel,
  license: EffectiveLicense,
): DetailFact[] {
  const facts: DetailFact[] = [];
  const licenseFact: DetailFact = {
    label: "License",
    value: license.value,
    title: license.licenses.join(" · ") || "No asset declares a license.",
  };
  switch (model.level) {
    case "property": {
      const chain = model.typeChain;
      facts.push(
        {
          label: "Owner",
          value: index.topologyNodesByName.has(model.subject.component) ? (
            <NodePill name={model.subject.component} />
          ) : (
            <EdgePill name={model.subject.component} />
          ),
        },
        {
          label: "Type",
          value: chain?.steps.at(0)?.typeName ?? "unknown",
        },
        {
          label: "Presence",
          value: chain?.narrowed
            ? "present · source nullable"
            : chain?.steps.at(0)?.presence ?? "unknown",
          absent: !chain,
        },
        licenseFact,
      );
      break;
    }
    case "node":
    case "edge": {
      const component = model.component;
      const identity = component
        ? identityFields(index, component.kind, component.name)
        : [];
      facts.push(
        {
          label: "Labels",
          value: component?.labels.length
            ? component.labels.join(" · ")
            : "no labels",
          absent: !component?.labels.length,
        },
        {
          label: "Identity",
          value: identity.length ? identity.join(", ") : "not declared",
          absent: !identity.length,
        },
      );
      if (model.level === "edge") {
        const edge = index.topologyEdgesByName.get(model.subject.component);
        const source = edge?.source?.[2];
        const target = edge?.target?.[2];
        facts.push({
          label: "Endpoints",
          value:
            source && target ? (
              <span className="inline-flex flex-wrap items-center gap-1">
                <NodePill name={source} />
                <span aria-hidden>→</span>
                <NodePill name={target} />
              </span>
            ) : (
              "not resolved"
            ),
          absent: !source || !target,
        });
      }
      facts.push(licenseFact);
      break;
    }
    case "abstract": {
      facts.push(
        {
          label: "Labels",
          value: model.abstract?.labels.length
            ? model.abstract.labels.join(" · ")
            : "no labels",
          absent: !model.abstract?.labels.length,
        },
        licenseFact,
      );
      break;
    }
    case "asset": {
      const asset = model.asset;
      const profile = asset?.profile;
      facts.push(
        {
          label: "Version",
          value: index.assetsByName.get(model.subject.component)?.version ?? "—",
          absent: !index.assetsByName.get(model.subject.component)?.version,
        },
        {
          label: "Authority",
          value: profile?.authority ?? "not declared",
          absent: !profile?.authority,
        },
        {
          label: "Coverage",
          value: profile?.coverage ?? "not declared",
          absent: !profile?.coverage,
        },
        {
          label: "Layout",
          value:
            index.assetsByName.get(model.subject.component)?.layout?.kind ??
            "unspecified",
          absent: !index.assetsByName.get(model.subject.component)?.layout?.kind,
        },
        {
          label: "Location",
          value:
            index.assetsByName.get(model.subject.component)?.layout?.locator ??
            "not recorded",
          title:
            index.assetsByName.get(model.subject.component)?.layout?.locator ??
            undefined,
          absent:
            !index.assetsByName.get(model.subject.component)?.layout?.locator,
        },
        licenseFact,
      );
      break;
    }
  }
  return facts;
}

function SubjectDetailEditor(props: WorkspaceProps) {
  const index = props.state.index;
  const model = useProofModel(props);
  const selection = documentSelection(activeDocument(props.state));
  const meaning = subjectMeaning(index, model);
  const constitutionalSubject = useMemo(
    () =>
      selection?.abstract
        ? { ...model.subject, abstract: true }
        : model.subject,
    [model.subject, selection?.abstract],
  );
  const constitution = useMemo(
    () => constitutionModel(index, constitutionalSubject),
    [index, constitutionalSubject],
  );
  const contribution = useMemo(
    () => contributionModel(index, constitutionalSubject),
    [index, constitutionalSubject],
  );
  const license = subjectLicense(index, model);
  const facts = useMemo(
    () => overviewFacts(index, model, license),
    [index, model, license],
  );
  useEffect(() => {
    if (selection) return;
    props.actions.setSelection(
      toWorkbenchSelection(defaultProofSubject(props.state.index)),
    );
  }, [props.actions, props.state.index, selection]);

  const propertyBindings =
    model.level === "property"
      ? findComponentPropertyBindings(
          index,
          index.topologyNodesByName.has(model.subject.component)
            ? "node"
            : "edge",
          model.subject.component,
          model.subject.property ?? "",
        )
          .map((entry) => entry.binding)
          .filter(
            (binding, position, all) =>
              all.findIndex((other) => other.index === binding.index) ===
              position,
          )
      : [];
  const bindings =
    model.level === "node" || model.level === "edge"
      ? componentBindings(index, model.level, model.subject.component)
      : propertyBindings;

  const constitutionSection = (
    <DetailBand
      concept="semantics"
      title="Constitution"
      question="What is this subject for, and how does it come to be?"
      testId="detail-constitution"
    >
      <Constitution model={constitution} />
    </DetailBand>
  );
  const meaningSection = (
    <DetailBand
      concept="semantics"
      title="Meaning"
      question="What is this for, and what does it exclude?"
      testId="detail-meaning"
    >
      <DesignMeaning
        claims={meaning.claims}
        limitations={meaning.limitations}
        purpose={meaning.purpose}
        frames={meaning.frames}
        emptyText="Meaning omitted for this subject."
      />
    </DetailBand>
  );
  const kindSection = (
    <>
      {model.level === "property" ? (
        <PropertyProofView model={model} />
      ) : model.level === "asset" || model.level === "abstract" ? null : (
        <ComponentProofView index={index} model={model} />
      )}
    </>
  );
  const contributionSection = <ContributionSection model={contribution} />;
  const bindingsSection = (
    <>

      {bindings.length ? (
        <BindingsSection bindings={bindings} />
      ) : null}

    </>
  );

  return (
    <DetailDocument
      testId="detail-editor"
      concept={
        model.level === "abstract"
          ? "abstractNode"
          : selection?.abstract && model.level === "edge"
            ? "abstractEdge"
            : model.level
      }
      kicker={model.level}
      title={levelTitle(model)}
      subtitle={
        model.component?.description ??
        model.abstract?.description ??
        profileSummary(model.asset?.profile)
      }
      facts={facts}
    >
      {model.level === "asset" ? null : constitutionSection}
      {meaningSection}
      {contributionSection}
      {kindSection}
      {bindingsSection}
    </DetailDocument>
  );
}
