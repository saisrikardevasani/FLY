import type { Branch, FlowNode, Graph } from "./types";

/** Pure graph traversal. No Inngest, no network, so it can be tested on its own. */

/** The entry node is the one nothing points at. */
export function findStart(graph: Graph): FlowNode | undefined {
  const targeted = new Set(graph.edges.map((e) => e.target));
  return graph.nodes.find((n) => !targeted.has(n.id));
}

/** Follow the edge leaving `fromId` on the given branch. */
export function nextNode(
  graph: Graph,
  fromId: string,
  branch: Branch,
): FlowNode | undefined {
  const edge = graph.edges.find(
    (e) => e.source === fromId && (e.sourceHandle ?? "yes") === branch,
  );
  if (!edge) return undefined;
  return graph.nodes.find((n) => n.id === edge.target);
}
