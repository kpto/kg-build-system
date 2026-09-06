"use client";

/**
 * The stub every unbuilt feature area renders.
 *
 * It shows the values the area will be handed, so a placeholder is still a smoke
 * test of the wiring: if `problems` and `document` reach this component, they will
 * reach the real feature too.
 */

import { Card, Chip, EmptyState, Panel, ProblemBadge } from "@/components/ui";
import { refLabel } from "@/lib/ids";
import type { Problem, ProjectDocument } from "@/lib/types";

export interface FeatureStubProps {
  area: string;
  title: string;
  document: ProjectDocument;
  problems: Problem[];
  /** The planned interaction, so the contract stays next to the placeholder. */
  notes: readonly string[];
}

export function FeatureStub({ area, title, document, problems, notes }: FeatureStubProps) {
  return (
    <Panel
      id={`panel-${area}`}
      role="region"
      title={title}
      subtitle={`area: ${area}`}
      actions={
        <>
          <Chip tone="template" title="Placeholder for this area: it renders on the shell contract">stub</Chip>
          <ProblemBadge problems={problems} />
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <EmptyState
          title="Coming soon"
          body={
            <span>
              This area is a placeholder mounted on the shell contract. It already receives{" "}
              <code className="font-mono text-info">FeatureProps</code> and is ready for its
              implementation.
            </span>
          }
        />

        <Card header={<SectionLabel>how this area will use them</SectionLabel>}>
          <ul className="flex flex-col gap-1">
            {notes.map((note) => (
              <li key={note} className="flex gap-2 text-[12px] leading-snug text-muted">
                <span aria-hidden className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-faint" />
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card header={<SectionLabel>live props · {problems.length} relevant problems</SectionLabel>}>
          {problems.length === 0 ? (
            <p className="text-[12px] text-faint">No problems resolved into this area.</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {problems.slice(0, 6).map((problem) => (
                <li key={problem.id} className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate text-[12px] text-ink">{problem.message}</span>
                  <span className="shrink-0 font-mono text-[10px] text-faint">
                    {problem.ref ? refLabel(problem.ref) : "no ref"}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="pt-1 font-mono text-[11px] text-faint">
            rev {document.revision} · {document.components?.length ?? 0} components ·{" "}
            {document.tables?.length ?? 0} tables · {document.bindings?.length ?? 0} bindings
          </p>
        </Card>
      </div>
    </Panel>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">{children}</h3>
  );
}
