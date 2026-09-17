"use client";

import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";

import { Input } from "@/components/ui/input";
import type { OutcomeData } from "@/lib/types";

export function OutcomeNode({ id, data, selected }: NodeProps<Node<OutcomeData, "outcome">>) {
  const reached = (data as OutcomeData & { state?: string }).state === "reached";
  const onChange = (data as OutcomeData & {
    onLabelChange?: (id: string, label: string) => void;
  }).onLabelChange;

  return (
    <div
      className={`w-56 rounded-full border-2 bg-white px-4 py-3 shadow-sm ${
        reached ? "border-emerald-500 ring-2 ring-emerald-200" : "border-slate-300"
      } ${selected ? "ring-2 ring-slate-400" : ""}`}
    >
      <Handle type="target" position={Position.Top} className="!h-3 !w-3 !bg-slate-400" />
      <Input
        value={data.label}
        onChange={(e) => onChange?.(id, e.target.value)}
        className="h-7 border-0 text-center text-sm font-medium shadow-none focus-visible:ring-0 nodrag"
      />
    </div>
  );
}
