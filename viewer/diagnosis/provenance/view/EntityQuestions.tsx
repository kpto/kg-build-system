"use client";

import { ArrowRight, MessageCircleQuestion } from "lucide-react";
import { severityColor } from "@/shared/ui/theme";
import type { ProvenanceQuestionsModel } from "@/diagnosis/provenance/model/ProvenanceModel";

export interface EntityQuestionsProps {
  model: ProvenanceQuestionsModel;
}

/**
 * Design questions raised by the selected property and its owning entity.
 *
 * This is a row group inside the Lineage inspector section: the question is the
 * row subject, its rule and evidence count are row metadata, and the whole row
 * is the single action that opens the finding in Review.
 */
export function EntityQuestions({ model }: EntityQuestionsProps) {
  return (
    <div
      data-testid="lineage-questions"
      data-level="section"
      role="region"
      aria-label={model.question}
      className="min-w-0 border-b border-line-soft last:border-b-0"
    >
      <div className="ui-section-header border-b border-line-soft bg-panel">
        <MessageCircleQuestion
          className="size-3.5 shrink-0 text-accent"
          aria-hidden
        />
        <h3 className="ui-section-title shrink-0 text-accent">{model.title}</h3>
        <span className="ui-row-meta hidden min-w-0 truncate sm:inline">
          {model.meta}
        </span>
        <span className="ui-section-count ml-auto shrink-0">
          {model.countLabel}
        </span>
      </div>

      <div>
        {model.rows.map((row) => (
          <button
            key={row.id}
            type="button"
            data-testid={`lineage-question-${row.index}`}
            data-level="row"
            onClick={() => row.action?.run()}
            disabled={!row.action}
            className="ui-row group items-start text-left"
          >
            <span
              className="mt-1.5 size-1.5 shrink-0 rounded-full"
              style={{ backgroundColor: severityColor[row.severity] }}
              aria-hidden
            />
            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="text-[10px] leading-relaxed text-text">
                {row.question}
              </span>
              <span className="ui-row-meta">
                rule <span className="text-muted">{row.rule}</span>
                <span className="mx-1 text-line">·</span>
                <span className="tnum">{row.evidenceCount}</span> evidence
                <span className="mx-1 text-line">·</span>
                {row.subjectKind}
              </span>
            </span>
            <span
              className="ui-chip shrink-0 border-line-soft bg-panel-soft/40 font-mono text-[8px] uppercase tracking-[0.08em]"
              style={{ color: severityColor[row.severity] }}
            >
              {row.severity}
            </span>
            <ArrowRight
              className="size-3 shrink-0 text-faint transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-accent"
              aria-hidden
            />
          </button>
        ))}
      </div>
    </div>
  );
}
