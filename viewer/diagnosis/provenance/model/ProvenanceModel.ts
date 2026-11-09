import type { CampaignView } from "@/shared/model/campaign";
import type { DiagnosisInput } from "@/shared/model/builders";
import type { ActionModel, FieldModel } from "@/shared/model/hierarchy";
import type {
  AuditFinding,
  AuditReport,
  AuditSubject,
  DecisionView,
  Severity,
} from "@/lib/reviewTypes";
import type {
  AnnotationDTO,
  EntityKind,
  Expression,
  LineageBranch,
  LineageGraph,
  LineageLane,
  LineageNode,
  MetaGraphIndex,
  ViewerIndex,
} from "@/lib/types";
import { computeImpact } from "@/lib/impact";
import {
  lineageFromSelection,
  lineageNodeIdFromSelection,
} from "@/diagnosis/model/selection";

export type ProvenanceChainTone =
  | "source"
  | "asset"
  | "transform"
  | "accent"
  | "target";

export interface ProvenanceLaneModel {
  id: LineageLane;
  label: string;
  count: number;
  order: number;
}

export interface ProvenanceNodeModel {
  id: string;
  label: string;
  lane: LineageLane;
  kind: LineageNode["kind"];
  selected: boolean;
  dimmed: boolean;
  terminal: boolean;
  description?: string;
  artifact?: string;
  component?: string;
  property?: string;
  annotations: AnnotationDTO[];
  /** The raw node is only the command argument; the view does not read it. */
  node: LineageNode;
}

export interface ProvenanceEdgeModel {
  id: string;
  source: string;
  target: string;
  label?: string;
  branchKey: string;
  active: boolean;
  dimmed: boolean;
  laneTint?: LineageLane;
}

export interface ProvenanceGraphModel {
  id: "provenance-graph";
  question: string;
  lanes: ProvenanceLaneModel[];
  nodes: ProvenanceNodeModel[];
  edges: ProvenanceEdgeModel[];
  terminalNodeId: string;
  focusNodeId?: string;
  selectionLabel: string;
}

export interface ProvenanceEmptyExampleModel {
  id: string;
  label: string;
  kind: EntityKind;
  component: string;
  property: string;
  action?: ActionModel;
}

export interface ProvenanceEmptyModel {
  id: "lineage-empty";
  title: string;
  countLabel: string;
  heading: string;
  body: string;
  chain: Array<{ id: string; label: string; tone: ProvenanceChainTone }>;
  examples: ProvenanceEmptyExampleModel[];
  openBlueprint: ActionModel;
  footnote: string;
}

export interface ProvenanceReceiptFieldModel {
  id: string;
  label: string;
  value: string;
  title?: string;
  expression?: Expression;
  tone?: "source" | "target" | "text" | "faint";
}

export interface ProvenanceReceiptRowModel {
  id: string;
  index: number;
  branchKey: string;
  ordinal: string;
  propertyName: string;
  bindingIndex: number;
  bindingKind: EntityKind;
  selected: boolean;
  source: ProvenanceReceiptFieldModel;
  operator: ProvenanceReceiptFieldModel;
  binding: ProvenanceReceiptFieldModel;
  target: ProvenanceReceiptFieldModel;
  aggregates: string[];
  dedups: string[];
  operators: string[];
  identity: string;
  title: string;
  focus?: ActionModel;
}

export interface ProvenanceReceiptModel {
  id: "proof-receipt";
  title: string;
  question: string;
  countLabel: string;
  schemaLabel: string;
  hint: string;
  rows: ProvenanceReceiptRowModel[];
  emptyHint: string;
}

export interface ProvenanceBranchModel {
  id: string;
  index: number;
  ordinal: string;
  key: string;
  bindingIndex: number;
  bindingKind: EntityKind;
  source: FieldModel;
  asset: FieldModel;
  binding: FieldModel;
  identity: FieldModel;
  fieldMap: FieldModel;
  expression?: Expression;
  targets: string[];
  targetFallback?: string;
}

export interface ProvenanceBranchComparisonModel {
  id: "branch-comparison";
  title: string;
  question: string;
  meta: string;
  countLabel: string;
  legend: Array<{ id: string; label: string; tone: ProvenanceChainTone }>;
  branches: ProvenanceBranchModel[];
}

export interface ProvenanceImpactFieldModel {
  id: string;
  label: string;
  value: string;
  title?: string;
  tone: "source" | "target" | "neutral";
}

export interface ProvenanceImpactModel {
  id: "lineage-impact";
  title: string;
  question: string;
  subjectLabel: string;
  countLabel: string;
  fields: ProvenanceImpactFieldModel[];
  targets: string[];
}

export interface ProvenanceDecisionModel {
  id: string;
  index: number;
  title: string;
  status: string;
  source: string;
  rationale: string;
  rationaleSupplied: boolean;
  fields: FieldModel[];
}

export interface ProvenanceDecisionsModel {
  id: "lineage-decisions";
  title: string;
  question: string;
  countLabel: string;
  rows: ProvenanceDecisionModel[];
  emptyHint: string;
}

export interface ProvenanceQuestionModel {
  id: string;
  index: number;
  question: string;
  rule: string;
  evidenceCount: number;
  severity: Severity;
  subjectKind: string;
  subject?: AuditSubject;
  action?: ActionModel;
}

export interface ProvenanceQuestionsModel {
  id: "lineage-questions";
  title: string;
  question: string;
  meta: string;
  countLabel: string;
  rows: ProvenanceQuestionModel[];
}

export interface ProvenanceSourceFilterModel {
  id: "lineage-source-filter";
  label: string;
  active: string;
  activeBranches: number;
  totalBranches: number;
  countLabel: string;
  title: string;
  clear: ActionModel;
  visible: boolean;
}

export interface ProvenanceCommands {
  selectNode: (node: LineageNode) => void;
  openReview: (subject: AuditSubject) => void;
  openBlueprint: () => void;
  openLineageExample: (
    kind: EntityKind,
    component: string,
    property: string,
  ) => void;
  clearSourceFilter: () => void;
}

export interface ProvenanceModel {
  id: "provenance";
  question: string;
  metaGraph: MetaGraphIndex;
  graph: ProvenanceGraphModel | null;
  empty: ProvenanceEmptyModel;
  receipt: ProvenanceReceiptModel | null;
  branchComparison: ProvenanceBranchComparisonModel | null;
  impact: ProvenanceImpactModel | null;
  decisions: ProvenanceDecisionsModel | null;
  questions: ProvenanceQuestionsModel | null;
  sourceFilter: ProvenanceSourceFilterModel;
  commands: ProvenanceCommands;
}

/**
 * The campaign-free input of the provenance builder.
 *
 * The old shell still supplies its own subject-filter callbacks; the campaign
 * builder maps the campaign commands onto this surface.
 */
export interface ProvenanceSource {
  metaGraph: MetaGraphIndex;
  lineage: LineageGraph | null;
  index?: ViewerIndex;
  audit?: AuditReport;
  decisions?: DecisionView[];
  selectedNodeId?: string;
  sourceFilter?: string;
  onSelectNode?: (node: LineageNode) => void;
  onOpenReview?: (subject: AuditSubject) => void;
  onSelectProperty?: (
    kind: EntityKind,
    component: string,
    property: string,
  ) => void;
  onOpenBlueprint?: () => void;
  onClearSourceFilter?: () => void;
}

const LANE_ORDER: LineageLane[] = [
  "asset",
  "source",
  "transformation",
  "binding",
  "post",
  "target",
];

const LANE_LABELS: Record<LineageLane, string> = {
  asset: "Asset",
  source: "Source / Table",
  transformation: "Transformation / Projection",
  binding: "Binding",
  post: "Post-processing",
  target: "Target",
};

const BRANCH_LEGEND: ProvenanceBranchComparisonModel["legend"] = [
  { id: "source", label: "source", tone: "source" },
  { id: "asset", label: "asset", tone: "asset" },
  { id: "binding", label: "binding", tone: "accent" },
  { id: "identity", label: "identity", tone: "transform" },
  { id: "target", label: "target", tone: "target" },
];

function literalText(value: unknown): string {
  try {
    return JSON.stringify(value) ?? String(value);
  } catch {
    return String(value);
  }
}

function fieldText(expression: Extract<Expression, { kind: "field" }>): string {
  const base = expression.field[2] ?? expression.field.at(-1) ?? "";
  const path = expression.path?.length ? `.${expression.path.join(".")}` : "";
  return `${base}${path}`;
}

/** Render an expression with its field keys, operator names and literals. */
export function renderExpressionText(
  expression: Expression | undefined,
  depth = 0,
): string {
  if (!expression) return "—";
  if (expression.kind === "field") return fieldText(expression);
  if (expression.kind === "literal") return literalText(expression.value);
  const name = expression.operator.at(-1) ?? "operation";
  if (depth > 6) return `${name}(…)`;
  const argumentsText = (expression.arguments ?? [])
    .map((argument) => renderExpressionText(argument, depth + 1))
    .join(", ");
  return `${name}(${argumentsText})`;
}

function identityText(branch: LineageBranch): string {
  const binding = branch.binding.binding;
  const identity = renderExpressionText(binding.identity);
  const source = renderExpressionText(binding.source_identity);
  const target = renderExpressionText(binding.target_identity);
  if (binding.kind === "edge" && (source !== "—" || target !== "—")) {
    return `${source} → ${target}`;
  }
  return identity;
}

function comparisonIdentityText(branch: LineageBranch): string {
  const binding = branch.binding.binding;
  if (binding.kind === "edge") {
    return `${renderExpressionText(binding.source_identity)} → ${renderExpressionText(
      binding.target_identity,
    )}`;
  }
  return renderExpressionText(binding.identity);
}

function stageSteps(
  branch: LineageBranch,
  operators: readonly string[],
): string[] {
  return branch.postSteps
    .filter((step) => operators.includes(step.instruction.kind[0]))
    .map((step) => step.id.join("/"));
}

function branchNode(
  branch: LineageBranch,
  nodesById: Map<string, LineageNode>,
): LineageNode | undefined {
  const binding = branch.nodeIds.find(
    (id) => id.startsWith("semantic:binding:") && nodesById.has(id),
  );
  if (binding) return nodesById.get(binding);
  for (const id of branch.nodeIds) {
    const node = nodesById.get(id);
    if (node) return node;
  }
  return undefined;
}

function branchMatchesSource(branch: LineageBranch, source: string): boolean {
  if (
    branch.sourceRelations.includes(source) ||
    branch.relationNames.includes(source) ||
    branch.assetNames.includes(source)
  ) {
    return true;
  }
  for (const step of [...branch.sourceSteps, ...branch.upstreamSteps]) {
    if ((step.outputs ?? []).some((output) => output.type.includes(source))) {
      return true;
    }
  }
  return false;
}

function nodeIsDimmed(
  lineage: LineageGraph,
  nodeId: string,
  source: string | undefined,
): boolean {
  if (!source) return false;
  const owningBranches = lineage.branches.filter((branch) =>
    branch.nodeIds.includes(nodeId),
  );
  if (!owningBranches.length) return false;
  return !owningBranches.some((branch) => branchMatchesSource(branch, source));
}

function matchesDecision(
  decision: DecisionView,
  lineage: LineageGraph,
  subject: AuditSubject,
): boolean {
  const candidate = decision.subject;
  if (!candidate) return false;
  const component = candidate.component ?? candidate.name;
  if (
    candidate.kind === "property" &&
    component === subject.component &&
    candidate.property === subject.property
  ) {
    return true;
  }
  if (
    (candidate.kind === "node" || candidate.kind === "edge") &&
    component === subject.component
  ) {
    return true;
  }
  if (candidate.kind === "binding" && component === subject.component) {
    return true;
  }
  if (
    candidate.kind === "asset" &&
    lineage.branches.some((branch) => branch.assetNames.includes(component))
  ) {
    return true;
  }
  return false;
}

function relatedQuestionFindings(
  audit: AuditReport | undefined,
  lineage: LineageGraph,
  subject: AuditSubject,
): AuditFinding[] {
  if (!audit) return [];
  const component = subject.component ?? subject.name;
  const assets = new Set(
    lineage.branches.flatMap((branch) => branch.assetNames),
  );
  return audit.questions.filter((finding) => {
    if (!finding.question) return false;
    const candidate = finding.subject;
    if (!candidate) return false;
    const candidateComponent = candidate.component ?? candidate.name;
    if (
      candidate.kind === "property" &&
      candidateComponent === component &&
      candidate.property === subject.property
    ) {
      return true;
    }
    if (
      (candidate.kind === "node" || candidate.kind === "edge") &&
      candidateComponent === component
    ) {
      return true;
    }
    if (candidate.kind === "binding" && candidateComponent === component) {
      return true;
    }
    if (candidate.kind === "asset" && assets.has(candidateComponent)) {
      return true;
    }
    return false;
  });
}

function subjectForLineage(lineage: LineageGraph): AuditSubject {
  return {
    kind: "property",
    name: lineage.selection.component,
    component: lineage.selection.component,
    property: lineage.selection.property,
    entityKind: lineage.selection.kind,
  };
}

function commandsFromSource(source: ProvenanceSource): ProvenanceCommands {
  return {
    selectNode: source.onSelectNode ?? (() => {}),
    openReview: source.onOpenReview ?? (() => {}),
    openBlueprint: source.onOpenBlueprint ?? (() => {}),
    openLineageExample: source.onSelectProperty ?? (() => {}),
    clearSourceFilter: source.onClearSourceFilter ?? (() => {}),
  };
}

function emptyModel(
  source: ProvenanceSource,
  commands: ProvenanceCommands,
): ProvenanceEmptyModel {
  const examples: ProvenanceEmptyExampleModel[] = [
    {
      id: "lineage-example-defect-condition-rating",
      label: "defect.condition_rating",
      kind: "node",
      component: "defect",
      property: "condition_rating",
      action: source.onSelectProperty
        ? {
            id: "lineage-example-defect-condition-rating",
            label: "defect.condition_rating",
            icon: "lineage",
            run: () =>
              source.onSelectProperty?.("node", "defect", "condition_rating"),
          }
        : undefined,
    },
    {
      id: "lineage-example-reading-value",
      label: "reading.value",
      kind: "node",
      component: "reading",
      property: "value",
      action: source.onSelectProperty
        ? {
            id: "lineage-example-reading-value",
            label: "reading.value",
            icon: "lineage",
            run: () => source.onSelectProperty?.("node", "reading", "value"),
          }
        : undefined,
    },
  ];

  return {
    id: "lineage-empty",
    title: "Provenance",
    countLabel: "no selection",
    heading: "Select a property to trace its lineage",
    body:
      "Open the Blueprint canvas and click a property row, or choose a property in the Outliner. The lineage follows the binding expression through source relations, projections, aggregate and deduplication steps to every publication target, then states the design question and decision behind it.",
    chain: [
      { id: "source", label: "source", tone: "source" },
      { id: "transform", label: "transform", tone: "transform" },
      { id: "binding", label: "binding", tone: "accent" },
      { id: "target", label: "target", tone: "target" },
    ],
    examples,
    openBlueprint: {
      id: "lineage-empty-open-blueprint",
      label: "Open Blueprint",
      icon: "blueprint",
      run: () => commands.openBlueprint(),
    },
    footnote: "compile-only snapshot",
  };
}

function graphModel(
  lineage: LineageGraph,
  selectedNodeId: string | undefined,
  activeFilter: string | undefined,
): ProvenanceGraphModel {
  const matchingBranchKeys = new Set(
    activeFilter
      ? lineage.branches
          .filter((branch) => branchMatchesSource(branch, activeFilter))
          .map((branch) => branch.key)
      : [],
  );

  const laneCounts = new Map<LineageLane, number>();
  for (const node of lineage.nodes) {
    laneCounts.set(node.lane, (laneCounts.get(node.lane) ?? 0) + 1);
  }
  const lanes: ProvenanceLaneModel[] = lineage.lanes.map((lane) => ({
    id: lane.id,
    label: lane.label || LANE_LABELS[lane.id],
    count: laneCounts.get(lane.id) ?? 0,
    order: Math.max(0, LANE_ORDER.indexOf(lane.id)),
  }));

  const nodes: ProvenanceNodeModel[] = lineage.nodes.map((node) => ({
    id: node.id,
    label: node.label,
    lane: node.lane,
    kind: node.kind,
    selected: node.id === selectedNodeId,
    dimmed: nodeIsDimmed(lineage, node.id, activeFilter),
    terminal: node.id === lineage.terminalNodeId,
    description: node.metadata.description,
    artifact: node.metadata.artifacts[0]?.join("."),
    component: node.component,
    property: node.property,
    annotations: node.metadata.annotations,
    node,
  }));

  const nodesById = new Map(lineage.nodes.map((node) => [node.id, node]));
  const edges: ProvenanceEdgeModel[] = lineage.edges.map((edge) => {
    const dimmed =
      Boolean(activeFilter) && !matchingBranchKeys.has(edge.branchKey);
    const active = Boolean(
      selectedNodeId &&
        lineage.branches.some(
          (branch) =>
            branch.key === edge.branchKey &&
            branch.nodeIds.includes(selectedNodeId),
        ),
    );
    const sourceLane = nodesById.get(edge.source)?.lane;
    const targetLane = nodesById.get(edge.target)?.lane;
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      branchKey: edge.branchKey,
      active,
      dimmed,
      laneTint:
        sourceLane && sourceLane === targetLane ? sourceLane : undefined,
    };
  });

  const focusNodeId =
    (selectedNodeId &&
    lineage.nodes.some((node) => node.id === selectedNodeId)
      ? selectedNodeId
      : undefined) ??
    lineage.nodes.find((node) => node.kind === "binding")?.id ??
    lineage.terminalNodeId;

  return {
    id: "provenance-graph",
    question: "where does this value come from?",
    lanes,
    nodes,
    edges,
    terminalNodeId: lineage.terminalNodeId,
    focusNodeId,
    selectionLabel: `${lineage.selection.component}.${lineage.selection.property}`,
  };
}

function receiptModel(
  lineage: LineageGraph,
  selectedNodeId: string | undefined,
  commands: ProvenanceCommands,
): ProvenanceReceiptModel {
  const nodesById = new Map(lineage.nodes.map((node) => [node.id, node]));
  const rows: ProvenanceReceiptRowModel[] = lineage.branches.map(
    (branch, index) => {
      const target = branchNode(branch, nodesById);
      const operators = (() => {
        const names: string[] = [];
        const visit = (expression: Expression | undefined) => {
          if (!expression) return;
          if (expression.kind === "operation") {
            names.push(expression.operator.at(-1) ?? "operation");
            for (const argument of expression.arguments ?? []) visit(argument);
          }
        };
        visit(branch.expression);
        return names;
      })();
      const aggregates = stageSteps(branch, ["aggregate"]);
      const dedups = stageSteps(branch, [
        "deduplication",
        "merging",
        "conflict_validation",
      ]);
      const targets = branch.targetSteps.map((step) => step.id.join("/"));
      const fields = branch.fieldKeys.length
        ? branch.fieldKeys.join(" + ")
        : branch.sourceRelations.join(", ") || "literal";
      const selected = selectedNodeId
        ? branch.nodeIds.includes(selectedNodeId)
        : false;
      const operatorText = renderExpressionText(branch.expression);

      return {
        id: branch.key,
        index,
        branchKey: branch.key,
        ordinal: String(index + 1).padStart(2, "0"),
        propertyName: branch.propertyName,
        bindingIndex: branch.binding.index,
        bindingKind: branch.binding.binding.kind,
        selected,
        source: {
          id: "source",
          label: "source",
          value: fields,
          title: fields,
          tone: "source",
        },
        operator: {
          id: "operator",
          label: "operator",
          value: branch.expression ? operatorText : "direct copy",
          title: operatorText,
          expression: branch.expression,
          tone: "text",
        },
        binding: {
          id: "binding",
          label: "binding",
          value: `#${branch.binding.index} · ${branch.binding.binding.kind}`,
          title: `${branch.binding.binding.kind} binding #${branch.binding.index}`,
          tone: "text",
        },
        target: {
          id: "target",
          label: "target",
          value: targets.join(", ") || "no publication target",
          title: targets.join(", ") || "no publication target",
          tone: targets.length ? "target" : "faint",
        },
        aggregates,
        dedups,
        operators,
        identity: identityText(branch),
        title: target
          ? `Focus ${target.label} on the canvas`
          : "This branch has no selectable lineage node",
        focus:
          target && commands.selectNode
            ? {
                id: "focus-node",
                label: "Focus",
                icon: "focus",
                run: () => commands.selectNode(target),
              }
            : undefined,
      };
    },
  );

  return {
    id: "proof-receipt",
    title: "Proof receipt",
    question: "how is this value produced?",
    countLabel: `${lineage.branches.length} branch${
      lineage.branches.length === 1 ? "" : "es"
    }`,
    schemaLabel: "source → operator → binding → target",
    hint: "click a row to focus",
    rows,
    emptyHint: "No binding branch for this property.",
  };
}

function branchComparisonModel(
  lineage: LineageGraph,
): ProvenanceBranchComparisonModel | null {
  if (lineage.branches.length < 2) return null;

  return {
    id: "branch-comparison",
    title: "Compare branches",
    question: "how do the branches differ?",
    meta: `${lineage.selection.component}.${lineage.selection.property} · same property, different route`,
    countLabel: `${lineage.branches.length} branches`,
    legend: BRANCH_LEGEND,
    branches: lineage.branches.map((branch, index) => {
      const source =
        branch.sourceRelations.join(", ") ||
        branch.relationNames.join(", ") ||
        "not traced";
      const asset = branch.assetNames.join(", ") || "—";
      const targets = branch.targetSteps.map((step) => step.id.join("/"));
      const targetFallback = branch.targetSteps.length
        ? undefined
        : branch.downstreamSteps.length
          ? branch.downstreamSteps
              .slice(-1)
              .map((step) => step.id.join("/"))
              .join(", ")
          : "no publication target";
      return {
        id: branch.key,
        index,
        ordinal: String(index + 1).padStart(2, "0"),
        key: branch.key,
        bindingIndex: branch.binding.index,
        bindingKind: branch.binding.binding.kind,
        source: { id: "source", label: "source", value: source },
        asset: { id: "asset", label: "asset", value: asset },
        binding: {
          id: "binding",
          label: "binding",
          value: `#${branch.binding.index} · ${branch.binding.binding.kind}`,
        },
        identity: {
          id: "identity",
          label: "identity",
          value: comparisonIdentityText(branch),
        },
        fieldMap: {
          id: "field-map",
          label: "field map",
          value: branch.fieldKeys.join(", ") || "literal",
          title: branch.fieldKeys.join(", ") || "literal",
        },
        expression: branch.expression,
        targets,
        targetFallback,
      };
    }),
  };
}

function impactModel(
  index: ViewerIndex,
  subject: AuditSubject,
): ProvenanceImpactModel {
  const impact = computeImpact(index, subject);
  const records =
    typeof impact.records === "number" ? String(impact.records) : "not recorded";
  const subjectLabel = `${subject.kind} · ${subject.component ?? subject.name}`;

  return {
    id: "lineage-impact",
    title: "Impact radius",
    question: "what changes if this branch changes?",
    subjectLabel,
    countLabel: `${impact.upstream.length + impact.downstream.length} steps`,
    targets: impact.targets,
    fields: [
      {
        id: "upstream",
        label: "upstream",
        value: `${impact.upstream.length} steps feed this field`,
        tone: "source",
      },
      {
        id: "downstream",
        label: "downstream",
        value: `${impact.downstream.length} steps consume it`,
        tone: "target",
      },
      {
        id: "targets",
        label: "targets",
        value: impact.targets.length ? impact.targets.join(", ") : "not recorded",
        tone: "neutral",
      },
      { id: "records", label: "records", value: records, tone: "neutral" },
      {
        id: "nodes",
        label: "nodes",
        value: impact.nodes.length ? impact.nodes.join(", ") : "not recorded",
        tone: "neutral",
      },
      {
        id: "edges",
        label: "edges",
        value: impact.edges.length ? impact.edges.join(", ") : "not recorded",
        tone: "neutral",
      },
    ],
  };
}

function decisionsModel(
  decisions: DecisionView[],
  lineage: LineageGraph,
  subject: AuditSubject,
): ProvenanceDecisionsModel {
  const matching = decisions.filter((decision) =>
    matchesDecision(decision, lineage, subject),
  );
  return {
    id: "lineage-decisions",
    title: "Decision rationale",
    question: "why does this route exist?",
    countLabel: String(matching.length),
    rows: matching.map((decision, index) => ({
      id: decision.id,
      index,
      title: decision.title,
      status: decision.status,
      source: decision.source,
      rationale: decision.rationale,
      rationaleSupplied: decision.rationaleSupplied,
      fields: [
        {
          id: "rationale",
          label: "rationale",
          value: decision.rationaleSupplied ? "supplied" : "not captured",
          tone: decision.rationaleSupplied ? "info" : "accent",
        },
        { id: "source", label: "source", value: decision.source },
        {
          id: "reason",
          label: "reason",
          value:
            decision.rationale ||
            "The snapshot does not record a reason for this decision.",
        },
      ],
    })),
    emptyHint:
      "No decision subject matches this property or its owning entity.",
  };
}

function questionsModel(
  audit: AuditReport | undefined,
  lineage: LineageGraph,
  subject: AuditSubject,
  commands: ProvenanceCommands,
  hasOpenReview: boolean,
): ProvenanceQuestionsModel | null {
  if (!audit) return null;
  const findings = relatedQuestionFindings(audit, lineage, subject);
  if (!findings.length) return null;
  return {
    id: "lineage-questions",
    title: "Design questions",
    question: "what is unresolved about this subject?",
    meta: "needs a human decision",
    countLabel: String(findings.length),
    rows: findings.map((finding, index) => ({
      id: finding.id,
      index,
      question: finding.question ?? "",
      rule: finding.rule,
      evidenceCount: finding.evidence.length,
      severity: finding.severity,
      subjectKind: finding.subject?.kind ?? "unattributed",
      subject: finding.subject,
      action: hasOpenReview
        ? {
            id: "open-review",
            label: "Open review",
            icon: "review",
            run: () => commands.openReview(finding.subject ?? subject),
          }
        : undefined,
    })),
  };
}

function sourceFilterModel(
  lineage: LineageGraph | null,
  filter: string | undefined,
  commands: ProvenanceCommands,
  hasClear: boolean,
): ProvenanceSourceFilterModel {
  const totalBranches = lineage?.branches.length ?? 0;
  const activeBranches =
    lineage && filter
      ? lineage.branches.filter((branch) =>
          branchMatchesSource(branch, filter),
        ).length
      : 0;
  return {
    id: "lineage-source-filter",
    label: "source filter",
    active: filter ?? "",
    activeBranches,
    totalBranches,
    countLabel: `${activeBranches} / ${totalBranches} branches`,
    title: "Clear the source filter; every branch stays on the canvas",
    visible: Boolean(lineage && filter),
    clear: {
      id: "clear-source-filter",
      label: "clear",
      icon: "reset",
      title: "Clear the source filter; every branch stays on the canvas",
      run: hasClear ? () => commands.clearSourceFilter() : () => {},
    },
  };
}

/**
 * Build the provenance representation from the campaign.
 *
 * The model owns the lineage lanes, nodes, edges, the proof receipt, the branch
 * comparison, the impact radius, the decision rationale, the design questions
 * and the source filter. The view owns the canvas viewport, hover and which
 * filter chip is dismissed.
 */
export function buildProvenanceModel(
  campaign: CampaignView,
  input: DiagnosisInput,
): ProvenanceModel {
  return buildProvenanceModelFromSource({
    index: campaign.record.index,
    metaGraph: campaign.record.index.metaGraph,
    audit: campaign.record.audit ?? undefined,
    decisions: campaign.record.decisions,
    lineage: lineageFromSelection(campaign.selection),
    selectedNodeId: lineageNodeIdFromSelection(campaign.selection),
    sourceFilter: input.lineageSourceFilter,
    onSelectNode: (node) => campaign.commands.selectLineageNode(node),
    onOpenReview: (subject) => campaign.commands.openReview(subject),
    onSelectProperty: (kind, component, property) =>
      campaign.commands.selectProperty(kind, component, property),
    onOpenBlueprint: () => campaign.commands.setRepresentation("blueprint"),
    onClearSourceFilter: input.onClearSourceFilter,
  });
}

export function buildProvenanceModelFromSource(
  source: ProvenanceSource,
): ProvenanceModel {
  const commands = commandsFromSource(source);
  const empty = emptyModel(source, commands);
  const lineage = source.lineage;
  const activeFilter = source.sourceFilter;

  if (!lineage) {
    return {
      id: "provenance",
      question: "where does this value come from?",
      metaGraph: source.metaGraph,
      graph: null,
      empty,
      receipt: null,
      branchComparison: null,
      impact: null,
      decisions: null,
      questions: null,
      sourceFilter: sourceFilterModel(
        null,
        activeFilter,
        commands,
        Boolean(source.onClearSourceFilter),
      ),
      commands,
    };
  }

  const subject = subjectForLineage(lineage);
  const graph = graphModel(lineage, source.selectedNodeId, activeFilter);
  const receipt = receiptModel(lineage, source.selectedNodeId, commands);

  return {
    id: "provenance",
    question: "where does this value come from?",
    metaGraph: source.metaGraph,
    graph,
    empty,
    receipt,
    branchComparison: branchComparisonModel(lineage),
    impact: source.index ? impactModel(source.index, subject) : null,
    decisions: decisionsModel(
      source.decisions ?? [],
      lineage,
      subject,
    ),
    questions: questionsModel(
      source.audit,
      lineage,
      subject,
      commands,
      Boolean(source.onOpenReview),
    ),
    sourceFilter: sourceFilterModel(
      lineage,
      activeFilter,
      commands,
      Boolean(source.onClearSourceFilter),
    ),
    commands,
  };
}
