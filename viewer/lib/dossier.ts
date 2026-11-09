/**
 * Review dossier export.
 *
 * The Markdown is the human hand-off artifact; the JSON is the machine-readable
 * equivalent. Both are built from already-loaded data and contain no server
 * call, no clock value and no generated rationale.
 */

import type {
  LineageGraph,
  PropertySelection,
  StepId,
  ViewerIndex,
} from "./types";
import type {
  AuditFinding,
  AuditReport,
  AuditSubject,
  DecisionView,
  Impact,
  ReviewRecord,
  SnapshotDiff,
} from "./reviewTypes";
import { expressionPreview } from "./expressions";
import { buildLineage } from "./lineage";
import { computeImpact } from "./impact";
import { summarizeQueue } from "./reviewQueue";

export interface DossierInput {
  index: ViewerIndex;
  audit: AuditReport;
  decisions: DecisionView[];
  queue: Record<string, ReviewRecord>;
  selection?: PropertySelection;
  lineage?: LineageGraph;
  diff?: SnapshotDiff;
}

function cell(value: unknown): string {
  return String(value ?? "")
    .replace(/\|/g, "\\|")
    .replace(/\r?\n/g, "<br>")
    .trim();
}

function subjectLabel(subject: AuditSubject | undefined): string {
  if (!subject) return "—";
  const name = subject.component ?? subject.name;
  if (subject.kind === "property") {
    return `${subject.entityKind ?? "node"} · ${name}.${subject.property ?? ""}`;
  }
  if (subject.kind === "step") {
    return subject.stepId
      ? `step · ${subject.stepId.join("/")}`
      : `step · ${subject.name}`;
  }
  return `${subject.kind} · ${name}`;
}

function evidenceLabel(finding: AuditFinding): string {
  return finding.evidence
    .map((entry) => `${entry.artifact} ${entry.jsonPointer}`)
    .join("<br>");
}

function statusFor(
  finding: AuditFinding,
  queue: Record<string, ReviewRecord>,
): { status: string; note: string } {
  const record = queue[finding.id];
  return {
    status: record?.status ?? "open",
    note: record?.note ?? "",
  };
}

function stepList(steps: StepId[]): string {
  return steps.length ? steps.map((step) => step.join("/")).join(", ") : "—";
}

function propertyImpact(
  index: ViewerIndex,
  selection: PropertySelection,
): Impact {
  return computeImpact(index, {
    kind: "property",
    name: selection.component,
    component: selection.component,
    property: selection.property,
    entityKind: selection.kind,
  });
}

function lineageSection(
  index: ViewerIndex,
  selection: PropertySelection,
  lineage: LineageGraph,
): string[] {
  const lines: string[] = ["## Selected property receipt", ""];
  lines.push(
    `Property: \`${selection.kind} ${selection.component}.${selection.property}\``,
    "",
    `Expression: \`${expressionPreview(
      lineage.branches.find((branch) => branch.expression)?.expression,
    )}\``,
    "",
    "### Lineage branches",
    "",
    "| Branch | Binding | Sources | Fields | Targets |",
    "| --- | --- | --- | --- | --- |",
  );
  if (!lineage.branches.length) {
    lines.push("| — | — | — | — | — |");
  } else {
    for (const branch of lineage.branches) {
      lines.push(
        `| ${cell(branch.key)} | ${cell(branch.binding.index)} | ${cell(
          branch.sourceRelations.join(", ") || "—",
        )} | ${cell(branch.fieldKeys.join(", ") || "—")} | ${cell(
          branch.targetSteps.map((step) => step.id.join("/")).join(", ") || "—",
        )} |`,
      );
    }
  }

  const impact = propertyImpact(index, selection);
  lines.push(
    "",
    "### Impact",
    "",
    `- Upstream: ${stepList(impact.upstream)}`,
    `- Downstream: ${stepList(impact.downstream)}`,
    `- Targets: ${impact.targets.join(", ") || "—"}`,
    `- Records: ${typeof impact.records === "number" ? impact.records : "not recorded"}`,
    "",
  );
  return lines;
}

export function buildDossierMarkdown(input: DossierInput): string {
  const { index, audit, decisions, queue, selection, diff } = input;
  const snapshot = index.snapshot;
  const report = snapshot.report;
  const summary = summarizeQueue(audit, queue);
  const reviewed = summary.total - summary.open;
  const lineage = selection
    ? input.lineage ?? buildLineage(index, selection)
    : undefined;

  const lines: string[] = [];
  lines.push(`# Review dossier — ${snapshot.title}`, "");
  lines.push(
    `Snapshot: \`${snapshot.name}\` (format ${snapshot.format}, version ${snapshot.version})`,
    "",
    "| Count | Value |",
    "| --- | --- |",
    `| Assets | ${index.stats.assets} |`,
    `| Relations | ${index.stats.tables} |`,
    `| Projections | ${index.stats.projections} |`,
    `| Structs | ${index.stats.structs} |`,
    `| Topology nodes | ${index.stats.topologyNodes} |`,
    `| Topology edges | ${index.stats.topologyEdges} |`,
    `| Topology properties | ${index.stats.topologyProperties} |`,
    `| Bindings | ${index.stats.bindings} |`,
    `| Steps | ${index.stats.steps} |`,
    `| Connections | ${index.stats.connections} |`,
    "",
  );

  lines.push("## Health score", "");
  lines.push(
    `Score: **${audit.score.value} / 100**. This is a weighted rubric, not a confidence value.`,
    "",
    "| Component | Value | Weight | Detail |",
    "| --- | --- | --- | --- |",
  );
  for (const component of audit.score.components) {
    lines.push(
      `| ${cell(component.label)} | ${cell(component.value)} | ${cell(
        component.weight,
      )} | ${cell(component.detail)} |`,
    );
  }
  lines.push("");

  lines.push("## Audit findings", "");
  lines.push(
    "Findings are deterministic observations with evidence, not proof of correctness.",
    "",
  );
  if (!audit.findings.length) {
    lines.push("_No findings._", "");
  } else {
    lines.push(
      "| Finding | Severity | Rule | Subject | Evidence | Status | Note |",
      "| --- | --- | --- | --- | --- | --- | --- |",
    );
    for (const finding of audit.findings) {
      const state = statusFor(finding, queue);
      lines.push(
        `| ${cell(finding.id)} | ${cell(finding.severity)} | ${cell(
          finding.rule,
        )} | ${cell(subjectLabel(finding.subject))} | ${cell(
          evidenceLabel(finding),
        )} | ${cell(state.status)} | ${cell(state.note || "—")} |`,
      );
    }
    lines.push("");
  }

  lines.push("## Design questions", "");
  if (!audit.questions.length) {
    lines.push("_No design questions._", "");
  } else {
    for (const finding of audit.questions) {
      lines.push(
        `- **${finding.title}** — ${finding.question} (${cell(
          subjectLabel(finding.subject),
        )}; finding \`${finding.id}\`)`,
      );
    }
    lines.push("");
  }

  lines.push("## Decision ledger", "");
  const ai = snapshot.review?.ai;
  if (ai && (ai.model || ai.runId || ai.generatedAt || ai.note)) {
    lines.push(
      `AI provenance: model=${cell(ai.model ?? "not recorded")}; runId=${cell(
        ai.runId ?? "not recorded",
      )}; generatedAt=${cell(ai.generatedAt ?? "not recorded")}.`,
      "",
    );
    if (ai.note) lines.push(`${ai.note}`, "");
  }
  if (!decisions.length) {
    lines.push("_No decisions._", "");
  } else {
    lines.push(
      "| ID | Title | Status | Source | Rationale | Rationale supplied |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const decision of decisions) {
      lines.push(
        `| ${cell(decision.id)} | ${cell(decision.title)} | ${cell(
          decision.status,
        )} | ${cell(decision.source)} | ${cell(decision.rationale || "—")} | ${
          decision.rationaleSupplied ? "yes" : "no"
        } |`,
      );
    }
    lines.push("");
  }

  if (snapshot.review?.notes?.length) {
    lines.push("### Reviewer notes", "");
    for (const note of snapshot.review.notes) {
      lines.push(
        `- ${note.text}${note.author ? ` — ${note.author}` : ""}${
          note.subject ? ` (${cell(subjectLabel(note.subject))})` : ""
        }`,
      );
    }
    lines.push("");
  }

  lines.push("## Build health", "");
  lines.push(
    `- Published artifacts: ${report?.published_artifacts?.length ?? 0}`,
    `- Recovered failures: ${report?.recovered_failures?.length ?? 0}`,
    `- Unresolved failures: ${report?.unresolved_failures?.length ?? 0}`,
    "",
    "| Component | Version | Runtime fields |",
    "| --- | --- | --- |",
  );
  for (const component of index.workflow.components ?? []) {
    const runtimeFields = (component.runtime_fields ?? []).map((field) =>
      typeof field === "string"
        ? field
        : String((field as Record<string, unknown>).key ?? "runtime field"),
    );
    lines.push(
      `| ${cell(component.id)} | ${cell(component.version ?? "—")} | ${cell(
        runtimeFields.join(", ") || "—",
      )} |`,
    );
  }
  lines.push("");

  if (diff) {
    lines.push("## Snapshot diff", "");
    lines.push(
      `- Steps: +${diff.summary.stepsAdded} / -${diff.summary.stepsRemoved} / changed ${diff.steps.changed.length}`,
      `- Connections: +${diff.summary.connectionsAdded} / -${diff.summary.connectionsRemoved}`,
      `- Nodes: +${diff.summary.nodesAdded} / -${diff.summary.nodesRemoved}`,
      `- Edges: +${diff.summary.edgesAdded} / -${diff.summary.edgesRemoved}`,
      `- Bindings: +${diff.summary.bindingsAdded} / -${diff.summary.bindingsRemoved}`,
      `- Changed properties: ${diff.summary.propertiesChanged}`,
      "",
    );
  }

  if (selection && lineage) {
    lines.push(...lineageSection(index, selection, lineage));
  } else {
    lines.push("## Selected property receipt", "", "_No property selected._", "");
  }

  lines.push("## Review queue", "");
  lines.push(
    `Progress: ${reviewed} / ${summary.total} findings reviewed (${summary.open} open, ${summary.acknowledged} acknowledged, ${summary.waived} waived, ${summary.resolved} resolved).`,
    "",
    "_Findings are deterministic observations with evidence, not proof of correctness._",
    "",
  );

  return lines.join("\n");
}

export function buildDossierJson(input: DossierInput): string {
  const { index, audit, decisions, queue, selection, diff } = input;
  const snapshot = index.snapshot;
  const report = snapshot.report;
  const lineage = selection
    ? input.lineage ?? buildLineage(index, selection)
    : undefined;
  const impact = selection ? propertyImpact(index, selection) : undefined;

  return JSON.stringify(
    {
      format: "kg-viewer-dossier",
      version: 1,
      snapshot: {
        name: snapshot.name,
        title: snapshot.title,
        format: snapshot.format,
        version: snapshot.version,
        stats: index.stats,
      },
      health: audit.score,
      counts: audit.counts,
      findings: audit.findings,
      questions: audit.questions,
      decisions,
      queue,
      build: {
        published_artifacts: report?.published_artifacts ?? [],
        recovered_failures: report?.recovered_failures ?? [],
        unresolved_failures: report?.unresolved_failures ?? [],
        provenance: report?.provenance ?? null,
        components: index.workflow.components ?? [],
      },
      review: snapshot.review ?? null,
      selection: selection ?? null,
      lineage: lineage ?? null,
      impact: impact ?? null,
      diff: diff ?? null,
    },
    null,
    2,
  );
}

export function downloadDossier(
  filename: string,
  text: string,
  mime = "text/markdown",
): void {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  const blob = new Blob([text], { type: mime });
  const url =
    typeof URL !== "undefined" && typeof URL.createObjectURL === "function"
      ? URL.createObjectURL(blob)
      : "";
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  if (url && typeof URL.revokeObjectURL === "function") {
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}
