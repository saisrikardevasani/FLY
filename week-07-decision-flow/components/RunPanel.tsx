"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import type { RunState } from "@/lib/types";

const STATUS: Record<RunState["status"], string> = {
  running: "bg-blue-100 text-blue-700",
  done: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
};

export function RunPanel({
  input,
  setInput,
  run,
  history,
  busy,
  error,
  onRun,
  onSelectRun,
}: {
  input: string;
  setInput: (value: string) => void;
  run: RunState | null;
  history: RunState[];
  busy: boolean;
  error: string | null;
  onRun: () => void;
  onSelectRun: (run: RunState) => void;
}) {
  return (
    <aside className="flex h-full w-96 flex-col border-l bg-white">
      <div className="space-y-3 p-4">
        <div>
          <h2 className="text-sm font-semibold">Run the workflow</h2>
          <p className="text-xs text-slate-500">
            The text below is what every decision node is asked about.
          </p>
        </div>

        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Paste a customer message"
          className="min-h-28 text-sm"
        />

        <Button onClick={onRun} disabled={busy} className="w-full">
          {busy ? "Running..." : "Run"}
        </Button>

        {error ? (
          <p className="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
            {error}
          </p>
        ) : null}
      </div>

      <Separator />

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Execution log
          </h3>
          {run ? (
            <Badge className={`${STATUS[run.status]} border-0 text-[10px]`}>{run.status}</Badge>
          ) : null}
        </div>

        {!run ? (
          <p className="text-xs text-slate-400">No run yet.</p>
        ) : (
          <ol className="space-y-2">
            {run.steps.map((step) => (
              <li key={`${step.order}-${step.nodeId}`} className="rounded border p-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    {step.order}. {step.label}
                  </span>
                  {step.answer ? (
                    <span
                      className={
                        step.answer === "yes"
                          ? "font-semibold text-emerald-600"
                          : "font-semibold text-amber-600"
                      }
                    >
                      {step.answer.toUpperCase()}
                    </span>
                  ) : step.type === "outcome" ? (
                    <span className="font-semibold text-emerald-600">REACHED</span>
                  ) : null}
                </div>
                {step.prompt ? (
                  <p className="mt-1 text-slate-500">{step.prompt}</p>
                ) : null}
                {step.error ? <p className="mt-1 text-red-600">{step.error}</p> : null}
                {step.ms ? <p className="mt-1 text-slate-400">{step.ms}ms</p> : null}
              </li>
            ))}
          </ol>
        )}

        {run?.error ? (
          <p className="mt-3 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
            {run.error}
          </p>
        ) : null}

        {run?.outcome ? (
          <p className="mt-3 rounded border border-emerald-200 bg-emerald-50 p-2 text-xs text-emerald-800">
            Outcome: <span className="font-semibold">{run.outcome}</span>
          </p>
        ) : null}
      </div>

      {history.length > 0 ? (
        <>
          <Separator />
          <div className="max-h-48 overflow-y-auto p-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              History
            </h3>
            <ul className="space-y-1">
              {history.map((past) => (
                <li key={past.id}>
                  <button
                    onClick={() => onSelectRun(past)}
                    className={`w-full rounded px-2 py-1 text-left text-xs hover:bg-slate-100 ${
                      past.id === run?.id ? "bg-slate-100" : ""
                    }`}
                  >
                    <span className="font-mono text-slate-400">{past.id}</span>{" "}
                    <span className="text-slate-700">
                      {past.outcome ?? past.error ?? past.status}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </>
      ) : null}
    </aside>
  );
}
