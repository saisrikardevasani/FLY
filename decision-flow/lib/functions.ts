import { findStart, nextNode } from "./graph";
import { inngest } from "./inngest";
import { decide } from "./llm";
import { appendStep, updateRun } from "./runs";
import type { Branch, Graph } from "./types";

/** A drawn graph can contain a cycle. Stop rather than loop until the bill arrives. */
const MAX_HOPS = 25;

export const runWorkflow = inngest.createFunction(
  { id: "run-workflow", triggers: [{ event: "flow/run.requested" }], retries: 1 },
  async ({ event, step }) => {
    const { runId, graph, input } = event.data as {
      runId: string;
      graph: Graph;
      input: string;
    };

    let current = findStart(graph);
    if (!current) {
      updateRun(runId, { status: "failed", error: "no start node: every node has an input" });
      return { runId, error: "no start node" };
    }

    let order = 0;
    const visited: string[] = [];

    while (current && order < MAX_HOPS) {
      order += 1;
      const node = current;
      visited.push(node.id);

      if (node.type === "outcome") {
        const label = (node.data as { label: string }).label;
        appendStep(runId, { order, nodeId: node.id, label, type: "outcome" });
        updateRun(runId, {
          status: "done",
          outcome: label,
          finishedAt: new Date().toISOString(),
        });
        return { runId, outcome: label, visited };
      }

      const prompt = (node.data as { prompt: string }).prompt?.trim();
      if (!prompt) {
        const error = `node ${node.id} has no prompt`;
        appendStep(runId, { order, nodeId: node.id, label: "(empty)", type: "decision", error });
        updateRun(runId, { status: "failed", error, finishedAt: new Date().toISOString() });
        return { runId, error };
      }

      // One Inngest step per node. Each is retried and memoised independently, so a
      // decision already taken is never asked again.
      const started = Date.now();
      let answer: Branch;
      try {
        answer = await step.run(`decide-${node.id}-${order}`, () => decide(prompt, input));
      } catch (error) {
        const message = (error as Error).message;
        appendStep(runId, {
          order,
          nodeId: node.id,
          label: (node.data as { label: string }).label,
          type: "decision",
          prompt,
          error: message,
        });
        updateRun(runId, {
          status: "failed",
          error: message,
          finishedAt: new Date().toISOString(),
        });
        throw error;
      }

      appendStep(runId, {
        order,
        nodeId: node.id,
        label: (node.data as { label: string }).label,
        type: "decision",
        prompt,
        answer,
        ms: Date.now() - started,
      });

      const following = nextNode(graph, node.id, answer);
      if (!following) {
        const error = `node ${node.id} has no ${answer.toUpperCase()} edge`;
        updateRun(runId, {
          status: "failed",
          error,
          finishedAt: new Date().toISOString(),
        });
        return { runId, error };
      }
      current = following;
    }

    const error = `stopped after ${MAX_HOPS} hops, the graph probably has a cycle`;
    updateRun(runId, { status: "failed", error, finishedAt: new Date().toISOString() });
    return { runId, error };
  },
);

export const functions = [runWorkflow];
