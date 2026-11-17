"use client";

/**
 * The fulfilment map: the two axes of a graph and the binding that meets them.
 *
 * Left is the record axis (what the graph asserts), right is the relation axis
 * (what the domain supplies) and the centre is the binding that fulfils one
 * with the other. The map is one renderer for every detail document; a subject
 * only changes which side is emphasised.
 */

import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, ChevronsLeftRight } from "lucide-react";

import {
  bindingRelations,
  buildAxisMap,
  fulfilmentKey,
  unresolvedRelations,
  type AxisBinding,
  type AxisRecord,
  type AxisRelation,
  type AxisSubject,
} from "@/lib/axis";
import type { ViewerIndex } from "@/lib/types";
import {
  AssetPill,
  BindingPill,
  ConceptPill,
  DerivedRelationPill,
  SourceRelationPill,
} from "@/shared/ui/ConceptPill";
import styles from "./fulfilment.module.css";

export interface AxisOpenTarget {
  kind: "node" | "edge" | "table" | "projection" | "asset";
  name: string;
}

function countLabel(count: number, noun: string): string {
  if (count === 1) return `${count} ${noun}`;
  const plural = noun.endsWith("y")
    ? `${noun.slice(0, -1)}ies`
    : noun.endsWith("s")
      ? noun
      : `${noun}s`;
  return `${count} ${plural}`;
}

function RecordCard({
  record,
  active,
  onOpen,
}: {
  record: AxisRecord;
  active: boolean;
  onOpen?(target: AxisOpenTarget): void;
}) {
  return (
    <article
      className={styles.card}
      data-kind={record.kind}
      data-active={active || undefined}
    >
      <header className={styles.cardHead}>
        <ConceptPill
          concept={record.kind}
          name={record.name}
          size="md"
          onOpen={
            onOpen
              ? () => onOpen({ kind: record.kind, name: record.name })
              : undefined
          }
          title={`Open the ${record.kind} document`}
        />
        <span className={styles.cardTag}>
          {record.abstract ? "abstract category" : record.kind}
        </span>
      </header>
      {record.labels.length ? (
        <p className={styles.cardMeta}>{record.labels.join(" · ")}</p>
      ) : null}
      {record.properties.length ? (
        <div className={styles.chips}>
          {record.properties.slice(0, 10).map((property) => (
            <span key={property.name} className={styles.chip}>
              {property.name}
              <em>{property.type}</em>
            </span>
          ))}
          {record.properties.length > 10 ? (
            <span className={styles.chip}>+{record.properties.length - 10}</span>
          ) : null}
        </div>
      ) : (
        <p className={styles.cardEmpty}>No properties are declared.</p>
      )}
      <footer className={styles.cardFoot}>
        <span>{countLabel(record.properties.length, "property")}</span>
        <span>
          {record.meaningCount
            ? countLabel(record.meaningCount, "meaning unit")
            : "meaning omitted"}
        </span>
      </footer>
    </article>
  );
}

function BindingCard({ binding }: { binding: AxisBinding }) {
  return (
    <article className={styles.binding} data-kind={binding.targetKind}>
      <header className={styles.bindingHead}>
        <span className={styles.bindingIndex}>#{binding.index}</span>
        <ConceptPill
          concept={binding.targetKind}
          name={binding.target}
          size="md"
        />
      </header>
      {binding.purpose ? (
        <p className={styles.bindingPurpose}>{binding.purpose}</p>
      ) : null}
      <dl className={styles.bindingFacts}>
        <div>
          <dt>identity</dt>
          <dd>
            {binding.identityFields.length
              ? binding.identityFields.join(", ")
              : "not declared"}
          </dd>
        </div>
        <div>
          <dt>grain</dt>
          <dd>
            {binding.relations.length
              ? bindingRelations(binding)
              : "no row source"}
          </dd>
        </div>
        <div>
          <dt>coverage</dt>
          <dd>{countLabel(binding.propertyCount, "property")} written</dd>
        </div>
      </dl>
      <footer className={styles.cardFoot}>
        <span>{binding.debugName ?? "unnamed binding"}</span>
        <span>
          {binding.limitations.length
            ? countLabel(binding.limitations.length, "limitation")
            : binding.meaningCount
              ? countLabel(binding.meaningCount, "meaning unit")
              : "fulfilment not stated"}
        </span>
      </footer>
    </article>
  );
}

function RelationCard({
  relation,
  active,
  onOpen,
}: {
  relation: AxisRelation;
  active: boolean;
  onOpen?(target: AxisOpenTarget): void;
}) {
  const documentKind = relation.kind === "source" ? "table" : "projection";
  return (
    <article
      className={styles.card}
      data-kind={relation.kind}
      data-active={active || undefined}
    >
      <header className={styles.cardHead}>
        <ConceptPill
          concept={documentKind}
          name={relation.name}
          size="md"
          onOpen={
            onOpen
              ? () => onOpen({ kind: documentKind, name: relation.name })
              : undefined
          }
          title={`Open the ${
            relation.kind === "source" ? "source" : "derived"
          } relation document`}
        />
        <span className={styles.cardTag}>
          {relation.kind === "source" ? "source relation" : "derived relation"}
        </span>
      </header>
      {relation.scanned.length ? (
        <p className={styles.cardInline}>
          scans
          {relation.scanned.map((name) => (
            <SourceRelationPill key={name} name={name} />
          ))}
        </p>
      ) : relation.asset ? (
        <p className={styles.cardInline}>
          asset <AssetPill name={relation.asset} />
        </p>
      ) : null}
      <div className={styles.chips}>
        {relation.columns.slice(0, 12).map((column) => (
          <span key={column.name} className={styles.chip}>
            {column.name}
            <em>{column.type}</em>
          </span>
        ))}
        {relation.columns.length > 12 ? (
          <span className={styles.chip}>+{relation.columns.length - 12}</span>
        ) : null}
      </div>
      <footer className={styles.cardFoot}>
        <span>{countLabel(relation.columns.length, "column")}</span>
        <span>
          {relation.meaningCount
            ? countLabel(relation.meaningCount, "meaning unit")
            : "contract not stated"}
        </span>
      </footer>
    </article>
  );
}

function CompactRow({
  binding,
  relations,
  active,
  onOpen,
}: {
  binding: AxisBinding;
  relations: AxisRelation[];
  active: boolean;
  onOpen?(target: AxisOpenTarget): void;
}) {
  const resolved = relations.filter((relation) =>
    binding.relations.includes(relation.name),
  );
  return (
    <div className={styles.row} data-active={active || undefined}>
      <ConceptPill
        concept={binding.targetKind}
        name={binding.target}
        onOpen={
          onOpen
            ? () => onOpen({ kind: binding.targetKind, name: binding.target })
            : undefined
        }
        title="Open the record document"
      />
      <ArrowLeft aria-hidden className={styles.rowArrow} />
      <span className={styles.rowBinding}>
        <BindingPill
          name={`#${binding.index}`}
          title={binding.debugName ?? `binding #${binding.index}`}
        />
        {binding.identityFields.length ? (
          <span className={styles.rowIdentity}>
            {binding.identityFields.join(", ")}
          </span>
        ) : null}
        <span className={styles.rowCoverage}>
          {countLabel(binding.propertyCount, "property")}
        </span>
      </span>
      <ArrowRight aria-hidden className={styles.rowArrow} />
      <span className={styles.rowRelations}>
        {resolved.length ? (
          resolved.map((relation) =>
            relation.kind === "source" ? (
              <SourceRelationPill
                key={relation.name}
                name={relation.name}
                onOpen={
                  onOpen
                    ? () => onOpen({ kind: "table", name: relation.name })
                    : undefined
                }
              />
            ) : (
              <DerivedRelationPill
                key={relation.name}
                name={relation.name}
                onOpen={
                  onOpen
                    ? () => onOpen({ kind: "projection", name: relation.name })
                    : undefined
                }
              />
            ),
          )
        ) : (
          <span className={styles.rowUnresolved}>
            {bindingRelations(binding)}
          </span>
        )}
      </span>
    </div>
  );
}

interface BindingGroup {
  key: string;
  relations: string[];
  bindings: AxisBinding[];
  records: Array<{ kind: "node" | "edge"; name: string }>;
}

function groupBindings(bindings: AxisBinding[]): BindingGroup[] {
  const groups = new Map<string, BindingGroup>();
  for (const binding of bindings) {
    const key = [...binding.relations].sort().join("\u0000") || "unbound";
    const group = groups.get(key) ?? {
      key,
      relations: [...binding.relations].sort(),
      bindings: [],
      records: [],
    };
    group.bindings.push(binding);
    if (
      !group.records.some(
        (record) =>
          record.kind === binding.targetKind && record.name === binding.target,
      )
    ) {
      group.records.push({ kind: binding.targetKind, name: binding.target });
    }
    groups.set(key, group);
  }
  return [...groups.values()].sort((left, right) =>
    left.relations.join(",").localeCompare(right.relations.join(",")),
  );
}

function GroupRow({
  group,
  relations,
  active,
  onOpen,
}: {
  group: BindingGroup;
  relations: AxisRelation[];
  active: boolean;
  onOpen?(target: AxisOpenTarget): void;
}) {
  const resolved = relations.filter((relation) =>
    group.relations.includes(relation.name),
  );
  const properties = group.bindings.reduce(
    (total, binding) => total + binding.propertyCount,
    0,
  );
  return (
    <div className={styles.row} data-active={active || undefined}>
      <span className={styles.rowRelations}>
        {group.records.slice(0, 3).map((record) => (
          <ConceptPill
            key={`${record.kind}:${record.name}`}
            concept={record.kind}
            name={record.name}
            onOpen={
              onOpen
                ? () => onOpen({ kind: record.kind, name: record.name })
                : undefined
            }
            title={`Open the ${record.kind} document`}
          />
        ))}
        {group.records.length > 3 ? (
          <span className={styles.rowUnresolved}>
            +{group.records.length - 3} records
          </span>
        ) : null}
      </span>
      <ArrowLeft aria-hidden className={styles.rowArrow} />
      <span className={styles.rowBinding}>
        <span className={styles.bindingIndex}>
          {group.bindings.length} {group.bindings.length === 1 ? "binding" : "bindings"}
        </span>
        <span className={styles.rowCoverage}>
          {countLabel(properties, "property")}
        </span>
      </span>
      <ArrowRight aria-hidden className={styles.rowArrow} />
      <span className={styles.rowRelations}>
        {resolved.length ? (
          resolved.map((relation) =>
            relation.kind === "source" ? (
              <SourceRelationPill
                key={relation.name}
                name={relation.name}
                onOpen={
                  onOpen
                    ? () => onOpen({ kind: "table", name: relation.name })
                    : undefined
                }
              />
            ) : (
              <DerivedRelationPill
                key={relation.name}
                name={relation.name}
                onOpen={
                  onOpen
                    ? () => onOpen({ kind: "projection", name: relation.name })
                    : undefined
                }
              />
            ),
          )
        ) : (
          <span className={styles.rowUnresolved}>
            no published relation
          </span>
        )}
      </span>
    </div>
  );
}

export function FulfilmentMap({
  index,
  subject,
  onOpen,
  defaultExpanded = false,
  narrow = false,
}: {
  index: ViewerIndex;
  subject: AxisSubject;
  onOpen?(target: AxisOpenTarget): void;
  defaultExpanded?: boolean;
  /** Stack the row for a narrow inspector; the full map is not offered. */
  narrow?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const map = useMemo(() => buildAxisMap(index, subject), [index, subject]);
  if (!map) return null;
  const missing = unresolvedRelations(map);
  const groups = groupBindings(map.bindings);
  const useGroups = map.bindings.length > 12;
  const visibleGroups = useGroups ? groups.slice(0, 10) : groups;
  const activeRecord =
    subject.kind === "node" ||
    subject.kind === "edge" ||
    subject.kind === "abstract"
      ? subject.component
      : undefined;
  const activeRelation =
    subject.kind === "relation" || subject.kind === "projection"
      ? subject.component
      : undefined;

  return (
    <div className={styles.map} data-testid="fulfilment-map" data-narrow={narrow || undefined}>
      <div className={styles.mapBar}>
        <p className={styles.mapSummary}>
          <span className={styles.axisLabel}>records</span>
          <ChevronsLeftRight aria-hidden className={styles.mapIcon} />
          <span className={styles.axisLabel}>relations</span>
          <span className={styles.mapCounts}>
            {countLabel(map.records.length, "record")} ·{" "}
            {countLabel(map.bindings.length, "fulfilment")} ·{" "}
            {countLabel(map.relations.length, "relation")}
          </span>
        </p>
        {narrow ? null : (
          <button
            type="button"
            className={styles.mapToggle}
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "Compact" : "Full axis map"}
          </button>
        )}
      </div>

      {expanded ? (
        <div className={styles.columns}>
          <section className={styles.column} aria-label="Graph records">
            <header className={styles.columnHead}>
              <span>Graph · records</span>
              <span>{map.records.length}</span>
            </header>
            <div className={styles.columnBody}>
              {map.records.length ? (
                map.records.map((record) => (
                  <RecordCard
                    key={`${record.kind}:${record.name}`}
                    record={record}
                    active={record.name === activeRecord}
                    onOpen={onOpen}
                  />
                ))
              ) : (
                <p className={styles.cardEmpty}>
                  No record is bound by this relation.
                </p>
              )}
            </div>
          </section>

          <section
            className={styles.column}
            data-axis="fulfilment"
            aria-label="Bindings"
          >
            <header className={styles.columnHead}>
              <span>Fulfilment</span>
              <span>{map.bindings.length}</span>
            </header>
            <div className={styles.columnBody}>
              {map.bindings.length ? (
                map.bindings.map((binding) => (
                  <BindingCard key={fulfilmentKey(binding)} binding={binding} />
                ))
              ) : (
                <p className={styles.cardEmpty}>
                  No binding meets these two axes.
                </p>
              )}
            </div>
          </section>

          <section className={styles.column} aria-label="Domain relations">
            <header className={styles.columnHead}>
              <span>Relations · domain</span>
              <span>{map.relations.length}</span>
            </header>
            <div className={styles.columnBody}>
              {map.relations.length ? (
                map.relations.map((relation) => (
                  <RelationCard
                    key={relation.name}
                    relation={relation}
                    active={relation.name === activeRelation}
                    onOpen={onOpen}
                  />
                ))
              ) : (
                <p className={styles.cardEmpty}>
                  No relation is published for this subject.
                </p>
              )}
            </div>
          </section>
        </div>
      ) : (
        <div className={styles.rows}>
          {map.bindings.length ? (
            useGroups ? (
              visibleGroups.map((group) => (
                <GroupRow
                  key={group.key}
                  group={group}
                  relations={map.relations}
                  active={group.relations.includes(activeRelation ?? "")}
                  onOpen={onOpen}
                />
              ))
            ) : (
              map.bindings.map((binding) => (
                <CompactRow
                  key={fulfilmentKey(binding)}
                  binding={binding}
                  relations={map.relations}
                  active={
                    binding.target === activeRecord ||
                    binding.relations.includes(activeRelation ?? "")
                  }
                  onOpen={onOpen}
                />
              ))
            )
          ) : (
            <p className={styles.cardEmpty}>
              No binding meets these two axes.
            </p>
          )}
          {useGroups ? (
            <p className={styles.groupNote}>
              {groups.length > visibleGroups.length
                ? `Showing ${visibleGroups.length} of ${groups.length} relation groups; open the full axis map to read every binding.`
                : `${groups.length} relation groups, each stating the rows it supplies. Open the full axis map to read every binding.`}
            </p>
          ) : null}
        </div>
      )}

      {missing.length ? (
        <p className={styles.unresolved}>
          The snapshot names {missing.join(", ")} without publishing the
          relation; the binding still states the grain it reads.
        </p>
      ) : null}
    </div>
  );
}
