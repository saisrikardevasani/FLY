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
import type { FlowNode, Graph } from "@/lib/types";

const nodeTypes = { decision: DecisionNode, outcome: OutcomeNode };

let counter = 100;
const nextId = (prefix: string) => `${prefix}${counter++}`;

export function FlowCanvas({
  onGraphChange,
}: {
  onGraphChange?: (graph: Graph) => void;
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
        data: { ...n.data, onPromptChange: setPrompt, onLabelChange: setLabel },
      })) as FlowNode[],
    [nodes, setPrompt, setLabel],
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
        edges={edges}
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
