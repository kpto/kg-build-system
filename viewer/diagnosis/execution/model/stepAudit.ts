import { stepKey } from "@/lib/indexes";
import type { AuditFinding, AuditReport, AuditSubject, Severity } from "@/lib/reviewTypes";
import type { StepId, ViewerIndex, WorkflowStep } from "@/lib/types";

/** Lower is more severe. */
export const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

export interface StepAuditSummary {
  count: number;
  severity?: Severity;
  findings: AuditFinding[];
}

export function highestSeverity(
  findings: readonly AuditFinding[],
): Severity | undefined {
  let highest: Severity | undefined;
  for (const finding of findings) {
    if (!highest || SEVERITY_ORDER[finding.severity] < SEVERITY_ORDER[highest]) {
      highest = finding.severity;
    }
  }
  return highest;
}

export function summarizeFindings(
  findings: readonly AuditFinding[],
): StepAuditSummary {
  return {
    count: findings.length,
    ...(findings.length ? { severity: highestSeverity(findings) } : {}),
    findings: [...findings],
  };
}

function addStep(target: Map<string, WorkflowStep>, step: WorkflowStep): void {
  target.set(stepKey(step.id), step);
}

function stepsForSubject(
  index: ViewerIndex,
  subject: AuditSubject,
): WorkflowStep[] {
  const steps = new Map<string, WorkflowStep>();

  if (subject.kind === "step") {
    const addById = (id: StepId) => {
      const step = index.stepsById.get(stepKey(id));
      if (step) addStep(steps, step);
    };

    if (subject.stepId) addById(subject.stepId);
    const slash = subject.name.indexOf("/");
    if (slash >= 0) {
      addById([
        subject.name.slice(0, slash),
        subject.name.slice(slash + 1),
      ]);
    }
    if (subject.component) addById([subject.component, subject.name]);
    return [...steps.values()];
  }

  if (subject.kind === "binding") {
    const binding =
      typeof subject.bindingIndex === "number"
        ? index.bindings.find(
            (candidate) => candidate.index === subject.bindingIndex,
          )
        : index.bindingByComponent.get(subject.component ?? subject.name)?.[0];
    if (binding?.step) addStep(steps, binding.step);
    return [...steps.values()];
  }

  if (
    subject.kind === "property" ||
    subject.kind === "node" ||
    subject.kind === "edge"
  ) {
    const component = subject.component ?? subject.name;
    for (const binding of index.bindingByComponent.get(component) ?? []) {
      if (binding.step) addStep(steps, binding.step);
    }
  }

  return [...steps.values()];
}

/**
 * Match every audit finding to the workflow steps it affects.
 *
 * The mapping follows the audit subject contract: a step subject names its
 * `component/name`; a binding subject names its binding step; property and
 * topology subjects fan out through all bindings for the component and then to
 * the steps that produce those bindings.
 */
export function buildStepAuditMap(
  index: ViewerIndex,
  audit?: AuditReport,
): Map<string, StepAuditSummary> {
  const byStep = new Map<string, AuditFinding[]>();

  for (const finding of audit?.findings ?? []) {
    if (!finding.subject) continue;
    for (const step of stepsForSubject(index, finding.subject)) {
      const key = stepKey(step.id);
      const findings = byStep.get(key) ?? [];
      if (!findings.some((candidate) => candidate.id === finding.id)) {
        findings.push(finding);
      }
      byStep.set(key, findings);
    }
  }

  const summaries = new Map<string, StepAuditSummary>();
  for (const [key, findings] of byStep) {
    summaries.set(key, summarizeFindings(findings));
  }
  return summaries;
}

/** Findings for a step set, counted once per finding. */
export function summarizeGroupAudit(
  stepAudit: ReadonlyMap<string, StepAuditSummary>,
  steps: readonly WorkflowStep[],
): StepAuditSummary {
  const findings = new Map<string, AuditFinding>();
  for (const step of steps) {
    for (const finding of stepAudit.get(stepKey(step.id))?.findings ?? []) {
      findings.set(finding.id, finding);
    }
  }
  return summarizeFindings([...findings.values()]);
}

/** Resolve the steps a review subject points at. */
export function subjectSteps(
  index: ViewerIndex,
  subject: AuditSubject | undefined,
): WorkflowStep[] {
  return subject ? stepsForSubject(index, subject) : [];
}
