import type { Graph } from "./types";

/** The brief's own example, so the canvas is never empty on first load. */
export const initialGraph: Graph = {
  nodes: [
    {
      id: "d1",
      type: "decision",
      position: { x: 260, y: 0 },
      data: { label: "Support?", prompt: "Is this message a support request?" },
    },
    {
      id: "d2",
      type: "decision",
      position: { x: 20, y: 220 },
      data: { label: "Urgent?", prompt: "Is the sender reporting something broken right now?" },
    },
    {
      id: "o1",
      type: "outcome",
      position: { x: 560, y: 240 },
      data: { label: "Sales" },
    },
    {
      id: "o2",
      type: "outcome",
      position: { x: -80, y: 440 },
      data: { label: "Urgent support" },
    },
    {
      id: "o3",
      type: "outcome",
      position: { x: 200, y: 440 },
      data: { label: "Normal support" },
    },
  ],
  edges: [
    { id: "e1", source: "d1", sourceHandle: "yes", target: "d2" },
    { id: "e2", source: "d1", sourceHandle: "no", target: "o1" },
    { id: "e3", source: "d2", sourceHandle: "yes", target: "o2" },
    { id: "e4", source: "d2", sourceHandle: "no", target: "o3" },
  ],
};

export const STORAGE_KEY = "decision-flow:graph";
