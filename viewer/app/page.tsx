import { ReviewCampaign } from "@/review/ReviewCampaign";

/**
 * The page is the campaign entry point. The review campaign owns the snapshot,
 * review state and task switch; the domains own their panels and canvas bodies.
 */
export default function Page() {
  return <ReviewCampaign />;
}
