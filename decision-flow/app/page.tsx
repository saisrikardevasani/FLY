"use client";

import { useState } from "react";

import { FlowCanvas } from "@/components/FlowCanvas";
import type { Graph } from "@/lib/types";

export default function Home() {
  const [graph, setGraph] = useState<Graph | null>(null);

  return (
    <main className="flex h-screen flex-col bg-slate-50">
      <header className="flex items-center justify-between border-b bg-white px-5 py-3">
        <div>
          <h1 className="text-base font-semibold">AI Decision Flow</h1>
          <p className="text-xs text-slate-500">
            Every node is a question the model answers YES or NO. The answer picks the edge.
          </p>
        </div>
        <div className="text-xs text-slate-500">
          {graph ? `${graph.nodes.length} nodes · ${graph.edges.length} edges` : ""}
        </div>
      </header>

      <div className="flex-1">
        <FlowCanvas onGraphChange={setGraph} />
      </div>
    </main>
  );
}
