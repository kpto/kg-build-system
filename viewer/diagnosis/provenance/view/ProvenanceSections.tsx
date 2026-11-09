"use client";

import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { cx } from "@/shared/ui/theme";
import type {
  ProvenanceDecisionsModel,
  ProvenanceImpactModel,
} from "@/diagnosis/provenance/model/ProvenanceModel";

function ValueRow({
  label,
  tone,
  children,
}: {
  label: string;
  tone?: string;
  children: ReactNode;
}) {
  return (
    <div data-level="field" className="ui-field min-w-0">
      <dt className={cx("ui-field-label", tone)}>{label}</dt>
      <dd className="ui-field-value min-w-0">{children}</dd>
    </div>
  );
}

export function ImpactPanel({ model }: { model: ProvenanceImpactModel }) {
  return (
    <div
      data-testid={model.id}
      data-level="section"
      role="region"
      aria-label={model.question}
      className="ui-section min-w-0"
    >
      <div className="ui-section-header">
        <h3 className="ui-section-title shrink-0">{model.title}</h3>
        <span className="ui-row-meta hidden min-w-0 truncate sm:inline">
          {model.subjectLabel}
        </span>
        <span className="ui-section-count ml-auto shrink-0">
          {model.countLabel}
        </span>
      </div>

      <dl>
        {model.fields.map((field) => (
          <ValueRow
            key={field.id}
            label={field.label}
            tone={
              field.tone === "source"
                ? "text-source"
                : field.tone === "target"
                  ? "text-target"
                  : undefined
            }
          >
            {field.id === "targets" && model.targets.length ? (
              <span className="flex flex-wrap gap-1">
                {model.targets.map((target) => (
                  <span
                    key={target}
                    className="ui-chip whitespace-normal break-all font-mono text-[9px] text-target"
                  >
                    {target}
                  </span>
                ))}
              </span>
            ) : field.id === "upstream" || field.id === "downstream" ? (
              <span className={field.tone === "source" ? "text-source" : "text-target"}>
                {field.value.split(" ")[0]}
              </span>
            ) : null}
            {field.id === "upstream" || field.id === "downstream" ? (
              <span>
                {field.value.slice(field.value.indexOf(" ") + 1)}
              </span>
            ) : field.id === "targets" && model.targets.length ? null : (
              <span
                className={field.value === "not recorded" ? "text-faint" : undefined}
              >
                {field.value}
              </span>
            )}
          </ValueRow>
        ))}
      </dl>
    </div>
  );
}

export function DecisionsPanel({ model }: { model: ProvenanceDecisionsModel }) {
  return (
    <div
      data-testid={model.id}
      data-level="section"
      role="region"
      aria-label={model.question}
      className="ui-section min-w-0"
    >
      <div className="ui-section-header">
        <h3 className="ui-section-title shrink-0">{model.title}</h3>
        <span className="ui-row-meta hidden min-w-0 truncate sm:inline">
          why this route exists
        </span>
        <span className="ui-section-count ml-auto shrink-0">
          {model.countLabel}
        </span>
      </div>

      {model.rows.length ? (
        <div>
          {model.rows.map((row) => (
            <div
              key={row.id}
              data-testid={`lineage-decision-${row.index}`}
              data-level="row"
              className={cx(
                "ui-row items-start py-1",
                !row.rationaleSupplied && "border-l-2 border-l-accent/70",
              )}
            >
              <span className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="flex min-w-0 items-center gap-2">
                  <span className="min-w-0 truncate text-[10px] leading-relaxed text-text">
                    {row.title}
                  </span>
                  <span className="ui-chip ml-auto shrink-0 border-line-soft bg-panel-soft/40 font-mono text-[8px] uppercase tracking-[0.06em] text-faint">
                    {row.status}
                  </span>
                </span>
                <span className="flex flex-col">
                  {row.fields.map((field) => (
                    <span
                      key={field.id}
                      data-level="field"
                      className="ui-field min-w-0 px-0 py-0"
                    >
                      <span className="ui-field-label">{field.label}</span>
                      <span
                        className={cx(
                          "ui-field-value flex items-center gap-1",
                          field.id === "rationale" && row.rationaleSupplied
                            ? "text-source"
                            : field.id === "rationale"
                              ? "text-accent"
                              : "truncate",
                        )}
                      >
                        {field.id === "rationale" ? (
                          row.rationaleSupplied ? (
                            <CheckCircle2
                              className="size-2.5 shrink-0"
                              aria-hidden
                            />
                          ) : (
                            <AlertTriangle
                              className="size-2.5 shrink-0"
                              aria-hidden
                            />
                          )
                        ) : null}
                        <span className="truncate">{field.value}</span>
                      </span>
                    </span>
                  ))}
                </span>
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="ui-hint px-2 py-2">{model.emptyHint}</p>
      )}
    </div>
  );
}
