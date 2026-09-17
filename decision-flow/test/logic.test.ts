import assert from "node:assert/strict";
import test from "node:test";

import { decorate } from "../lib/edges.ts";
import { findStart, nextNode } from "../lib/graph.ts";
import { parseGraph, serialise } from "../lib/graph-io.ts";
import { parseAnswer } from "../lib/llm.ts";
import type { Graph } from "../lib/types.ts";

const graph: Graph = {
  nodes: [
    { id: "d1", type: "decision", position: { x: 0, y: 0 }, data: { label: "A", prompt: "q" } },
    { id: "o1", type: "outcome", position: { x: 0, y: 0 }, data: { label: "Yes leaf" } },
    { id: "o2", type: "outcome", position: { x: 0, y: 0 }, data: { label: "No leaf" } },
  ],
  edges: [
    { id: "e1", source: "d1", sourceHandle: "yes", target: "o1" },
    { id: "e2", source: "d1", sourceHandle: "no", target: "o2" },
  ],
};

test("the model's answer is read strictly", () => {
  assert.equal(parseAnswer("YES"), "yes");
  assert.equal(parseAnswer("no"), "no");
  assert.equal(parseAnswer("  Yes.  "), "yes");
  assert.equal(parseAnswer("YES\n"), "yes");
});

test("anything that is not a clear yes or no is refused", () => {
  // A model that hedges must not be silently read as one branch.
  assert.throws(() => parseAnswer("Yes and no, it depends"), /did not answer YES or NO/);
  assert.throws(() => parseAnswer("Maybe"), /did not answer YES or NO/);
  assert.throws(() => parseAnswer(""), /did not answer YES or NO/);
  assert.throws(() => parseAnswer("I cannot help with that"), /did not answer YES or NO/);
});

test("a word containing yes does not count as YES", () => {
  assert.throws(() => parseAnswer("eyes"), /did not answer YES or NO/);
});

test("the start node is the one nothing points at", () => {
  assert.equal(findStart(graph)?.id, "d1");
});

test("a graph where everything is a target has no start", () => {
  const cyclic: Graph = {
    nodes: graph.nodes,
    edges: [...graph.edges, { id: "e3", source: "o1", sourceHandle: "yes", target: "d1" }],
  };
  assert.equal(findStart(cyclic), undefined);
});

test("the next node is the one on the matching branch", () => {
  assert.equal(nextNode(graph, "d1", "yes")?.id, "o1");
  assert.equal(nextNode(graph, "d1", "no")?.id, "o2");
  assert.equal(nextNode(graph, "o1", "yes"), undefined);
});

test("edges are coloured and labelled by the handle they leave", () => {
  const yes = decorate({ id: "a", source: "d1", sourceHandle: "yes", target: "o1" });
  const no = decorate({ id: "b", source: "d1", sourceHandle: "no", target: "o2" });
  assert.equal(yes.label, "YES");
  assert.equal(no.label, "NO");
  assert.notEqual(yes.style?.stroke, no.style?.stroke);
});

test("an edge with no handle defaults to the YES path", () => {
  assert.equal(decorate({ id: "c", source: "d1", target: "o1" }).label, "YES");
});

test("a serialised graph survives a round trip", () => {
  const back = parseGraph(JSON.stringify(serialise(graph)));
  assert.equal(back.nodes.length, 3);
  assert.equal(back.edges.length, 2);
  assert.equal(back.nodes[0].id, "d1");
});

test("serialising drops the callbacks the canvas attaches", () => {
  const dirty = {
    ...graph,
    nodes: graph.nodes.map((n) => ({ ...n, data: { ...n.data, onPromptChange: () => {} } })),
  } as Graph;
  const clean = serialise(dirty);
  assert.equal("onPromptChange" in clean.nodes[0].data, false);
});

test("an imported file that is not a graph is rejected", () => {
  assert.throws(() => parseGraph("null"), /not an object/);
  assert.throws(() => parseGraph("{}"), /nodes array/);
  assert.throws(() => parseGraph('{"nodes":[{"id":"x"}],"edges":[]}'), /malformed node/);
  assert.throws(
    () => parseGraph('{"nodes":[{"id":"x","type":"wat","position":{}}],"edges":[]}'),
    /unknown node type/,
  );
  assert.throws(
    () => parseGraph('{"nodes":[],"edges":[{"id":"e","source":"a"}]}'),
    /malformed edge/,
  );
});
