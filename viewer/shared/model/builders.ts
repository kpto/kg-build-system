import type { Representation, Grouping } from "@/shared/model/campaign";
import type { AuditSubject } from "@/lib/reviewTypes";
import type { StepId } from "@/lib/types";

export interface NavigatorInput {
  grouping: Grouping;
  collapsedGroups: ReadonlySet<string>;
  onToggleGroup: (key: string) => void;
}

export interface DiagnosisInput {
  representation: Representation;
  setRepresentation: (representation: Representation) => void;
  grouping: Grouping;
  setGrouping: (grouping: Grouping) => void;
  collapsedGroups: ReadonlySet<string>;
  onToggleGroup: (key: string) => void;
  onToggleAll: (collapse: boolean) => void;
  focusStepId?: StepId;
  lineageSourceFilter?: string;
  onClearSourceFilter: () => void;
}

export interface AuditInput {
  selectedFindingId?: string;
  subjectFilter?: AuditSubject;
  onClearSubjectFilter: () => void;
}
