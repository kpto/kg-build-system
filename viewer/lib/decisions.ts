/**
 * Decision ledger.
 *
 * Sidecar decisions come first, verbatim. Derived cards state only what the
 * snapshot itself records: asset semantics, component version/runtime fields,
 * build provenance, meta-graph provenance and annotations. A derived card marks
 * `rationaleSupplied` only when a description, claim, limitation or annotation
 * actually supplies the reason. No model name, prompt or generated rationale is
 * invented.
 */

import type { ViewerIndex } from "./types";
import type {
  AuditSubject,
  Decision,
  DecisionView,
  EvidenceRef,
  ReviewSidecar,
} from "./reviewTypes";
import { flattenAnnotations } from "./annotations";

export interface DecisionCoverage {
  total: number;
  rationaleSupplied: number;
  rationaleMissing: number;
  sidecar: number;
  derived: number;
}

function nonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function evidence(
  label: string,
  artifact: EvidenceRef["artifact"],
  jsonPointer: string,
): EvidenceRef {
  return { label, artifact, jsonPointer };
}

function sentence(parts: readonly string[]): string {
  const body = parts
    .map((part) => part.trim().replace(/\.+$/, ""))
    .filter(Boolean)
    .join(". ");
  return body ? `${body}.` : "";
}

function sidecarView(decision: Decision): DecisionView {
  return {
    ...decision,
    evidence: decision.evidence ?? [],
    source: "sidecar",
    rationaleSupplied: nonEmpty(decision.rationale),
  };
}

function assetDecision(
  index: ViewerIndex,
  assetIndex: number,
): DecisionView | undefined {
  const asset = index.blueprint.assets?.[assetIndex];
  if (!asset) return undefined;
  const semantics = asset.semantics;
  const parts: string[] = [];
  if (semantics) {
    if (nonEmpty(semantics.subject)) parts.push(`subject: ${semantics.subject}`);
    if (nonEmpty(semantics.coverage)) parts.push(`coverage: ${semantics.coverage}`);
    if (nonEmpty(semantics.authority)) parts.push(`authority: ${semantics.authority}`);
    if (nonEmpty(semantics.basis)) parts.push(`basis: ${semantics.basis}`);
    if (nonEmpty(semantics.title)) parts.push(`title: ${semantics.title}`);
    if (nonEmpty(semantics.description)) {
      parts.push(`description: ${semantics.description}`);
    }
    if (semantics.claims?.length) {
      parts.push(`claims: ${semantics.claims.join("; ")}`);
    }
    if (semantics.limitations?.length) {
      parts.push(`limitations: ${semantics.limitations.join("; ")}`);
    }
  }

  const annotationText = flattenAnnotations(asset.annotations)
    .map((annotation) => annotation.text)
    .join(", ");
  if (annotationText) parts.push(`annotations: ${annotationText}`);

  const rationale = parts.length
    ? sentence(parts)
    : "The asset declares no semantics beyond its name.";
  const subject: AuditSubject = {
    kind: "asset",
    name: asset.name,
    component: asset.name,
  };

  return {
    id: `derived:asset:${asset.name}`,
    title: nonEmpty(semantics?.subject)
      ? `Asset "${asset.name}" covers ${semantics?.subject}`
      : `Asset "${asset.name}" declares no source semantics`,
    status: "accepted",
    rationale,
    evidence: [
      evidence("asset declaration", "blueprint", `/assets/${assetIndex}`),
      evidence("asset semantics", "blueprint", `/assets/${assetIndex}/semantics`),
    ],
    subject,
    tags: ["asset", "semantics", "derived"],
    source: "derived",
    rationaleSupplied: parts.length > 0,
  };
}

function componentDecision(
  index: ViewerIndex,
  componentIndex: number,
): DecisionView | undefined {
  const component = index.workflow.components?.[componentIndex];
  if (!component) return undefined;
  const runtimeFields = component.runtime_fields ?? [];
  const parts: string[] = [];
  if (nonEmpty(component.version)) {
    parts.push(`The workflow declares version ${component.version}`);
  }

  const fieldLabels: string[] = [];
  let supplied = false;
  for (const field of runtimeFields) {
    if (typeof field === "string") {
      fieldLabels.push(field);
      parts.push(`runtime field ${field}`);
      continue;
    }
    const record = field as Record<string, unknown>;
    const key = nonEmpty(record.key) ? record.key : "runtime field";
    fieldLabels.push(key);
    const valueType = nonEmpty(record.value_type)
      ? record.value_type
      : "unknown type";
    const required = record.required === true ? "required" : "optional";
    const description = nonEmpty(record.description)
      ? `: ${record.description}`
      : "";
    if (nonEmpty(record.description)) supplied = true;
    parts.push(`runtime field ${key} (${valueType}, ${required})${description}`);
  }

  if (!parts.length) {
    parts.push(`The workflow declares component "${component.id}" with no version or runtime fields`);
  }

  const subject: AuditSubject = {
    kind: "step",
    name: component.id,
    component: component.id,
  };
  const title = runtimeFields.length
    ? `Component "${component.id}" declares ${runtimeFields.length} runtime field${runtimeFields.length === 1 ? "" : "s"}`
    : `Component "${component.id}"${nonEmpty(component.version) ? ` at version ${component.version}` : ""}`;

  return {
    id: `derived:component:${component.id}`,
    title,
    status: "accepted",
    rationale: sentence(parts),
    evidence: [
      evidence("workflow component", "workflow", `/components/${componentIndex}`),
      ...(runtimeFields.length
        ? [
            evidence(
              "runtime fields",
              "workflow",
              `/components/${componentIndex}/runtime_fields`,
            ),
          ]
        : []),
    ],
    subject,
    tags: ["component", "provenance", "derived", ...(runtimeFields.length ? ["runtime"] : [])],
    source: "derived",
    rationaleSupplied: supplied,
  };
}

function reportDecision(index: ViewerIndex): DecisionView {
  const report = index.snapshot.report;
  const published = report?.published_artifacts ?? [];
  const recovered = report?.recovered_failures ?? [];
  const unresolved = report?.unresolved_failures ?? [];
  const provenance = report?.provenance;
  const provenanceKeys = provenance ? Object.keys(provenance).sort() : [];
  const artifactTypes = [...new Set(published.map((artifact) => artifact.type.join(".")))].sort();

  const parts = [
    `The build report publishes ${published.length} artifact${published.length === 1 ? "" : "s"}${
      artifactTypes.length ? ` (${artifactTypes.join(", ")})` : ""
    }`,
    `the report records ${recovered.length} recovered and ${unresolved.length} unresolved failures`,
  ];
  if (provenanceKeys.length) {
    parts.push(`provenance keys: ${provenanceKeys.join(", ")}`);
  }

  const supplied = Boolean(
    provenance &&
      Object.values(provenance).some(
        (value) => typeof value === "string" && value.trim().length > 0,
      ),
  );

  return {
    id: "derived:report",
    title: `Build report publishes ${published.length} artifact${published.length === 1 ? "" : "s"}`,
    status: "accepted",
    rationale: sentence(parts),
    evidence: [
      evidence("published artifacts", "report", "/published_artifacts"),
      evidence("recovered failures", "report", "/recovered_failures"),
      evidence("unresolved failures", "report", "/unresolved_failures"),
    ],
    subject: {
      kind: "step",
      name: index.snapshot.name,
      component: "report",
    },
    tags: ["build-health", "report", "derived"],
    source: "derived",
    rationaleSupplied: supplied,
  };
}

function metaGraphDecision(index: ViewerIndex): DecisionView | undefined {
  const generatedBy = index.snapshot.metaGraph?.generated_by;
  if (!generatedBy || !Object.keys(generatedBy).length) return undefined;
  const moduleId = nonEmpty(generatedBy.module_id)
    ? generatedBy.module_id
    : "unknown module";
  const moduleVersion = nonEmpty(generatedBy.module_version)
    ? generatedBy.module_version
    : undefined;
  const details = Object.entries(generatedBy)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}: ${String(value)}`);
  const supplied = ["note", "description", "rationale"].some((key) =>
    nonEmpty(generatedBy[key]),
  );

  return {
    id: "derived:meta_graph:generated_by",
    title: `Meta graph generated by ${moduleId}${moduleVersion ? ` ${moduleVersion}` : ""}`,
    status: "accepted",
    rationale: `The meta graph records its generator: ${details.join("; ")}.`,
    evidence: [evidence("meta graph generator", "metaGraph", "/generated_by")],
    subject: {
      kind: "step",
      name: moduleId,
      component: "meta_graph",
    },
    tags: ["provenance", "metaGraph", "derived"],
    source: "derived",
    rationaleSupplied: supplied,
  };
}

function annotationDecisions(index: ViewerIndex): DecisionView[] {
  const decisions: DecisionView[] = [];
  (index.blueprint.graph?.nodes ?? []).forEach((node, nodeIndex) => {
    const annotations = flattenAnnotations(node.annotations);
    if (!annotations.length) return;
    decisions.push({
      id: `derived:annotation:node:${node.name}`,
      title: `Node "${node.name}" carries ${annotations.length} annotation${annotations.length === 1 ? "" : "s"}`,
      status: "accepted",
      rationale: `The snapshot records: ${annotations.map((annotation) => annotation.text).join(", ")}.`,
      evidence: [
        evidence("node annotations", "blueprint", `/graph/nodes/${nodeIndex}/annotations`),
      ],
      subject: {
        kind: "node",
        name: node.name,
        component: node.name,
        entityKind: "node",
      },
      tags: ["annotation", "derived"],
      source: "derived",
      rationaleSupplied: true,
    });
  });
  (index.blueprint.graph?.edges ?? []).forEach((edge, edgeIndex) => {
    const annotations = flattenAnnotations(edge.annotations);
    if (!annotations.length) return;
    decisions.push({
      id: `derived:annotation:edge:${edge.name}`,
      title: `Edge "${edge.name}" carries ${annotations.length} annotation${annotations.length === 1 ? "" : "s"}`,
      status: "accepted",
      rationale: `The snapshot records: ${annotations.map((annotation) => annotation.text).join(", ")}.`,
      evidence: [
        evidence("edge annotations", "blueprint", `/graph/edges/${edgeIndex}/annotations`),
      ],
      subject: {
        kind: "edge",
        name: edge.name,
        component: edge.name,
        entityKind: "edge",
      },
      tags: ["annotation", "derived"],
      source: "derived",
      rationaleSupplied: true,
    });
  });
  return decisions;
}

export function deriveDecisions(
  index: ViewerIndex,
  review?: ReviewSidecar,
): DecisionView[] {
  const sidecar = (review?.decisions ?? []).map(sidecarView);

  const derived: DecisionView[] = [];
  (index.blueprint.assets ?? []).forEach((_, assetIndex) => {
    const decision = assetDecision(index, assetIndex);
    if (decision) derived.push(decision);
  });
  (index.workflow.components ?? []).forEach((_, componentIndex) => {
    const decision = componentDecision(index, componentIndex);
    if (decision) derived.push(decision);
  });
  derived.push(reportDecision(index));
  const metaDecision = metaGraphDecision(index);
  if (metaDecision) derived.push(metaDecision);
  derived.push(...annotationDecisions(index));

  derived.sort((left, right) => left.id.localeCompare(right.id));

  return [...sidecar, ...derived];
}

export function decisionCoverage(
  decisions: readonly DecisionView[],
): DecisionCoverage {
  let rationaleSupplied = 0;
  let sidecar = 0;
  let derived = 0;
  for (const decision of decisions) {
    if (decision.rationaleSupplied) rationaleSupplied += 1;
    if (decision.source === "sidecar") sidecar += 1;
    else derived += 1;
  }
  return {
    total: decisions.length,
    rationaleSupplied,
    rationaleMissing: decisions.length - rationaleSupplied,
    sidecar,
    derived,
  };
}
