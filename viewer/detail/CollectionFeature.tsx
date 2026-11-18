"use client";

/**
 * A virtual collection document: one layer read as a group.
 *
 * The pages are Dependency (the layer DAG below), Dependant (one layer above),
 * Items (the members of the layer) and Coverage. A collection has no Meaning
 * page: it declares no purpose of its own.
 */

import { useMemo } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import { ConceptPill } from "@/detail/view/ConceptPill";
import { activeDocument, documentSelection, type WorkspaceProps } from "@/workbench/types";
import {
  collectionModel,
  type CollectionItem,
  type CollectionLayer,
  type CollectionRef,
} from "./model/collection";
import {
  DetailBand,
  DetailDocument,
  MemberTable,
  type MemberRow,
} from "./view/DetailChrome";
import { cx } from "@/shared/ui/theme";
import styles from "./detail.module.css";

function openCollection(
  props: WorkspaceProps,
  ref: CollectionRef,
): void {
  props.actions.openTab({
    selection: {
      kind: "collection",
      collection: ref.id,
      component: ref.component,
      name: ref.component,
    },
    preview: true,
  });
}

function LayerRow({
  layer,
  onOpen,
}: {
  layer: CollectionLayer;
  onOpen(ref: CollectionRef): void;
}) {
  const content = (
    <>
      <span className={styles.layerRail} aria-hidden>
        <span className={styles.layerDot} data-current={layer.current ? "true" : undefined} />
      </span>
      <ConceptGlyph concept={layer.concept} className={styles.layerMark} />
      <span className={styles.layerBody}>
        <span className={styles.layerTitle}>{layer.title}</span>
        {layer.note ? <span className={styles.layerNote}>{layer.note}</span> : null}
      </span>
      <span className={styles.layerCount}>{layer.count}</span>
    </>
  );

  if (layer.collection && !layer.current) {
    return (
      <li className={styles.layerItem}>
        <button
          type="button"
          className={cx(styles.layerRow, styles.layerButton)}
          data-current={layer.current ? "true" : undefined}
          onClick={() => onOpen(layer.collection as CollectionRef)}
          title={`Open the ${layer.title} collection`}
        >
          {content}
        </button>
      </li>
    );
  }

  return (
    <li className={styles.layerItem}>
      <div
        className={styles.layerRow}
        data-current={layer.current ? "true" : undefined}
      >
        {content}
      </div>
    </li>
  );
}

function LayerAxis({
  title,
  layers,
  onOpen,
}: {
  title: string;
  layers: CollectionLayer[];
  onOpen(ref: CollectionRef): void;
}) {
  if (!layers.length) return null;
  return (
    <div className={styles.layerAxis}>
      <p className={styles.layerAxisTitle}>{title}</p>
      <ol className={styles.layerList}>
        {layers.map((layer) => (
          <LayerRow key={layer.key} layer={layer} onOpen={onOpen} />
        ))}
      </ol>
    </div>
  );
}

function ItemLabel({
  item,
  onOpen,
}: {
  item: CollectionItem;
  onOpen(ref: CollectionRef): void;
}) {
  if (item.collection) {
    return (
      <button
        type="button"
        className={styles.collectionItemButton}
        onClick={() => onOpen(item.collection as CollectionRef)}
        title={`Open ${item.name}`}
      >
        <ConceptGlyph concept={item.concept} className={styles.collectionItemMark} />
        <span>{item.name}</span>
      </button>
    );
  }
  return (
    <ConceptPill
      concept={item.concept}
      name={item.name}
      component={item.component}
      property={item.property}
      ownerConcept={item.ownerConcept}
      bindingIndex={item.bindingIndex}
      stepId={item.stepId}
    />
  );
}

function conceptForBand(kind: string): ConceptKind {
  switch (kind) {
    case "dependency":
      return "graph";
    case "dependant":
      return "edge";
    case "items":
      return "node";
    default:
      return "semantics";
  }
}

export function CollectionEditor(props: WorkspaceProps) {
  const selection = documentSelection(activeDocument(props.state));
  const id = selection?.collection ?? "assets";
  const component = selection?.component;
  const model = useMemo(
    () => collectionModel(props.state.index, id, component),
    [props.state.index, id, component],
  );

  const open = (ref: CollectionRef) => openCollection(props, ref);
  const itemRows: MemberRow[] = model.items.rows.map((item) => ({
    key: item.key,
    title: item.name,
    cells: [<ItemLabel key="label" item={item} onOpen={open} />, ...item.cells],
  }));

  return (
    <DetailDocument
      testId="collection-editor"
      concept={model.concept}
      kicker={model.kicker}
      title={model.title}
      subtitle={model.subtitle}
      facts={model.facts}
    >
      <DetailBand
        concept={conceptForBand("dependency")}
        title="Dependency"
        question="How does this collection come to be?"
        testId="collection-dependency"
      >
        {model.dependency.axes.length ? (
          <div className={styles.layerAxes}>
            {model.dependency.axes.map((entry) => (
              <LayerAxis
                key={entry.axis}
                title={entry.label}
                layers={entry.layers}
                onOpen={open}
              />
            ))}
          </div>
        ) : (
          <p className={styles.coverageReading}>{model.dependency.empty}</p>
        )}
      </DetailBand>

      <DetailBand
        concept={conceptForBand("dependant")}
        title="Dependant"
        question="Which layer depends on this collection?"
        testId="collection-dependant"
      >
        {model.dependants.axes.length ? (
          <div className={styles.layerAxes}>
            {model.dependants.axes.map((entry) => (
              <LayerAxis
                key={entry.axis}
                title={entry.label}
                layers={entry.layers}
                onOpen={open}
              />
            ))}
          </div>
        ) : (
          <p className={styles.coverageReading}>{model.dependants.empty}</p>
        )}
      </DetailBand>

      <DetailBand
        concept={model.concept}
        title="Items"
        question="Which participants belong to this collection?"
        testId="collection-items"
      >
        <MemberTable
          columns={model.items.columns}
          template={model.items.template}
          rows={itemRows}
          empty={model.items.empty}
        />
      </DetailBand>

      <DetailBand
        concept={conceptForBand("coverage")}
        title="Coverage"
        question="How complete is this collection?"
        testId="collection-coverage"
      >
        <ul className={styles.coverageList}>
          {model.coverage.map((row) => (
            <li key={row.key} className={styles.coverageItem}>
              <span className={styles.coverageMeasure}>{row.measure}</span>
              <span className={styles.coverageCount}>{row.count}</span>
              <span className={styles.coverageReading}>{row.reading}</span>
            </li>
          ))}
        </ul>
      </DetailBand>
    </DetailDocument>
  );
}
