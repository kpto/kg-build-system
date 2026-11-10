import type { CSSProperties } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { concepts } from "./concepts";

/** A small concept glyph; colour is the concept's representative colour. */
export function ConceptGlyph({
  concept,
  className,
}: {
  concept: ConceptKind;
  className?: string;
}) {
  const definition = concepts[concept];
  const Icon = definition.icon;
  return (
    <Icon
      aria-hidden
      className={className}
      style={{ color: definition.color }}
      data-concept={concept}
    />
  );
}

/** A large concept mark for a detail banner: the kind's logo in its colour. */
export function ConceptMark({
  concept,
  className,
}: {
  concept: ConceptKind;
  className?: string;
}) {
  const definition = concepts[concept];
  const Icon = definition.icon;
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
      <Icon aria-hidden />
    </span>
  );
}
