import { readFileSync } from "node:fs";
import { loadSnapshotFromObject } from "../lib/load";
import { buildViewerIndex } from "../lib/indexes";

const text = readFileSync(
  new URL("../public/data/reference.snapshot.json", import.meta.url),
  "utf8",
);

export const snapshot = loadSnapshotFromObject(JSON.parse(text));
export const index = buildViewerIndex(snapshot);
