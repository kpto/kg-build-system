import type { Representation } from "@/shared/model/campaign";
import type { IconToken } from "@/shared/model/hierarchy";
import type { ExecutionModel } from "@/diagnosis/execution/model/ExecutionModel";
import type { SemanticsModel } from "@/diagnosis/semantics/model/SemanticsModel";
import type { ProvenanceModel } from "@/diagnosis/provenance/model/ProvenanceModel";

export interface DiagnosisTabModel {
  id: Representation;
  label: string;
  hint: string;
  icon: IconToken;
  active: boolean;
  command: () => void;
}

export interface DiagnosisHeaderModel {
  title: string;
  meta: string;
  icon: IconToken;
  question: string;
}

export { buildDiagnosisModel } from "@/diagnosis/model/buildDiagnosisModel";

/** The active representation's own ViewModel. */
export type DiagnosisChildModel =
  | { id: "workflow"; model: ExecutionModel }
  | { id: "blueprint"; model: SemanticsModel }
  | { id: "lineage"; model: ProvenanceModel };

/**
 * The diagnosis panel ViewModel: one header, three representation tabs and the
 * active representation's model.
 *
 * It owns the representation switch. It does not own the graph projection, the
 * viewport or any React state.
 */
export interface DiagnosisModel {
  id: "diagnosis";
  representation: Representation;
  header: DiagnosisHeaderModel;
  tabs: DiagnosisTabModel[];
  child: DiagnosisChildModel;
  commands: {
    setRepresentation: (representation: Representation) => void;
  };
}
