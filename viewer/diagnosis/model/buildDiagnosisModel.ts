import type { DiagnosisInput } from "@/shared/model/builders";
import type {
  CampaignView,
  Representation,
} from "@/shared/model/campaign";
import type { IconToken } from "@/shared/model/hierarchy";
import { lineageFromSelection } from "@/diagnosis/model/selection";
import { buildExecutionModel } from "@/diagnosis/execution/model/buildExecutionModel";
import { buildSemanticsModel } from "@/diagnosis/semantics/model/SemanticsModel";
import { buildProvenanceModel } from "@/diagnosis/provenance/model/ProvenanceModel";
import type {
  DiagnosisChildModel,
  DiagnosisModel,
} from "@/diagnosis/model/DiagnosisModel";

const TABS: Array<{
  id: Representation;
  label: string;
  hint: string;
  icon: IconToken;
  title: string;
  question: string;
}> = [
  {
    id: "workflow",
    label: "Workflow",
    hint: "Step graph and connection flow (W)",
    icon: "workflow",
    title: "Execution",
    question: "what runs, in what order, and through which artifacts?",
  },
  {
    id: "blueprint",
    label: "Blueprint",
    hint: "Node, edge and relation blueprint (B)",
    icon: "blueprint",
    title: "Semantics",
    question: "what does the graph mean, and how is each property grounded?",
  },
  {
    id: "lineage",
    label: "Lineage",
    hint: "Property provenance and SQL preview (L)",
    icon: "lineage",
    title: "Provenance",
    question: "where does this value come from?",
  },
];

function count(value: number): string {
  return value.toLocaleString("en-US");
}

function metaFor(
  campaign: CampaignView,
  representation: Representation,
): string {
  const index = campaign.record.index;
  if (representation === "workflow") {
    return `${count(index.stats.steps)} steps · ${count(index.stats.connections)} connections`;
  }
  if (representation === "blueprint") {
    return `${count(index.stats.topologyNodes)} nodes · ${count(index.stats.topologyEdges)} edges`;
  }

  const lineage = lineageFromSelection(campaign.selection);
  const subjectCount = index.stats.topologyNodes + index.stats.topologyEdges;
  if (lineage && lineage.nodes.length > 0) {
    return `${count(subjectCount)} subjects · ${count(lineage.nodes.length)} nodes`;
  }
  return `${count(subjectCount)} subjects`;
}

function buildChild(
  campaign: CampaignView,
  input: DiagnosisInput,
  representation: Representation,
): DiagnosisChildModel {
  switch (representation) {
    case "workflow":
      return {
        id: "workflow",
        model: buildExecutionModel(campaign, input),
      };
    case "blueprint":
      return {
        id: "blueprint",
        model: buildSemanticsModel(campaign),
      };
    case "lineage":
      return {
        id: "lineage",
        model: buildProvenanceModel(campaign, input),
      };
  }
}

/**
 * Build the diagnosis panel ViewModel.
 *
 * The active representation is the only child model built; switching a tab
 * calls the campaign's `setRepresentation`, which rebuilds this tree.
 */
export function buildDiagnosisModel(
  campaign: CampaignView,
  input: DiagnosisInput,
): DiagnosisModel {
  const representation = input.representation;
  const active = TABS.find((tab) => tab.id === representation) ?? TABS[0];

  return {
    id: "diagnosis",
    representation,
    header: {
      title: active.title,
      meta: metaFor(campaign, representation),
      icon: active.icon,
      question: active.question,
    },
    tabs: TABS.map((tab) => ({
      id: tab.id,
      label: tab.label,
      hint: tab.hint,
      icon: tab.icon,
      active: tab.id === representation,
      command: () => input.setRepresentation(tab.id),
    })),
    child: buildChild(campaign, input, representation),
    commands: {
      setRepresentation: input.setRepresentation,
    },
  };
}
