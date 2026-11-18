/* Iteration graph layout: one handler for the console and the standalone demo.
 *
 * The model is a single pass order. Nothing downstream re-decides what an
 * earlier pass settled:
 *
 *   1. rows      topological order of `prev`, so a parent is always below its
 *                children; timestamps only break ties
 *   2. lanes     a column per trunk; siblings never share one, and a column is
 *                released when a merge absorbs it
 *   3. ports     the x a line leaves a card's bottom and enters a card's top
 *   4. channels  the one row gap each cross-lane line bends in, chosen by
 *                clearance, then a slot inside that gap
 *   5. sizes     a gap is as tall as the lines that bend in it, and every bend
 *                is placed from the gap, so the space and the drawing agree
 *   6. paths     one elbow function for every line; a ring column outside the
 *                lanes is the only alternative strategy and it is allocated
 *
 * Invariants:
 *   - a bend lies inside one row gap, and horizontal runs live in gaps, which
 *     are free of cards in every lane, so an edge never crosses a card
 *   - the gap between rows r and r+1 is rowGap + 2 * TURN_RADIUS * lines
 *   - bends in one gap are evenly spaced with equal outer margins
 *   - corrupt input (cycle, dangling parent, duplicate id, missing prev/ts)
 *     degrades without throwing and without stacking two cards
 *
 * `laneWidth` may be smaller than `cardWidth`: neighbouring columns then
 * interlock, which buys horizontal space without moving any line, because every
 * line sits on a card centre and a centre is never inside a neighbouring card.
 */
(function (global) {
  "use strict";

  var TURN_RADIUS = 14;
  var LINE_PITCH = 2 * TURN_RADIUS;
  var RING_GAP = 20;
  var RING_PITCH = 16;

  var DEFAULTS = {
    cardWidth: 264,
    cardHeight: 220,
    laneWidth: 292,
    rowGap: 30,
    padding: 12,
  };

  function round(value) {
    return Math.round(value * 100) / 100;
  }

  function timestampOf(event) {
    if (typeof event.timestamp === "string") return event.timestamp;
    if (typeof event.ts === "string") return event.ts;
    if (typeof event.at === "string") return event.at;
    return "";
  }

  function newestFirst(left, right) {
    if (left.ts !== right.ts) return left.ts < right.ts ? 1 : -1;
    if (left.id === right.id) return 0;
    return left.id < right.id ? 1 : -1;
  }

  function normalise(events, byId) {
    var records = [];
    (Array.isArray(events) ? events : []).forEach(function (raw) {
      if (!raw || typeof raw.id !== "string" || byId.has(raw.id)) return;
      var record = {
        id: raw.id,
        ts: timestampOf(raw),
        type: raw.type || raw.kind || "event",
        title: raw.title || raw.id,
        source: raw,
        prev: Array.isArray(raw.prev) ? raw.prev : [],
        parents: [],
        children: [],
        row: 0,
        lane: 0,
      };
      byId.set(record.id, record);
      records.push(record);
    });
    records.forEach(function (record) {
      var seen = Object.create(null);
      record.prev.forEach(function (id) {
        if (typeof id !== "string" || seen[id] || id === record.id) return;
        if (!byId.has(id)) return;
        seen[id] = true;
        record.parents.push(id);
      });
    });
    records.forEach(function (record) {
      record.parents.forEach(function (id) {
        byId.get(id).children.push(record.id);
      });
    });
    return records;
  }

  // Children before parents. A node becomes ready once every one of its
  // children has been placed, which makes "parent below child" a property of
  // the ordering rather than a hope about timestamps.
  function orderRows(records, byId) {
    var waiting = new Map();
    records.forEach(function (record) {
      waiting.set(record.id, record.children.length);
    });
    var ready = records.filter(function (record) {
      return record.children.length === 0;
    });
    var rows = [];
    var placed = new Set();
    while (ready.length) {
      ready.sort(newestFirst);
      var record = ready.shift();
      if (placed.has(record.id)) continue;
      placed.add(record.id);
      rows.push(record);
      record.parents.forEach(function (id) {
        var left = (waiting.get(id) || 0) - 1;
        waiting.set(id, left);
        if (left === 0) ready.push(byId.get(id));
      });
    }
    records
      .filter(function (record) {
        return !placed.has(record.id);
      })
      .sort(newestFirst)
      .forEach(function (record) {
        rows.push(record);
      });
    return rows;
  }

  // Oldest first: a child takes the column of the parent below it, and the
  // first child to reach that parent keeps it. Every later sibling needs a
  // column of its own, so a fork is always visible.
  function assignLanes(rows) {
    var laneOf = new Map();
    var occupant = [];
    function claim() {
      var index = 0;
      while (index < occupant.length && occupant[index] !== null) index += 1;
      if (index === occupant.length) occupant.push(null);
      return index;
    }
    for (var r = rows.length - 1; r >= 0; r -= 1) {
      var record = rows[r];
      var lane = -1;
      record.parents
        .map(function (id) {
          return laneOf.get(id);
        })
        .filter(function (value) {
          return value !== undefined;
        })
        .sort(function (left, right) {
          return left - right;
        })
        .forEach(function (candidate) {
          if (lane !== -1) return;
          var holder = occupant[candidate];
          if (holder === null || holder === undefined || record.parents.indexOf(holder) !== -1) {
            lane = candidate;
          }
        });
      if (lane === -1) lane = claim();
      laneOf.set(record.id, lane);
      occupant[lane] = record.id;
      record.parents.forEach(function (id) {
        var parentLane = laneOf.get(id);
        if (parentLane !== undefined && parentLane !== lane && occupant[parentLane] === id) {
          occupant[parentLane] = null;
        }
      });
    }
    return laneOf;
  }

  function laneIndex(laneOf, records) {
    var max = 0;
    records.forEach(function (record) {
      max = Math.max(max, laneOf.get(record.id) || 0);
    });
    return max + 1;
  }

  function layout(events, options) {
    var metrics = Object.assign({}, DEFAULTS, options || {});
    var byId = new Map();
    var records = normalise(events, byId);
    var rows = orderRows(records, byId);
    rows.forEach(function (record, index) {
      record.row = index;
    });
    var laneOf = assignLanes(rows);
    records.forEach(function (record) {
      record.lane = laneOf.get(record.id) || 0;
    });
    var lanes = laneIndex(laneOf, records);

    // Row index of every card, per lane, to answer "is the column clear".
    var laneRows = new Map();
    records.forEach(function (record) {
      if (!laneRows.has(record.lane)) laneRows.set(record.lane, []);
      laneRows.get(record.lane).push(record.row);
    });
    laneRows.forEach(function (list) {
      list.sort(function (left, right) {
        return left - right;
      });
    });
    function nextBelow(lane, row) {
      var list = laneRows.get(lane) || [];
      for (var i = 0; i < list.length; i += 1) if (list[i] > row) return list[i];
      return Infinity;
    }
    function nearestAbove(lane, row) {
      var list = laneRows.get(lane) || [];
      var best = -Infinity;
      for (var i = 0; i < list.length; i += 1) if (list[i] < row) best = list[i];
      return best;
    }

    // Choose the gap: the earliest one the source column can reach and the
    // parent column can still descend from. If none exists the line needs a
    // column outside the lanes.
    var channels = new Map();
    var rings = [];
    var edges = [];
    var skipped = [];
    records.forEach(function (record) {
      record.parents.forEach(function (parentId) {
        var parent = byId.get(parentId);
        if (!parent || parent.row <= record.row) {
          skipped.push({ child: record.id, parent: parentId, reason: "parent is not below the child" });
          return;
        }
        var edge = {
          child: record.id,
          parent: parentId,
          lane: record.lane,
          childRow: record.row,
          parentRow: parent.row,
          gap: -1,
          slot: 0,
          ring: -1,
        };
        edges.push(edge);
        if (record.lane === parent.lane) {
          var blocked = (laneRows.get(record.lane) || []).some(function (row) {
            return row > record.row && row < parent.row;
          });
          if (blocked) {
            edge.ring = rings.length;
            rings.push(edge);
          }
          return;
        }
        var earliest = Math.max(record.row, nearestAbove(parent.lane, parent.row));
        var latest = Math.min(parent.row - 1, nextBelow(record.lane, record.row) - 1);
        if (earliest <= latest) {
          edge.gap = earliest;
          if (!channels.has(earliest)) channels.set(earliest, []);
          channels.get(earliest).push(edge);
        } else {
          edge.ring = rings.length;
          rings.push(edge);
        }
      });
    });
    channels.forEach(function (list) {
      list.sort(function (left, right) {
        return left.lane - right.lane || (left.child < right.child ? -1 : 1);
      });
      list.forEach(function (edge, index) {
        edge.slot = index;
      });
    });

    var cardHeights = metrics.cardHeights || {};
    function heightOf(record) {
      var value = cardHeights[record.id];
      return typeof value === "number" && value > 0 ? value : metrics.cardHeight;
    }
    var rowTops = [];
    var cursor = metrics.padding;
    rows.forEach(function (record, index) {
      rowTops.push(cursor);
      cursor += heightOf(record);
      if (index < rows.length - 1) {
        cursor += metrics.rowGap + 2 * TURN_RADIUS * (channels.get(index) || []).length;
      }
    });
    // Lanes may be pitched closer than a card is wide, so the right edge is set
    // by the last card, not by the lane count.
    var rightEdge = metrics.padding + (lanes - 1) * metrics.laneWidth + metrics.cardWidth;
    var width = Math.max(metrics.padding * 2 + lanes * metrics.laneWidth, rightEdge + metrics.padding);
    var ringBase = rightEdge + RING_GAP;
    if (rings.length) {
      width = Math.max(width, ringBase + rings.length * RING_PITCH + metrics.padding);
    }

    function cardAt(id) {
      var record = byId.get(id);
      return {
        record: record,
        x: metrics.padding + record.lane * metrics.laneWidth,
        y: rowTops[record.row],
        height: heightOf(record),
      };
    }
    function turnY(gap, slot) {
      return rowTops[gap] + heightOf(rows[gap]) + metrics.rowGap / 2 + TURN_RADIUS + slot * LINE_PITCH;
    }
    function elbow(fx, fy, tx, ty, turn) {
      if (Math.abs(tx - fx) < 0.5) return "M " + round(fx) + " " + round(fy) + " V " + round(ty);
      var radius = Math.max(0, Math.min(TURN_RADIUS, Math.abs(tx - fx) / 2, (turn - fy) / 2, (ty - turn) / 2));
      var dir = tx > fx ? 1 : -1;
      return (
        "M " + round(fx) + " " + round(fy) +
        " V " + round(turn - radius) +
        " Q " + round(fx) + " " + round(turn) + " " + round(fx + dir * radius) + " " + round(turn) +
        " H " + round(tx - dir * radius) +
        " Q " + round(tx) + " " + round(turn) + " " + round(tx) + " " + round(turn + radius) +
        " V " + round(ty)
      );
    }
    function ringPath(fx, fy, tx, ty, outY, inY, channelX) {
      var out = Math.max(1, Math.min(TURN_RADIUS, Math.abs(channelX - fx) / 2, Math.abs(outY - fy) / 2));
      var back = Math.max(1, Math.min(TURN_RADIUS, Math.abs(channelX - tx) / 2, Math.abs(inY - ty) / 2));
      var toRight = channelX > fx ? 1 : -1;
      var toTarget = tx > channelX ? 1 : -1;
      return (
        "M " + round(fx) + " " + round(fy) +
        " V " + round(outY - out) +
        " Q " + round(fx) + " " + round(outY) + " " + round(fx + toRight * out) + " " + round(outY) +
        " H " + round(channelX - toRight * out) +
        " Q " + round(channelX) + " " + round(outY) + " " + round(channelX) + " " + round(outY + out) +
        " V " + round(inY - back) +
        " Q " + round(channelX) + " " + round(inY) + " " + round(channelX + toTarget * back) + " " + round(inY) +
        " H " + round(tx - toTarget * back) +
        " Q " + round(tx) + " " + round(inY) + " " + round(tx) + " " + round(inY + back) +
        " V " + round(ty)
      );
    }

    edges.forEach(function (edge) {
      var child = cardAt(edge.child);
      var parent = cardAt(edge.parent);
      // One anchor per side: every line leaves and enters at the card centre.
      var fx = child.x + metrics.cardWidth / 2;
      var tx = parent.x + metrics.cardWidth / 2;
      var fy = child.y + child.height;
      var ty = parent.y;
      if (edge.gap >= 0) {
        edge.d = elbow(fx, fy, tx, ty, turnY(edge.gap, edge.slot));
        return;
      }
      if (edge.ring >= 0) {
        var channelX = ringBase + RING_GAP + edge.ring * RING_PITCH;
        var outY = fy + Math.min(10, metrics.rowGap / 2);
        var inY = ty - Math.min(10, metrics.rowGap / 2);
        edge.d = ringPath(fx, fy, tx, ty, outY, inY, channelX);
        return;
      }
      // Same lane, column clear: both ends share the anchor, so this is one rail.
      edge.d = "M " + round(fx) + " " + round(fy) + " V " + round(ty);
    });

    var cards = records.map(function (record) {
      return {
        id: record.id,
        lane: record.lane,
        row: record.row,
        x: metrics.padding + record.lane * metrics.laneWidth,
        y: rowTops[record.row],
        width: metrics.cardWidth,
        height: heightOf(record),
        event: record.source,
        record: record,
      };
    });

    var gaps = [];
    for (var index = 0; index < rows.length - 1; index += 1) {
      var lines = channels.get(index) || [];
      gaps.push({
        index: index,
        top: rowTops[index] + heightOf(rows[index]),
        bottom: rowTops[index + 1],
        lines: lines.length,
        turns: lines.map(function (edge) {
          return turnY(index, edge.slot);
        }),
      });
    }

    return {
      metrics: metrics,
      width: width,
      height: cursor + metrics.padding,
      cards: cards,
      edges: edges,
      gaps: gaps,
      rows: rows.map(function (record, index) {
        return { index: index, top: rowTops[index], bottom: rowTops[index] + heightOf(record) };
      }),
      lanes: lanes,
      summary: {
        events: records.length,
        heads: records.filter(function (record) {
          return record.children.length === 0;
        }).length,
        forks: records.filter(function (record) {
          return record.children.length > 1;
        }).length,
        merges: records.filter(function (record) {
          return record.parents.length > 1;
        }).length,
      },
      skipped: skipped,
    };
  }

  global.KGIterationGraph = {
    TURN_RADIUS: TURN_RADIUS,
    LINE_PITCH: LINE_PITCH,
    DEFAULTS: DEFAULTS,
    layout: layout,
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
