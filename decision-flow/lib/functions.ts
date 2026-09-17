import { inngest } from "./inngest";

/** Phase 1 only: proves the app, the Dev Server and the SDK are wired together. */
export const sayHello = inngest.createFunction(
  { id: "say-hello", triggers: [{ event: "test/hello" }] },
  async ({ step }) => {
    await step.sleep("nap", "2s");
    return "Hello from the background!";
  },
);

export const functions = [sayHello];
