import type { IconToken } from "@/shared/model/hierarchy";
import type {
  CampaignCounts,
  CampaignView,
  Task,
} from "@/shared/model/campaign";
import type { SearchResult } from "@/lib/types";

/**
 * Framework-agnostic campaign model.
 *
 * It is the window level of the hierarchy: the campaign header, the status bar
 * and the campaign view every domain model reads. It contains no React, JSX or
 * view reference; a React binding injects it into `CampaignFrameView`.
 */

/** The header's tab identity. "explorer" is the UI name for the explore task. */
export type CampaignTaskTabId = "map" | "explorer" | "review";

export interface CampaignTaskTabModel {
  id: CampaignTaskTabId;
  task: Task;
  label: string;
  /** Keyboard/behaviour hint, rendered as the tab title. */
  hint: string;
  icon: IconToken;
}

/** Global search state. The query and results belong to the campaign. */
export interface CampaignSearchModel {
  query: string;
  results: SearchResult[];
  onQuery: (query: string) => void;
  onSelect: (result: SearchResult) => void;
}

/** Snapshot import affordance and the error the last import produced. */
export interface CampaignImportModel {
  error?: string;
  onFile: (file: File) => void;
}

export interface CampaignHeaderModel {
  title: string;
  /** Identity line: snapshot name and step count. */
  snapshot: string;
  task: Task;
  tabs: CampaignTaskTabModel[];
  onTask: (task: Task) => void;
  review: {
    open: number;
    total: number;
  };
  search: CampaignSearchModel;
  import: CampaignImportModel;
}

export interface CampaignBuildStatusModel {
  failures: number;
  compileOnly: boolean;
  metaComponents: number;
}

export interface CampaignStatusModel {
  counts: CampaignCounts;
  review: {
    resolved: number;
    total: number;
  };
  score?: number;
  impact?: string;
  build: CampaignBuildStatusModel;
}

export interface CampaignModel {
  header: CampaignHeaderModel;
  status: CampaignStatusModel;
  view: CampaignView;
}
