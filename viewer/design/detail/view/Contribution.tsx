"use client";

import type { ConstitutionModel } from "../model/constitution";
import { Constitution } from "./Constitution";
import { DetailBand } from "./DetailChrome";

/**
 * One level above the subject, drawn with the same constitution DAG: the
 * subject's purpose at the bottom and its contributions above it.
 */
export function ContributionSection({ model }: { model: ConstitutionModel }) {
  return (
    <DetailBand
      title="Contribution"
      question="Which layer depends on this subject?"
      testId="detail-contribution"
    >
      <Constitution model={model} label="Contribution" />
    </DetailBand>
  );
}
