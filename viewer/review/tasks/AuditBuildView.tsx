"use client";

import { BuildAuditView } from "@/audit/view/BuildAuditView";
import type { AuditTaskModel } from "@/review/model/buildAppModel";

interface AuditBuildViewProps {
  model: AuditTaskModel;
}

/**
 * Audit task: the build review model at full width. The audit panel owns its
 * section rail, so the task adds no Outliner or Properties panel.
 */
export function AuditBuildView({ model }: AuditBuildViewProps) {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
      <BuildAuditView model={model.audit} />
    </div>
  );
}
