import type { Graph } from "./types";

/** Strip the callbacks and run state the canvas attaches, leaving a plain graph. */
export function serialise(graph: Graph): Graph {
  return {
    nodes: graph.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data:
        n.type === "decision"
          ? { label: (n.data as { label: string }).label,
              prompt: (n.data as { prompt: string }).prompt }
          : { label: (n.data as { label: string }).label },
    })) as Graph["nodes"],
    edges: graph.edges.map((e) => ({
      id: e.id,
      source: e.source,
      sourceHandle: e.sourceHandle ?? null,
      target: e.target,
    })),
  };
}

/** Accept a graph from localStorage or an imported file, rejecting anything malformed. */
export function parseGraph(raw: string): Graph {
  const value = JSON.parse(raw) as unknown;
  if (typeof value !== "object" || value === null) throw new Error("not an object");

  const { nodes, edges } = value as Partial<Graph>;
  if (!Array.isArray(nodes) || !Array.isArray(edges)) {
    throw new Error("a graph needs a nodes array and an edges array");
  }
  for (const node of nodes as Array<{ id?: string; type?: string; position?: unknown }>) {
    if (!node.id || !node.type || !node.position) throw new Error(`malformed node: ${node.id}`);
    if (node.type !== "decision" && node.type !== "outcome") {
      throw new Error(`unknown node type: ${node.type}`);
    }
  }
  for (const edge of edges as Array<{ id?: string; source?: string; target?: string }>) {
    if (!edge.id || !edge.source || !edge.target) throw new Error(`malformed edge: ${edge.id}`);
  }
  return { nodes, edges };
}
