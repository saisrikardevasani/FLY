import type { Edge } from "@xyflow/react";

const YES = "#10b981";
const NO = "#f59e0b";

/** Colour and label an edge by which handle it left, so the graph reads at a glance. */
export function decorate(edge: Edge): Edge {
  const branch = edge.sourceHandle === "no" ? "no" : "yes";
  const colour = branch === "yes" ? YES : NO;
  return {
    ...edge,
    label: branch.toUpperCase(),
    labelStyle: { fill: colour, fontWeight: 600, fontSize: 11 },
    labelBgStyle: { fill: "#fff" },
    labelBgPadding: [4, 2] as [number, number],
    style: { stroke: colour, strokeWidth: 2 },
    animated: false,
  };
}
