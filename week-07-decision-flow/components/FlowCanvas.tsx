"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  addEdge,
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { DecisionNode } from "@/components/DecisionNode";
import { OutcomeNode } from "@/components/OutcomeNode";
import { Button } from "@/components/ui/button";
import { decorate } from "@/lib/edges";
import { parseGraph, serialise } from "@/lib/graph-io";
import { initialGraph, STORAGE_KEY } from "@/lib/initial-graph";
import type { FlowNode, Graph, RunState } from "@/lib/types";

const nodeTypes = { decision: DecisionNode, outcome: OutcomeNode };

let counter = 100;
const nextId = (prefix: string) => `${prefix}${counter++}`;

export function FlowCanvas({
  onGraphChange,
  run,
}: {
  onGraphChange?: (graph: Graph) => void;
  run?: RunState | null;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>(initialGraph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(
    initialGraph.edges.map(decorate),
  );
  const [loaded, setLoaded] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  // Restore whatever was on the canvas last time. A bad or absent entry just means
  // the example graph, never a blank screen.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const graph = parseGraph(saved);
        setNodes(graph.nodes);
        setEdges(graph.edges.map(decorate));
      }
    } catch {
      // keep the example graph
    }
    setLoaded(true);
  }, [setNodes, setEdges]);

  const graph = useMemo<Graph>(() => ({ nodes, edges }), [nodes, edges]);

  useEffect(() => {
    if (!loaded) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(serialise(graph)));
    } catch {
      // a full or blocked localStorage must not break editing
    }
    onGraphChange?.(serialise(graph));
  }, [graph, loaded, onGraphChange]);

  // Which node is at which point of the run, so the canvas shows the path being taken.
  const nodeState = useMemo(() => {
    const state = new Map<string, string>();
    if (!run) return state;
    run.steps.forEach((step, index) => {
      const last = index === run.steps.length - 1;
      if (step.error) state.set(step.nodeId, "error");
      else if (step.type === "outcome") state.set(step.nodeId, "reached");
      else if (step.answer) state.set(step.nodeId, step.answer);
      if (last && run.status === "running" && !step.answer) state.set(step.nodeId, "running");
    });
    return state;
  }, [run]);

  // The edges the run actually walked down, so they can be animated.
  const takenEdges = useMemo(() => {
    const taken = new Set<string>();
    if (!run) return taken;
    for (let i = 0; i < run.steps.length - 1; i += 1) {
      const from = run.steps[i];
      const to = run.steps[i + 1];
      if (!from.answer) continue;
      const edge = edges.find(
        (e) =>
          e.source === from.nodeId &&
          (e.sourceHandle ?? "yes") === from.answer &&
          e.target === to.nodeId,
      );
      if (edge) taken.add(edge.id);
    }
    return taken;
  }, [run, edges]);

  const shownEdges = useMemo(
    () =>
      edges.map((e) =>
        takenEdges.has(e.id)
          ? { ...e, animated: true, style: { ...e.style, strokeWidth: 3.5 } }
          : run
            ? { ...e, animated: false, style: { ...e.style, opacity: 0.35 } }
            : e,
      ),
    [edges, takenEdges, run],
  );

  // Narrowing on n.type keeps the node union intact: a decision keeps its prompt,
  // an outcome never grows one.
  const setPrompt = useCallback(
    (id: string, prompt: string) =>
      setNodes((current) =>
        current.map((n) =>
          n.id === id && n.type === "decision" ? { ...n, data: { ...n.data, prompt } } : n,
        ),
      ),
    [setNodes],
  );

  const setLabel = useCallback(
    (id: string, label: string) =>
      setNodes((current) =>
        current.map((n) =>
          n.id === id ? ({ ...n, data: { ...n.data, label } } as FlowNode) : n,
        ),
      ),
    [setNodes],
  );

  // The callbacks ride along in node data, which is how React Flow gets them to a
  // custom node without a context.
  const wired = useMemo(
    () =>
      nodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          onPromptChange: setPrompt,
          onLabelChange: setLabel,
          state: nodeState.get(n.id) ?? "idle",
        },
      })) as FlowNode[],
    [nodes, setPrompt, setLabel, nodeState],
  );

  const onConnect = useCallback(
    (connection: Connection) =>
      setEdges((current) => addEdge(decorate(connection as Edge), current)),
    [setEdges],
  );

  const addDecision = () =>
    setNodes((current) => [
      ...current,
      {
        id: nextId("d"),
        type: "decision" as const,
        position: { x: 120 + Math.random() * 240, y: 80 + Math.random() * 240 },
        data: { label: "New decision", prompt: "" },
      },
    ]);

  const addOutcome = () =>
    setNodes((current) => [
      ...current,
      {
        id: nextId("o"),
        type: "outcome" as const,
        position: { x: 120 + Math.random() * 240, y: 320 + Math.random() * 200 },
        data: { label: "New outcome" },
      },
    ]);

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(serialise(graph), null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "decision-flow.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const importJson = async (file: File) => {
    try {
      const parsed = parseGraph(await file.text());
      setNodes(parsed.nodes);
      setEdges(parsed.edges.map(decorate));
    } catch (error) {
      alert(`That file is not a workflow: ${(error as Error).message}`);
    }
  };

  const reset = () => {
    setNodes(initialGraph.nodes);
    setEdges(initialGraph.edges.map(decorate));
  };

  return (
    <div className="relative h-full w-full">
      <div className="absolute left-3 top-3 z-10 flex flex-wrap gap-2">
        <Button size="sm" onClick={addDecision}>
          Add decision
        </Button>
        <Button size="sm" variant="secondary" onClick={addOutcome}>
          Add outcome
        </Button>
        <Button size="sm" variant="outline" onClick={exportJson}>
          Export
        </Button>
        <Button size="sm" variant="outline" onClick={() => fileInput.current?.click()}>
          Import
        </Button>
        <Button size="sm" variant="ghost" onClick={reset}>
          Reset
        </Button>
        <input
          ref={fileInput}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && importJson(e.target.files[0])}
        />
      </div>

      <ReactFlow
        nodes={wired}
        edges={shownEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: false }}
      >
        <Background />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}
