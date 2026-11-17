import type { CSSProperties } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { concepts, LayerMark } from "./concepts";

/**
 * A small concept glyph; the mark and colour come from the concept catalogue.
 * Use `active` for a current or selected concept.
 */
export function ConceptGlyph({
  concept,
  className,
  active = false,
}: {
  concept: ConceptKind;
  className?: string;
  active?: boolean;
}) {
  const definition = concepts[concept];
  return (
    <LayerMark
      concept={concept}
      className={className}
      active={active}
      style={{ color: definition.color }}
    />
  );
}

/**
 * A large concept mark for a detail banner: the kind's mark in its colour.
 * The parent sets the box and the sizes; the catalogue supplies the mark.
 */
export function ConceptMark({
  concept,
  className,
  active = false,
}: {
  concept: ConceptKind;
  className?: string;
  active?: boolean;
}) {
  const definition = concepts[concept];
  return (
    <span
      className={className}
      data-concept={concept}
      role="img"
      aria-label={`${definition.label} document`}
      title={definition.label}
      style={
        {
          "--concept-color": definition.color,
        } as CSSProperties
      }
    >
      <LayerMark concept={concept} active={active} />
    </span>
  );
}
