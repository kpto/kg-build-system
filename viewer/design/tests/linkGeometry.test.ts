import { describe, expect, it } from "vitest";

import {
  linkPath,
  selfLoopPath,
  type LinkPoint,
} from "@/topology/model/linkGeometry";

function numbers(path: string): number[] {
  return path
    .split(/[^0-9eE.+-]+/)
    .filter((token) => token.length > 0)
    .map(Number);
}

function distance(a: LinkPoint, b: LinkPoint): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function cross(a: LinkPoint, b: LinkPoint): number {
  return a.x * b.y - a.y * b.x;
}

function dot(a: LinkPoint, b: LinkPoint): number {
  return a.x * b.x + a.y * b.y;
}

function cubic(path: string) {
  const values = numbers(path);
  return {
    start: { x: values[0], y: values[1] },
    control1: { x: values[2], y: values[3] },
    control2: { x: values[4], y: values[5] },
    end: { x: values[6], y: values[7] },
  };
}

describe("link geometry", () => {
  it("draws a self-loop as one circular arc outside the node", () => {
    const center = { x: 20, y: -10 };
    const nodeRadius = 10;
    const geometry = selfLoopPath(center, nodeRadius, 0);
    const values = numbers(geometry.path);
    // M x y A R R 0 1 0 x y
    const start = { x: values[0], y: values[1] };
    const loopRadius = values[2];
    const end = { x: values[7], y: values[8] };

    expect(geometry.path).toContain(" A ");
    expect(geometry.path).not.toContain(" C ");
    expect(values[5]).toBe(1); // large arc: the visible, outer part
    expect(loopRadius).toBeGreaterThan(0);
    expect(distance(start, center)).toBeCloseTo(nodeRadius, 6);
    expect(distance(end, center)).toBeCloseTo(nodeRadius, 6);

    // The loop circle is orthogonal to the node circle: the loop radius
    // vector and the node radius vector are perpendicular at both ends.
    const distanceToLoop = Math.hypot(nodeRadius, loopRadius);
    const loopCenter = { x: center.x + distanceToLoop, y: center.y };
    const endNormal = { x: end.x - center.x, y: end.y - center.y };
    const endRadial = { x: end.x - loopCenter.x, y: end.y - loopCenter.y };
    expect(dot(endNormal, endRadial)).toBeCloseTo(0, 6);
    expect(geometry.x).toBeCloseTo(end.x, 6);
    expect(geometry.y).toBeCloseTo(end.y, 6);
  });

  it("meets a straight link perpendicular to both surfaces", () => {
    const source = { id: "a", x: 0, y: 0 };
    const target = { id: "b", x: 100, y: 0 };
    const geometry = linkPath(source, target, 0, 10, 12);
    const values = numbers(geometry.path);
    const start = { x: values[0], y: values[1] };
    const end = { x: values[2], y: values[3] };

    expect(start).toEqual({ x: 10, y: 0 });
    expect(end).toEqual({ x: 88, y: 0 });
    expect(geometry.x).toBe(88);
    expect(geometry.y).toBe(0);
  });

  it("keeps two edges on one node pair on opposite sides", () => {
    const a = { id: "a", x: 0, y: 0 };
    const b = { id: "b", x: 100, y: 0 };
    const forward = linkPath(a, b, 0.4, 10, 10);
    const reverse = linkPath(b, a, -0.4, 10, 10);
    const ab = cubic(forward.path);
    const ba = cubic(reverse.path);

    // The two edges attach at four different points, not the same two points.
    expect(distance(ab.start, ba.end)).toBeGreaterThan(1);
    expect(distance(ab.end, ba.start)).toBeGreaterThan(1);

    // Each endpoint sits on its node surface and leaves along the radius, so
    // the link meets the surface perpendicularly.
    expect(distance(ab.start, a)).toBeCloseTo(10, 6);
    expect(distance(ab.end, b)).toBeCloseTo(10, 6);
    expect(
      cross(
        { x: ab.control1.x - ab.start.x, y: ab.control1.y - ab.start.y },
        { x: ab.start.x - a.x, y: ab.start.y - a.y },
      ),
    ).toBeCloseTo(0, 6);
    expect(
      cross(
        { x: ab.end.x - ab.control2.x, y: ab.end.y - ab.control2.y },
        { x: ab.end.x - b.x, y: ab.end.y - b.y },
      ),
    ).toBeCloseTo(0, 6);

    // The two edges bow to opposite sides of the canonical pair, so they never
    // overlap or cross near either node.
    const abMidY = (ab.control1.y + ab.control2.y) / 2;
    const baMidY = (ba.control1.y + ba.control2.y) / 2;
    expect(Math.sign(abMidY)).toBe(-Math.sign(baMidY));
  });

  it("keeps every link of a large parallel group distinct", () => {
    const a = { id: "a", x: 0, y: 0 };
    const b = { id: "b", x: 100, y: 0 };
    const paths = [-0.51, -0.17, 0.17, 0.51].map(
      (spread) => linkPath(a, b, spread, 10, 10).path,
    );

    expect(new Set(paths).size).toBe(paths.length);
  });

  it("reverses a parallel path without changing the world side", () => {
    const a = { id: "a", x: 0, y: 0 };
    const b = { id: "b", x: 100, y: 0 };
    const forward = cubic(linkPath(a, b, 0.4, 10, 10).path);
    const reverse = cubic(linkPath(b, a, 0.4, 10, 10).path);

    // Both directions use the same canonical curve; the reverse path is the
    // same curve traversed from the other end.
    expect(reverse.start.x).toBeCloseTo(forward.end.x, 6);
    expect(reverse.start.y).toBeCloseTo(forward.end.y, 6);
    expect(reverse.end.x).toBeCloseTo(forward.start.x, 6);
    expect(reverse.end.y).toBeCloseTo(forward.start.y, 6);
    expect(reverse.control1.x).toBeCloseTo(forward.control2.x, 6);
    expect(reverse.control1.y).toBeCloseTo(forward.control2.y, 6);
    expect(reverse.control2.x).toBeCloseTo(forward.control1.x, 6);
    expect(reverse.control2.y).toBeCloseTo(forward.control1.y, 6);
  });
});
