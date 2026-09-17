import { NextResponse } from "next/server";

import { findStart } from "@/lib/graph";
import { inngest } from "@/lib/inngest";
import { createRun } from "@/lib/runs";
import type { Graph } from "@/lib/types";

/** Start a run. Answers immediately with an id; the work happens in Inngest. */
export async function POST(request: Request) {
  let body: { graph?: Graph; input?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "body must be JSON" }, { status: 400 });
  }

  const graph = body.graph;
  const input = (body.input ?? "").trim();

  if (!graph?.nodes?.length) {
    return NextResponse.json({ error: "graph: needs at least one node" }, { status: 400 });
  }
  if (!input) {
    return NextResponse.json({ error: "input: required" }, { status: 400 });
  }
  if (!findStart(graph)) {
    return NextResponse.json(
      { error: "graph: no start node, every node has something pointing at it" },
      { status: 400 },
    );
  }

  const runId = crypto.randomUUID().slice(0, 8);
  createRun(runId, input);
  await inngest.send({ name: "flow/run.requested", data: { runId, graph, input } });

  return NextResponse.json({ id: runId, status: "running" }, { status: 202 });
}
