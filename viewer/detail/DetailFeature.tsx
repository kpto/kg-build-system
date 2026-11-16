"use client";

/**
 * Detail document view: one design subject read in full.
 *
 * Every kind renders the same band order: Overview, Meaning, Fulfilment,
 * Sources, Build steps, Expression, Members, Connections and Bindings. A kind
 * includes or omits a band; it never invents a second section grammar. The
 * content contract is `DETAIL_CONTENT.md`.
 */

import {
  useEffect,
  useMemo,
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
import {
  provenanceReferences,
  type ProvenanceReferences,
} from "@/proof/references";
import { ConceptGlyph, ConceptMark } from "@/shared/ui/ConceptMark";
import { ConceptReferenceChip } from "@/shared/ui/ConceptReference";
import { selectionForConceptTarget } from "@/workbench/conceptTarget";
import { activeDocument, documentSelection } from "@/workbench/types";
import type {
  LineageLane,
  SemanticSubjectKind,
  ViewerIndex,
} from "@/lib/types";
import { LINEAGE_LANES } from "@/lib/types";
import { collectFieldRefs, logicalTypeName } from "@/lib/expressions";
import {
  DetailBand,
  DetailDocument,
  DetailEmptyState,
  FactGrid,
  MemberTable,
  type DetailFact,
  type MemberRow,
} from "./view/DetailChrome";
import { FulfilmentMap, type AxisOpenTarget } from "./view/FulfilmentMap";
import {
  ExpressionTree,
  type ExpressionChain,
} from "./view/ExpressionTree";
import { WorkflowProvenanceGraph } from "./view/WorkflowProvenanceGraph";
import { DataItemEditor } from "./DataItemFeature";
import { ContextMenu } from "@/shared/ui/ContextMenu";
import { laneColor } from "@/shared/ui/theme";
import {
  branchLaneNodes,
  buildProof,
  collectProofSemantics,
  defaultProofSubject,
  traceArtifactLabel,
  type ProofBranch,
  type ProofLevel,
  type ProofModel,
  type ProofNode,
  type ProofPropertySummary,
  type ProofSemantics,
  type ProofSubject,
  type ProofTrace,
  type ProofTypeChain,
} from "@/proof/model";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import {
  attachedMeaning,
  componentMeaning,
  propertyMeaning,
  type DesignMeaningValue,
} from "@/shared/design/meaning";
import styles from "./detail.module.css";

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
      return { ...base, kind: "edge" };
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
      return `Node · ${model.subject.component}`;
    case "edge":
      return `Edge · ${model.subject.component}`;
    case "abstract":
      return `Abstract · ${model.abstract?.name ?? model.subject.component}`;
    case "asset":
      return `Asset · ${model.asset?.name ?? model.subject.component}`;
  }
}

function levelSubtitle(model: ProofModel): string {
  switch (model.level) {
    case "property": {
      const branchCount = model.branches.length;
      const type = model.typeChain?.steps.at(0)?.typeName ?? "unknown";
      return `${branchCount} ${branchCount === 1 ? "branch" : "branches"} · ${type}`;
    }
    case "node":
    case "edge":
      return `${model.properties.length} ${model.properties.length === 1 ? "property" : "properties"} · ${model.component?.labels.join(", ") || "no labels"}`;
    case "abstract":
      return `${model.abstract?.descendants.length ?? 0} concrete descendants`;
    case "asset": {
      const relations = model.asset?.relations.length ?? 0;
      const projections = model.asset?.projections.length ?? 0;
      return `${relations} tables · ${projections} projections · ${model.asset?.fields.length ?? 0} fields`;
    }
  }
}

function ProvenanceGroup({
  concept,
  label,
  references,
  onOpen,
  testId,
}: {
  concept: ConceptKind;
  label: string;
  references: ConceptReference[];
  onOpen(reference: ConceptReference): void;
  testId: string;
}) {
  return (
    <div className={styles.sourcesGroup} data-testid={testId}>
      <p className={styles.sourcesLabel}>
        <span>
          <ConceptGlyph concept={concept} className={styles.provenanceGroupIcon} />{" "}
          {label}
        </span>
        <span>{references.length}</span>
      </p>
      {references.length ? (
        <div className={styles.provenanceItems}>
          {references.map((reference) => (
            <ConceptReferenceChip
              key={`${reference.concept}:${reference.name}`}
              reference={reference}
              showIcon={false}
              onOpen={
                reference.target ? () => onOpen(reference) : undefined
              }
            />
          ))}
        </div>
      ) : (
        <p className={styles.provenanceEmpty}>None resolved</p>
      )}
    </div>
  );
}

function ProvenanceSection({
  provenance,
  onOpen,
}: {
  provenance: ProvenanceReferences;
  onOpen(reference: ConceptReference): void;
}) {
  const count = (value: number, singular: string) =>
    `${value} ${value === 1 ? singular : `${singular}s`}`;
  return (
    <DetailBand
      concept="graph"
      title="Sources"
      question="Where does this value come from?"
      meta={`${count(provenance.assets.length, "asset")} · ${count(
        provenance.tables.length,
        "source relation",
      )} · ${count(provenance.projections.length, "derived relation")}`}
      testId="detail-provenance"
    >
      <div className={styles.sourcesGrid}>
        <ProvenanceGroup
          concept="asset"
          label="Assets"
          references={provenance.assets}
          onOpen={onOpen}
          testId="detail-provenance-assets"
        />
        <ProvenanceGroup
          concept="table"
          label="Source relations"
          references={provenance.tables}
          onOpen={onOpen}
          testId="detail-provenance-tables"
        />
        <ProvenanceGroup
          concept="projection"
          label="Derived relations"
          references={provenance.projections}
          onOpen={onOpen}
          testId="detail-provenance-projections"
        />
      </div>
    </DetailBand>
  );
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

function attachmentLabel(kind: SemanticSubjectKind): string {
  switch (kind) {
    case "graph":
      return "graph declaration";
    case "binding":
      return "binding";
    case "field":
      return "source field";
    default:
      return kind;
  }
}

function SemanticCards({ attachments }: { attachments: ProofSemantics[] }) {
  if (!attachments.length) {
    return <DetailEmptyState>No attached meaning on this subject.</DetailEmptyState>;
  }
  return (
    <div className={styles.meaningGrid}>
      {attachments.map((attachment) => (
        <article key={attachment.key} className={styles.meaningCard}>
          <header className={styles.meaningCardHead}>
            <strong>
              {attachment.ownerName
                ? `${attachment.ownerName}.${attachment.name}`
                : attachment.name}
            </strong>
            <span>{attachmentLabel(attachment.kind)}</span>
          </header>
          <DesignMeaning
            claims={attachment.claims}
            limitations={attachment.limitations}
            purpose={attachment.purpose?.text}
            frames={attachment.frames}
            compact
            emptyText="No meaning is attached."
          />
        </article>
      ))}
    </div>
  );
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

function TypeChainSummary({ chain }: { chain?: ProofTypeChain }) {
  if (!chain) return <Badge tone="muted">no type chain</Badge>;
  return (
    <>
      <span className={styles.summaryType}>
        {chain.steps.at(0)?.typeName ?? "unknown"}
      </span>
      {chain.mismatch ? <Badge tone="warn">type mismatch</Badge> : null}
      {chain.narrowed ? <Badge tone="warn">presence narrowing</Badge> : null}
    </>
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
  onToggle,
  children,
}: {
  id: string;
  title: string;
  count: number;
  open: boolean;
  onToggle(id: string): void;
  children: ReactNode;
}) {
  return (
    <section className={styles.sideSection}>
      <button
        type="button"
        className={styles.sideSectionHead}
        aria-expanded={open}
        onClick={() => onToggle(id)}
        data-testid={`explorer-group-${id}`}
      >
        {open ? (
          <ChevronDown aria-hidden className={styles.sideChevron} />
        ) : (
          <ChevronRight aria-hidden className={styles.sideChevron} />
        )}
        <span>{title}</span>
        <span className={styles.sideCount}>{count}</span>
      </button>
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
  onSelect,
  onOpenPermanent,
  onContextMenu,
}: SidebarRowProps) {
  return (
    <button
      type="button"
      className={styles.sideRow}
      data-active={active ? "true" : undefined}
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
  const sectionOpen = (id: string) => Boolean(normalized) || open.has(id);
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
    matches(normalized, relation.name, relation.description),
  );
  const projections = index.projections.filter((projection) =>
    matches(normalized, projection.name, projection.description),
  );
  const nodes = index.topologyNodes.filter((node) =>
    matches(normalized, node.name) ||
    (node.properties ?? []).some((property) => matches(normalized, property.name)),
  );
  const edges = index.topologyEdges.filter((edge) =>
    matches(normalized, edge.name) ||
    (edge.properties ?? []).some((property) => matches(normalized, property.name)),
  );
  const concreteNodes = nodes.filter((node) => !node.abstract);
  const abstractNodes = nodes.filter((node) => node.abstract);

  const isActive = (
    level: ProofLevel,
    component: string,
    property?: string,
  ): boolean =>
    active?.level === level &&
    active.component === component &&
    (property === undefined || active.property === property);

  const renderNode = (node: (typeof nodes)[number]) => {
    const nodeOpen = normalized ? true : expanded.has(`node:${node.name}`);
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
            data-concept={node.abstract ? "abstract" : "node"}
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
              concept={node.abstract ? "abstract" : "node"}
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
    const edgeOpen = normalized ? true : expanded.has(`edge:${edge.name}`);
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
            onClick={() =>
              select({
                level: "edge",
                kind: "edge",
                component: edge.name,
              })
            }
            onDoubleClick={() =>
              openPermanent({
                level: "edge",
                kind: "edge",
                component: edge.name,
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
                    }),
                },
              ])
            }
            title={edge.name}
          >
            <ConceptGlyph concept="edge" className={styles.sideRowIcon} />
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
          title="Tables"
          count={tables.length}
          open={sectionOpen("tables")}
          onToggle={toggle}
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
          title="Projections"
          count={projections.length}
          open={sectionOpen("projections")}
          onToggle={toggle}
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
        >
          {concreteNodes.map(renderNode)}
        </SideSection>

        <SideSection
          id="abstract"
          title="Abstract"
          count={abstractNodes.length}
          open={sectionOpen("abstract")}
          onToggle={toggle}
        >
          {abstractNodes.map(renderNode)}
        </SideSection>

        <SideSection
          id="edges"
          title="Edges"
          count={edges.length}
          open={sectionOpen("edges")}
          onToggle={toggle}
        >
          {edges.map(renderEdge)}
        </SideSection>

        <SideSection
          id="workflow"
          title="Workflow"
          count={filteredWorkflowRows.length}
          open={workflowSectionOpen}
          onToggle={toggle}
        >
          {workflowGroups.length ? (
            workflowGroups.map((group) => {
              const groupKey = `wf:${group.component}`;
              const groupOpen = normalized ? true : expanded.has(groupKey);
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
                      onClick={() => toggleNode(groupKey)}
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
            title={`${node.semantics.length} attached semantics`}
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
  onOpen,
}: {
  bindings: ViewerIndex["bindings"];
  onOpen(target: AxisOpenTarget): void;
}) {
  const rows: MemberRow[] = bindings.map((binding) => {
    const fields = collectFieldRefs(binding.binding.identity)
      .map((ref) => ref[ref.length - 1])
      .filter(Boolean);
    const relations = relationNamesFromRowSource(binding.binding.rows);
    return {
      key: String(binding.index),
      onActivate: () =>
        onOpen({ kind: binding.kind, name: binding.component }),
      title: `Open ${binding.kind} ${binding.component}`,
      cells: [
        <span className={styles.memberName}>
          <ConceptGlyph concept={binding.kind} className={styles.memberGlyph} />
          {binding.binding.name ?? `binding #${binding.index}`}
        </span>,
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
      meta={`${bindings.length}`}
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
  onOpen,
}: {
  index: ViewerIndex;
  kind: "node" | "edge";
  component: string;
  onOpen(target: AxisOpenTarget): void;
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
        meta="2 endpoints"
      >
        <div className={styles.connectionRow}>
          <span>source</span>
          {source ? (
            <button
              type="button"
              onClick={() => onOpen({ kind: "node", name: source })}
            >
              {source}
            </button>
          ) : (
            <span>not resolved</span>
          )}
          <ArrowRight aria-hidden className={styles.inlineArrow} />
          <span>target</span>
          {target ? (
            <button
              type="button"
              onClick={() => onOpen({ kind: "node", name: target })}
            >
              {target}
            </button>
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
      meta={`${incident.length}`}
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
                <span>{component}</span>
              ) : (
                <button
                  type="button"
                  onClick={() => onOpen({ kind: "node", name: other })}
                >
                  {other}
                </button>
              )}
              <ArrowRight aria-hidden className={styles.inlineArrow} />
              {outgoing ? (
                <button
                  type="button"
                  onClick={() => onOpen({ kind: "node", name: other })}
                >
                  {other}
                </button>
              ) : (
                <span>{component}</span>
              )}
              <span className={styles.connectionLabel}>
                {edge.name}
                {edge.labels?.length ? ` · ${edge.labels.join(" · ")}` : ""}
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
  const attachments = collectProofSemantics(model);

  if (!branch) {
    return (
      <DetailBand
        title="Branches"
        question="Which bindings resolve this property?"
        meta="0"
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
        meta={`${model.branches.length}`}
        flush
      >
        <div className={styles.workToolbar}>
          <BranchBar
            branches={model.branches}
            active={activeBranch}
            onChange={setActiveBranch}
          />
          <div className={styles.workMeta}>
            <span className={styles.summaryLabel}>Type</span>
            <TypeChainSummary chain={branch.typeChain} />
            <span className={styles.summaryDivider} />
            <span className={styles.summaryLabel}>Targets</span>
            <span className={styles.summaryValue}>
              {branch.trace.target.length}
            </span>
            <span className={styles.summaryLabel}>Post</span>
            <span className={styles.summaryValue}>
              {branch.trace.post.length}
            </span>
            <span className={styles.summaryDivider} />
            <span className={styles.summaryLabel}>Meanings</span>
            <span className={styles.summaryValue}>{attachments.length}</span>
          </div>
        </div>

        <TypeChainView chain={branch.typeChain} />

        <LaneCanvas branch={branch} />
      </DetailBand>

      <DetailBand
        concept="edge"
        title="Connections"
        question="Which links does this branch assert?"
        meta={`${branch.edges.length} edges`}
      >
        <ConnectionLedger branch={branch} />
      </DetailBand>
    </div>
  );
}

function ComponentProofView({
  index,
  model,
  actions,
  onOpenAxis,
}: {
  index: ViewerIndex;
  model: ProofModel;
  actions: WorkspaceProps["actions"];
  onOpenAxis(target: AxisOpenTarget): void;
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
    onActivate: () =>
      actions.openTab({
        selection: toWorkbenchSelection({
          level: "property",
          kind: property.kind,
          component: property.component,
          property: property.property,
          propertyRef: property.propertyRef,
        }),
        preview: true,
      }),
    title: `Open ${property.component}.${property.property}`,
    cells: [
      <span className={styles.memberName}>
        <ConceptGlyph concept="property" className={styles.memberGlyph} />
        {property.property}
      </span>,
      logicalTypeName(property.logicalType),
      `${property.branchCount}`,
      property.sources.join(", ") || "—",
      property.bindingIndexes.join(", ") || "—",
    ],
  }));
  return (
    <div className={styles.levelBody}>
      <DetailBand
        title="Members"
        question="Which properties does this record assert?"
        meta={`${component.properties.length}`}
        testId="detail-properties"
      >
        <MemberTable
          columns={["Property", "Type", "Branches", "Sources", "Bindings"]}
          template="minmax(0, 1fr) 64px 72px minmax(0, 1fr) 72px"
          rows={rows}
          empty="No properties are declared for this subject."
        />
      </DetailBand>
      <ConnectionsSection
        index={index}
        kind={component.kind}
        component={component.name}
        onOpen={onOpenAxis}
      />
    </div>
  );
}

function AbstractProofView({
  model,
  actions,
}: {
  model: ProofModel;
  actions: WorkspaceProps["actions"];
}) {
  const abstract = model.abstract;
  if (!abstract) {
    return <DetailEmptyState>No abstract subject is available.</DetailEmptyState>;
  }
  const rows: MemberRow[] = abstract.descendants.map((descendant) => ({
    key: descendant.name,
    onActivate: () =>
      actions.openTab({
        selection: {
          kind: "node",
          level: "node",
          component: descendant.name,
          name: descendant.name,
        },
        preview: true,
      }),
    title: `Open the ${descendant.name} document`,
    cells: [
      <span className={styles.memberName}>
        <ConceptGlyph concept="node" className={styles.memberGlyph} />
        {descendant.name}
      </span>,
      descendant.labels.join(", ") || "—",
      `${descendant.properties.length}`,
      descendant.description ?? "—",
    ],
  }));
  return (
    <div className={styles.levelBody}>
      <DetailBand
        title="Members"
        question="Which records belong to this category?"
        meta={`${abstract.descendants.length}`}
      >
        <MemberTable
          columns={["Record", "Labels", "Properties", "Description"]}
          template="minmax(140px, 0.9fr) minmax(110px, 0.8fr) 66px minmax(180px, 1.6fr)"
          rows={rows}
          empty="No concrete record descends from this category."
        />
      </DetailBand>
    </div>
  );
}

function AssetProofView({
  index,
  model,
  onOpenAxis,
}: {
  index: ViewerIndex;
  model: ProofModel;
  onOpenAxis(target: AxisOpenTarget): void;
}) {
  const asset = model.asset;
  if (!asset) {
    return <DetailEmptyState>This asset is not present in the blueprint.</DetailEmptyState>;
  }
  const relationRows: MemberRow[] = [
    ...asset.relations.map((row) => ({ ...row, kindLabel: "source" })),
    ...asset.projections.map((row) => ({ ...row, kindLabel: "derived" })),
  ].map((row) => ({
    key: `${row.kindLabel}:${row.name}`,
    onActivate: () =>
      onOpenAxis({
        kind: row.kindLabel === "source" ? "table" : "projection",
        name: row.name,
      }),
    title: `Open the ${row.name} document`,
    cells: [
      <span className={styles.memberName}>
        <ConceptGlyph
          concept={row.kindLabel === "source" ? "table" : "projection"}
          className={styles.memberGlyph}
        />
        {row.name}
      </span>,
      row.kindLabel === "source" ? "source relation" : "derived relation",
      `${row.columns} columns`,
      `${row.semantics.length} meanings`,
    ],
  }));
  const fieldRows: MemberRow[] = asset.fields.map((field) => ({
    key: field.key,
    cells: [field.key, logicalTypeName(field.field.logical_type), field.ownerKind],
  }));
  const assetRelations = new Set([
    ...index.relations
      .filter((relation) => relation.asset?.[2] === asset.name)
      .map((relation) => relation.name),
    ...index.projections
      .filter((relation) => relation.asset?.[2] === asset.name)
      .map((relation) => relation.name),
  ]);
  const bindings = index.bindings.filter((binding) =>
    relationNamesFromRowSource(binding.binding.rows).some((name) =>
      assetRelations.has(name),
    ),
  );
  return (
    <div className={styles.levelBody}>
      <DetailBand
        title="Members"
        question="Which relations and fields does this asset supply?"
        meta={`${relationRows.length} relations`}
      >
        <MemberTable
          columns={["Relation", "Kind", "Shape", "Meaning"]}
          template="minmax(160px, 1.2fr) 110px 90px minmax(90px, 0.8fr)"
          rows={relationRows}
          empty="No relation is declared for this asset."
        />
      </DetailBand>
      <DetailBand
        title="Fields"
        question="Which declared fields carry this asset's values?"
        meta={`${fieldRows.length}`}
      >
        <MemberTable
          columns={["Field", "Type", "Owner"]}
          template="minmax(200px, 1.8fr) minmax(120px, 1fr) 90px"
          rows={fieldRows}
          empty="No field resolves to this asset."
        />
      </DetailBand>
      <BindingsSection bindings={bindings} onOpen={onOpenAxis} />
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

function subjectExpressionChains(
  index: ViewerIndex,
  model: ProofModel,
): ExpressionChain[] {
  const component = model.subject.component;
  if (model.level === "property") {
    return model.branches.map((branch) => ({
      id: branch.key,
      target: {
        concept: "property" as const,
        label: `${component}.${model.subject.property ?? ""}`,
        detail: "property expression",
      },
      expression: branch.branch.expression,
    }));
  }
  if (model.level === "node" || model.level === "edge") {
    const level = model.level;
    return index.bindings
      .filter(
        (binding) =>
          binding.kind === level && binding.component === component,
      )
      .map((binding) => ({
        id: `binding:${binding.index}`,
        target: {
          concept: level,
          label: component,
          detail: "identity expression",
        },
        expression: binding.binding.identity,
      }));
  }
  return [];
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
    wrap: true,
  };
  switch (model.level) {
    case "property": {
      const chain = model.typeChain;
      facts.push(
        { label: "Kind", value: "property" },
        {
          label: "Owner",
          value: `${model.subject.component} · ${
            index.topologyNodesByName.has(model.subject.component)
              ? "node"
              : "edge"
          }`,
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
          wrap: true,
          absent: !chain,
        },
        { label: "Branches", value: `${model.branches.length}` },
        { label: "Bindings", value: `${model.branches.length}` },
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
        { label: "Kind", value: model.level },
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
          wrap: true,
          absent: !identity.length,
        },
        {
          label: "Properties",
          value: `${model.properties.length}`,
        },
      );
      if (model.level === "edge") {
        const edge = index.topologyEdgesByName.get(model.subject.component);
        facts.push({
          label: "Endpoints",
          value: `${edge?.source?.[2] ?? "?"} → ${edge?.target?.[2] ?? "?"}`,
          wrap: true,
          absent: !edge?.source || !edge?.target,
        });
      } else {
        const incident = index.topologyEdges.filter(
          (edge) =>
            edge.source?.[2] === model.subject.component ||
            edge.target?.[2] === model.subject.component,
        );
        facts.push({ label: "Connections", value: `${incident.length}` });
      }
      facts.push(licenseFact);
      break;
    }
    case "abstract": {
      facts.push(
        { label: "Kind", value: "abstract category" },
        {
          label: "Labels",
          value: model.abstract?.labels.length
            ? model.abstract.labels.join(" · ")
            : "no labels",
          absent: !model.abstract?.labels.length,
        },
        {
          label: "Descendants",
          value: `${model.abstract?.descendants.length ?? 0}`,
        },
        licenseFact,
      );
      break;
    }
    case "asset": {
      const asset = model.asset;
      const profile = asset?.profile;
      facts.push(
        { label: "Kind", value: "asset" },
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
          wrap: true,
          absent: !profile?.coverage,
        },
        {
          label: "Relations",
          value: `${asset?.relations.length ?? 0} source · ${
            asset?.projections.length ?? 0
          } derived`,
        },
        { label: "Fields", value: `${asset?.fields.length ?? 0}` },
        licenseFact,
      );
      break;
    }
  }
  return facts;
}

function axisSubjectFor(model: ProofModel) {
  switch (model.level) {
    case "property":
      return {
        kind: "property" as const,
        component: model.subject.component,
        property: model.subject.property,
      };
    case "node":
    case "edge":
      return { kind: model.level, component: model.subject.component };
    case "abstract":
      return { kind: "abstract" as const, component: model.subject.component };
    case "asset":
      return { kind: "asset" as const, component: model.subject.component };
  }
}

function SubjectDetailEditor(props: WorkspaceProps) {
  const index = props.state.index;
  const model = useProofModel(props);
  const selection = documentSelection(activeDocument(props.state));
  const meaning = subjectMeaning(index, model);
  const meaningLimitationCount =
    meaning.limitations.length +
    (meaning.frames ?? []).reduce(
      (total, frame) => total + (frame.limitations?.length ?? 0),
      0,
    );
  const provenance = useMemo(
    () => provenanceReferences(index, model),
    [model, index],
  );
  const expressionChains = useMemo(
    () => subjectExpressionChains(index, model),
    [model, index],
  );
  const license = subjectLicense(index, model);
  const facts = useMemo(
    () => overviewFacts(index, model, license),
    [index, model, license],
  );
  const dataBound =
    model.level === "property" ||
    model.level === "node" ||
    model.level === "edge";

  useEffect(() => {
    if (selection) return;
    props.actions.setSelection(
      toWorkbenchSelection(defaultProofSubject(props.state.index)),
    );
  }, [props.actions, props.state.index, selection]);

  const openReference = (reference: ConceptReference) => {
    if (!reference.target) return;
    const selection = selectionForConceptTarget(reference.target);
    if (!selection) return;
    props.actions.openTab({ selection, preview: true });
  };
  const openAxis = (target: AxisOpenTarget) => {
    const selectionFor = (): SubjectSelection => {
      switch (target.kind) {
        case "table":
          return { kind: "relation", name: target.name, component: target.name };
        case "projection":
          return {
            kind: "projection",
            name: target.name,
            component: target.name,
          };
        case "asset":
          return {
            kind: "asset",
            level: "asset",
            name: target.name,
            component: target.name,
          };
        case "node":
        case "edge": {
          const abstract = index.topologyNodesByName.get(target.name)?.abstract;
          return {
            kind: target.kind,
            level: target.kind === "node" && abstract ? "abstract" : target.kind,
            name: target.name,
            component: target.name,
          };
        }
      }
    };
    props.actions.openTab({ selection: selectionFor(), preview: true });
  };
  const endpoint = (name?: string): ConceptReference | undefined =>
    name
      ? {
          concept: "node",
          name,
          target: { concept: "node", name },
        }
      : undefined;
  const source = endpoint(model.component?.provenance?.source);
  const target = endpoint(model.component?.provenance?.target);
  const banner =
    model.level === "edge" && (source || target) ? (
      <div className={styles.bannerRelations} aria-label="Edge endpoints">
        <span className={styles.bannerLabel}>source</span>
        {source ? (
          <ConceptReferenceChip
            reference={source}
            onOpen={() => openReference(source)}
          />
        ) : (
          <span className={styles.bannerEmpty}>not resolved</span>
        )}
        <ArrowRight aria-hidden className={styles.bannerArrow} />
        {target ? (
          <ConceptReferenceChip
            reference={target}
            onOpen={() => openReference(target)}
          />
        ) : (
          <span className={styles.bannerEmpty}>not resolved</span>
        )}
        <span className={styles.bannerLabel}>target</span>
      </div>
    ) : undefined;

  const subjectSemantics = model.subjectSemantics.filter(
    (attachment) =>
      attachment.name !== model.subject.component &&
      attachment.ownerName !== model.subject.component,
  );
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

  return (
    <DetailDocument
      testId="detail-editor"
      concept={model.level}
      kicker={`Design · ${model.level}`}
      title={levelTitle(model)}
      subtitle={levelSubtitle(model)}
      license={{
        value: license.value,
        source: license.source,
        title:
          license.licenses.join(" · ") || "No asset declares a license.",
      }}
      banner={banner}
    >
      <DetailBand
        title="Overview"
        question="What is this, in one screen?"
        meta={model.subject.component}
      >
        {model.component?.description || model.abstract?.description ? (
          <p className={styles.bandNote}>
            {model.component?.description ?? model.abstract?.description}
          </p>
        ) : model.asset?.profile?.description ? (
          <p className={styles.bandNote}>{model.asset.profile.description}</p>
        ) : null}
        <FactGrid facts={facts} />
      </DetailBand>

      <DetailBand
        concept="semantics"
        title="Meaning"
        question="What is this for, and what does it exclude?"
        meta={`${meaning.claims.length} ${
          meaning.claims.length === 1 ? "claim" : "claims"
        } · ${meaningLimitationCount} ${
          meaningLimitationCount === 1 ? "limitation" : "limitations"
        }`}
        testId="detail-meaning"
      >
        <DesignMeaning
          claims={meaning.claims}
          limitations={meaning.limitations}
          purpose={meaning.purpose}
          frames={meaning.frames}
          emptyText="No meaning is attached to this subject."
        />
        {subjectSemantics.length ? (
          <div className={styles.meaningAttached}>
            <p className={styles.bandNote}>Attached meaning</p>
            <SemanticCards attachments={subjectSemantics} />
          </div>
        ) : null}
      </DetailBand>

      <DetailBand
        title="Fulfilment"
        question="How do the record and relation axes meet?"
        meta="two axes"
        testId="detail-fulfilment"
      >
        <FulfilmentMap
          index={index}
          subject={axisSubjectFor(model)}
          onOpen={openAxis}
        />
      </DetailBand>

      {model.level === "asset" ? (
        <DetailBand
          concept="asset"
          title="Sources"
          question="Where does this asset read from?"
          meta="release boundary"
        >
          <p className={styles.inlineEmpty}>
            {`${
              index.assetsByName.get(model.subject.component)?.layout?.kind ??
              "Unspecified"
            } layout at ${
              index.assetsByName.get(model.subject.component)?.layout?.locator ??
              "an unrecorded location"
            }. The asset is the release boundary; every relation in Members reads it.`}
          </p>
        </DetailBand>
      ) : null}

      {dataBound ? (
        <ProvenanceSection provenance={provenance} onOpen={openReference} />
      ) : null}

      {dataBound ? (
        <WorkflowProvenanceGraph
          index={index}
          model={model}
          onOpenStep={(row) =>
            props.actions.openTab({
              selection: {
                kind: "step",
                component: row.component,
                name: row.name,
                stepId: row.id,
              },
            })
          }
        />
      ) : null}

      {dataBound ? (
        <ExpressionTree
          index={index}
          references={provenance}
          chains={expressionChains}
          item={{
            concept: model.level,
            label:
              model.level === "property"
                ? `${model.subject.component}.${model.subject.property ?? ""}`
                : model.subject.component,
          }}
        />
      ) : null}

      {model.level === "property" ? (
        <PropertyProofView model={model} />
      ) : model.level === "asset" ? (
        <AssetProofView
          index={index}
          model={model}
          onOpenAxis={openAxis}
        />
      ) : model.level === "abstract" ? (
        <AbstractProofView model={model} actions={props.actions} />
      ) : (
        <ComponentProofView
          index={index}
          model={model}
          actions={props.actions}
          onOpenAxis={openAxis}
        />
      )}

      {bindings.length ? (
        <BindingsSection bindings={bindings} onOpen={openAxis} />
      ) : null}
    </DetailDocument>
  );
}
