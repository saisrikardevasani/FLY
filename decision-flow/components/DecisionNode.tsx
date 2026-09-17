"use client";

import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";

import { Textarea } from "@/components/ui/textarea";
import type { DecisionData } from "@/lib/types";

type Props = NodeProps<Node<DecisionData, "decision">> & {
  onPromptChange?: (id: string, prompt: string) => void;
  state?: "idle" | "running" | "yes" | "no" | "error";
};

const RING: Record<string, string> = {
  idle: "border-slate-300",
  running: "border-blue-500 ring-2 ring-blue-200",
  yes: "border-emerald-500 ring-2 ring-emerald-200",
  no: "border-amber-500 ring-2 ring-amber-200",
  error: "border-red-500 ring-2 ring-red-200",
};

export function DecisionNode({ id, data, selected }: Props) {
  const state = (data as DecisionData & { state?: string }).state ?? "idle";
  const onChange = (data as DecisionData & {
    onPromptChange?: (id: string, prompt: string) => void;
  }).onPromptChange;

  return (
    <div
      className={`w-72 rounded-lg border-2 bg-white shadow-sm ${RING[state] ?? RING.idle} ${
        selected ? "ring-2 ring-slate-400" : ""
      }`}
    >
      <Handle type="target" position={Position.Top} className="!h-3 !w-3 !bg-slate-400" />

      <div className="border-b bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
        Decision
      </div>

      <div className="p-3">
        <Textarea
          value={data.prompt}
          onChange={(e) => onChange?.(id, e.target.value)}
          placeholder="Ask something the model can answer YES or NO"
          className="min-h-20 resize-none text-sm nodrag"
        />
      </div>

      <div className="flex items-center justify-between border-t px-3 py-1.5 text-xs font-medium">
        <span className="text-emerald-600">YES</span>
        <span className="text-amber-600">NO</span>
      </div>

      <Handle
        id="yes"
        type="source"
        position={Position.Bottom}
        style={{ left: "25%" }}
        className="!h-3 !w-3 !bg-emerald-500"
      />
      <Handle
        id="no"
        type="source"
        position={Position.Bottom}
        style={{ left: "75%" }}
        className="!h-3 !w-3 !bg-amber-500"
      />
    </div>
  );
}
