"use client";

import { ModelDiagnosisView } from "@/diagnosis/view/ModelDiagnosisView";
import { NavigatorView } from "@/navigation/view/NavigatorView";
import { PropertiesView } from "@/properties/view/PropertiesView";
import type { DiagnoseTaskModel } from "@/review/model/buildAppModel";

interface DiagnoseModelViewProps {
  model: DiagnoseTaskModel;
}

/**
 * Diagnosis task: the execution, semantic or provenance model between one
 * Outliner and one Properties panel.
 *
 * The task receives three panel models and renders their views. Grouping,
 * collapse and the active representation are campaign presentation state and
 * arrive inside those models; fit/read and canvas viewport stay in the panel
 * views.
 */
export function DiagnoseModelView({ model }: DiagnoseModelViewProps) {
  return (
    <>
      <NavigatorView model={model.navigator} />
      <ModelDiagnosisView model={model.diagnosis} />
      <PropertiesView model={model.properties} />
    </>
  );
}
