"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { FlowCanvas } from "@/components/FlowCanvas";
import { RunPanel } from "@/components/RunPanel";
import type { Graph, RunState } from "@/lib/types";

const EXAMPLE =
  "Everything is down, we are getting 500s on every request and cannot log in. " +
  "Production is completely blocked right now.";

export default function Home() {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [input, setInput] = useState(EXAMPLE);
  const [run, setRun] = useState<RunState | null>(null);
  const [history, setHistory] = useState<RunState[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const polling = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (polling.current) clearInterval(polling.current);
    polling.current = null;
  };

  useEffect(() => stopPolling, []);

  const onRun = useCallback(async () => {
    if (!graph) return;
    setBusy(true);
    setError(null);
    stopPolling();

    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ graph, input }),
      });
      const started = await response.json();
      if (!response.ok) {
        setError(started.error ?? "could not start the run");
        setBusy(false);
        return;
      }

      // Poll until the run stops being "running". Same shape as the background-job
      // assignment: the request returns immediately and the answer arrives later.
      polling.current = setInterval(async () => {
        const latest = await fetch(`/api/runs/${started.id}`);
        if (!latest.ok) return;
        const state: RunState = await latest.json();
        setRun(state);
        if (state.status !== "running") {
          stopPolling();
          setBusy(false);
          setHistory((past) => [state, ...past.filter((p) => p.id !== state.id)].slice(0, 12));
        }
      }, 700);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }, [graph, input]);

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

      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1">
          <FlowCanvas onGraphChange={setGraph} run={run} />
        </div>
        <RunPanel
          input={input}
          setInput={setInput}
          run={run}
          history={history}
          busy={busy}
          error={error}
          onRun={onRun}
          onSelectRun={setRun}
        />
      </div>
    </main>
  );
}
