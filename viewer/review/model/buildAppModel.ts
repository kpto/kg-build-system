import type {
  AuditInput,
  DiagnosisInput,
  NavigatorInput,
} from "@/shared/model/builders";
import {
  buildAuditModel,
  type AuditModel,
} from "@/audit/model/AuditModel";
import type { DiagnosisModel } from "@/diagnosis/model/DiagnosisModel";
import { buildDiagnosisModel } from "@/diagnosis/model/buildDiagnosisModel";
import type { NavigatorModel } from "@/navigation/model/NavigatorModel";
import { buildNavigatorModel } from "@/navigation/model/buildNavigatorModel";
import type { PropertiesModel } from "@/properties/model/PropertiesModel";
import { buildPropertiesModel } from "@/properties/model/buildPropertiesModel";
import type { TopologyModel } from "@/topology/model/TopologyModel";
import { buildTopologyModel } from "@/topology/model/buildTopologyModel";
import {
  buildCampaignModel,
  type CampaignModelInput,
} from "./buildCampaignModel";
import type { CampaignModel } from "./CampaignModel";

/**
 * The task level of the hierarchy. A task names its panels and their models;
 * it does not name a view.
 */
export interface OrientTaskModel {
  kind: "map";
  topology: TopologyModel;
}

export interface DiagnoseTaskModel {
  kind: "explore";
  navigator: NavigatorModel;
  diagnosis: DiagnosisModel;
  properties: PropertiesModel;
}

export interface AuditTaskModel {
  kind: "review";
  audit: AuditModel;
}

export type AppTaskModel = OrientTaskModel | DiagnoseTaskModel | AuditTaskModel;

export interface AppModel {
  campaign: CampaignModel;
  task: AppTaskModel;
}

/**
 * The controller state plus the presentation state each domain builder needs.
 */
export interface AppModelInput extends CampaignModelInput {
  navigator: NavigatorInput;
  diagnosis: DiagnosisInput;
  audit: AuditInput;
}

/**
 * The composition root of the viewer.
 *
 * It builds the campaign model and the model tree of exactly one active task,
 * then hands both to the React binding. A task that is not active is not built.
 */
export function buildAppModel(input: AppModelInput): AppModel {
  const campaign = buildCampaignModel(input);
  const view = campaign.view;

  switch (input.task) {
    case "map":
      return {
        campaign,
        task: {
          kind: "map",
          topology: buildTopologyModel(view),
        },
      };
    case "explore":
      return {
        campaign,
        task: {
          kind: "explore",
          navigator: buildNavigatorModel(view, input.navigator),
          diagnosis: buildDiagnosisModel(view, input.diagnosis),
          properties: buildPropertiesModel(view),
        },
      };
    case "review":
      return {
        campaign,
        task: {
          kind: "review",
          audit: buildAuditModel(view, input.audit),
        },
      };
  }
}
