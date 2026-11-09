"use client";

import type { AuditFinding } from "@/lib/reviewTypes";
import type { StepId } from "@/lib/types";
import { severityColor, theme } from "@/shared/ui/theme";
import { highestSeverity } from "@/diagnosis/execution/model/stepAudit";

export interface ArtifactSocket {
  label: string;
  title: string;
}

export interface WorkflowStepDetailData {
  stepId: StepId;
  componentVersion?: string;
  runtimeFields: string[];
  instructionKind: string;
  producerCount: number;
  consumerCount: number;
  artifactTypes: string[];
  inputSockets: ArtifactSocket[];
  outputSockets: ArtifactSocket[];
  findings: AuditFinding[];
  onReview?: () => void;
  onTrace?: () => void;
}

/**
 * Hover/focus explanation for one workflow step.
 *
 * The popover is deliberately rendered inside the step node so it follows the
 * node transform and does not require a portal or canvas-coordinate maths. It
 * is one flat overlay: one header, fields and rules, no nested cards.
 */
export function StepDetailPopover({
  data,
}: {
  data: WorkflowStepDetailData;
}) {
  const severity = highestSeverity(data.findings);
  const id = data.stepId.join("/");

  return (
    <div
      data-testid="step-detail"
      role="dialog"
      aria-label={`Step detail for ${id}`}
      className="nodrag nowheel nopan absolute top-full left-0 z-50 mt-1.5 w-[320px] border border-line-strong bg-panel text-left"
      onClick={(event) => event.stopPropagation()}
      onMouseDown={(event) => event.stopPropagation()}
    >
      <div className="flex items-start justify-between gap-2 border-b border-line px-2.5 py-1.5">
        <div className="min-w-0">
          <p className="text-[9px] text-faint">step</p>
          <p className="mt-0.5 truncate font-mono text-[10px] text-accent">
            {id}
          </p>
        </div>
        {data.findings.length ? (
          <span
            className="ui-chip shrink-0 text-[9px]"
            title={`Highest severity: ${severity ?? "info"}`}
          >
            <span
              className="size-1.5 rounded-full"
              style={{
                backgroundColor: severity
                  ? severityColor[severity]
                  : theme.faint,
              }}
            />
            {data.findings.length}
          </span>
        ) : null}
      </div>

      <div className="py-1">
        <div className="grid grid-cols-[72px_minmax(0,1fr)] items-baseline gap-2 px-2.5 py-0.5" data-level="field">
          <span className="text-right text-[9px] text-faint">component</span>
          <span className="min-w-0 font-mono text-[9px] break-words text-text">
            {data.stepId[0]}
            {data.componentVersion ? ` v${data.componentVersion}` : ""}
          </span>
        </div>
        <div className="grid grid-cols-[72px_minmax(0,1fr)] items-baseline gap-2 px-2.5 py-0.5" data-level="field">
          <span className="text-right text-[9px] text-faint">instruction</span>
          <span className="min-w-0 font-mono text-[9px] break-words text-text">{data.instructionKind}</span>
        </div>
        <div className="grid grid-cols-[72px_minmax(0,1fr)] items-baseline gap-2 px-2.5 py-0.5" data-level="field">
          <span className="text-right text-[9px] text-faint">producers</span>
          <span className="min-w-0 font-mono text-[9px] tabular-nums text-text">{data.producerCount}</span>
        </div>
        <div className="grid grid-cols-[72px_minmax(0,1fr)] items-baseline gap-2 px-2.5 py-0.5" data-level="field">
          <span className="text-right text-[9px] text-faint">consumers</span>
          <span className="min-w-0 font-mono text-[9px] tabular-nums text-text">{data.consumerCount}</span>
        </div>
      </div>

      <div className="border-t border-line-soft px-2.5 py-1.5">
        <p className="text-[9px] text-faint">runtime fields</p>
        {data.runtimeFields.length ? (
          <ul className="mt-1 space-y-1">
            {data.runtimeFields.map((field, index) => (
              <li
                key={`${field}-${index}`}
                className="font-mono text-[9px] leading-relaxed text-muted"
              >
                {field}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-[9px] text-faint">none declared</p>
        )}
      </div>

      <div className="border-t border-line-soft px-2.5 py-1.5">
        <p className="text-[9px] text-faint">artifact types</p>
        {data.artifactTypes.length ? (
          <div className="mt-1 flex flex-wrap gap-1">
            {data.artifactTypes.map((type) => (
              <span key={type} className="ui-chip max-w-full truncate text-[9px]" title={type}>
                {type}
              </span>
            ))}
          </div>
        ) : (
          <p className="mt-1 text-[9px] text-faint">none</p>
        )}
      </div>

      <div className="border-t border-line-soft px-2.5 py-1.5">
        <p className="text-[9px] text-faint">audit findings</p>
        {data.findings.length ? (
          <div className="thin-scrollbar mt-1 max-h-32 space-y-1.5 overflow-auto pr-1">
            {data.findings.map((finding) => (
              <div key={finding.id} className="flex items-start gap-1.5">
                <span
                  className="mt-1 size-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: severityColor[finding.severity] }}
                />
                <p className="min-w-0 text-[9px] leading-relaxed text-muted">
                  <span className="text-faint">{finding.severity}</span>
                  {` · ${finding.title}`}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-1 text-[9px] text-faint">none</p>
        )}
      </div>

      <div className="flex items-center gap-1.5 border-t border-line px-2.5 py-1.5">
        <button
          type="button"
          data-testid="review-step"
          data-level="control"
          onClick={() => data.onReview?.()}
          className="ui-button ui-focus-ring flex-1"
        >
          Review finding
        </button>
        <button
          type="button"
          data-testid="trace-step"
          data-level="control"
          onClick={() => data.onTrace?.()}
          className="ui-button ui-button-primary ui-focus-ring flex-1"
        >
          Trace lineage
        </button>
      </div>
    </div>
  );
}
