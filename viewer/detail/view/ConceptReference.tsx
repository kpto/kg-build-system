import type { ConceptReference } from "@/lib/concepts";
import { ConceptPill } from "./ConceptPill";

/**
 * One navigable concept reference, drawn as the layer's inline pill. The pill
 * resolves its own document; a caller supplies the reference and nothing else.
 */
export function ConceptReferenceChip({
  reference,
  className,
  size = "sm",
}: {
  reference: ConceptReference;
  className?: string;
  size?: "sm" | "md";
}) {
  return (
    <ConceptPill
      concept={reference.concept}
      name={reference.name}
      component={reference.target?.component}
      property={reference.target?.property}
      ownerConcept={reference.target?.ownerConcept}
      stepId={reference.target?.stepId}
      className={className}
      size={size}
    />
  );
}
