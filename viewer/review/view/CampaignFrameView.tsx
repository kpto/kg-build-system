"use client";

import { Check } from "lucide-react";
import type { AppModel } from "@/review/model/buildAppModel";
import { AuditBuildView } from "@/review/tasks/AuditBuildView";
import { DiagnoseModelView } from "@/review/tasks/DiagnoseModelView";
import { OrientMapView } from "@/review/tasks/OrientMapView";
import { CampaignHeaderView } from "@/review/view/CampaignHeaderView";
import { CampaignStatusView } from "@/review/view/CampaignStatusView";
import { ShortcutSheetView } from "@/review/view/ShortcutSheetView";

interface CampaignFrameViewProps {
  model: AppModel;
  /** Transient controller notices: toast and the shortcut sheet. */
  toast?: string;
  shortcutsOpen: boolean;
  onCloseShortcuts: () => void;
  /** Campaign context rendered for assistive technology. */
  activeSubjectFilter?: string;
}

/**
 * The window frame: campaign header, active task, status bar and transient
 * overlays. It maps task models to task views; it never builds a model.
 */
export function CampaignFrameView({
  model,
  toast,
  shortcutsOpen,
  onCloseShortcuts,
  activeSubjectFilter,
}: CampaignFrameViewProps) {
  const { task } = model;
  const record = model.campaign.view.record;
  const auditReady = Boolean(record.audit && record.coverage);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-abyss text-ink">
      <CampaignHeaderView model={model.campaign.header} />

      <div
        data-level="workspace"
        className="flex min-h-0 flex-1 overflow-hidden"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          const file = event.dataTransfer.files?.[0];
          if (file) model.campaign.view.commands.importFile(file);
        }}
      >
        {task.kind === "map" ? <OrientMapView model={task} /> : null}
        {task.kind === "explore" ? <DiagnoseModelView model={task} /> : null}
        {task.kind === "review" && auditReady ? (
          <AuditBuildView model={task} />
        ) : null}
        {task.kind === "review" && !auditReady ? (
          <div className="flex min-w-0 flex-1 items-center justify-center text-xs text-muted">
            Building the audit report…
          </div>
        ) : null}
      </div>

      <CampaignStatusView model={model.campaign.status} />

      <ShortcutSheetView open={shortcutsOpen} onClose={onCloseShortcuts} />
      {toast ? (
        <div
          data-testid="toast"
          className="pointer-events-none fixed bottom-10 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-sm border border-accent/40 bg-panel-raised px-3 py-2 text-[11px] text-ink"
        >
          <Check className="size-3.5 text-accent" aria-hidden />
          {toast}
        </div>
      ) : null}
      {activeSubjectFilter ? (
        <span className="sr-only" data-testid="active-subject-filter">
          {activeSubjectFilter}
        </span>
      ) : null}
    </div>
  );
}
