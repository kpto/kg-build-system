import { CampaignController } from "@/review/binding/CampaignController";

/**
 * The campaign entry point.
 *
 * The React binding owns the controller state and builds the model tree; the
 * views only bind to the injected models.
 */
export function ReviewCampaign() {
  return <CampaignController />;
}
