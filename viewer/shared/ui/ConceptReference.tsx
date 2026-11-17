import type { ConceptReference } from "@/lib/concepts";
import { ConceptPill } from "./ConceptPill";

/**
 * One navigable concept reference, drawn as the layer's inline pill. The same
 * component renders an asset, table or projection wherever a reference
 * appears; the mark and colour come from the concept catalogue.
 */
export function ConceptReferenceChip({
  reference,
  onOpen,
  className,
  size = "sm",
}: {
  reference: ConceptReference;
  onOpen?(): void;
  className?: string;
  size?: "sm" | "md";
}) {
  return (
    <ConceptPill
      concept={reference.concept}
      name={reference.name}
      onOpen={onOpen}
      className={className}
      size={size}
    />
  );
}
