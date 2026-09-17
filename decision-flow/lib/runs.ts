import type { RunState } from "./types";

// Runs live in memory, and the Inngest function and the API routes share this module
// because they run in the same Next.js process. A restart forgets every run, which is
// the same trade the background-job assignment made and for the same reason.
// globalThis survives dev-mode hot reloads, which module scope does not.
const store = ((globalThis as { __runs?: Map<string, RunState> }).__runs ??= new Map());

export function createRun(id: string, input: string): RunState {
  const run: RunState = {
    id,
    status: "running",
    input,
    startedAt: new Date().toISOString(),
    steps: [],
  };
  store.set(id, run);
  return run;
}

export function getRun(id: string): RunState | undefined {
  return store.get(id);
}

/** Replace the stored run rather than editing it in place. */
export function updateRun(id: string, patch: Partial<RunState>): void {
  const current = store.get(id);
  if (!current) return;
  store.set(id, { ...current, ...patch });
}

export function appendStep(id: string, step: RunState["steps"][number]): void {
  const current = store.get(id);
  if (!current) return;
  store.set(id, { ...current, steps: [...current.steps, step] });
}
