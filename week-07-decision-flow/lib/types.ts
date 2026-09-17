import type { Edge, Node } from "@xyflow/react";

/** A question the model answers with YES or NO. Execution continues down the matching edge. */
export type DecisionData = {
  label: string;
  prompt: string;
};

/** A leaf. Reaching one ends the run and is the answer. */
export type OutcomeData = {
  label: string;
};

export type FlowNode = Node<DecisionData, "decision"> | Node<OutcomeData, "outcome">;
export type FlowEdge = Edge;

/** Which side of a decision an edge leaves from. */
export type Branch = "yes" | "no";

export type Graph = {
  nodes: FlowNode[];
  edges: FlowEdge[];
};

/** One node's turn during a run. */
export type ExecutionStep = {
  order: number;
  nodeId: string;
  label: string;
  type: "decision" | "outcome";
  prompt?: string;
  answer?: Branch;
  error?: string;
  ms?: number;
};

export type RunState = {
  id: string;
  status: "running" | "done" | "failed";
  input: string;
  startedAt: string;
  finishedAt?: string;
  steps: ExecutionStep[];
  outcome?: string;
  error?: string;
};
