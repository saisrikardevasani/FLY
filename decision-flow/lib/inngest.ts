import { Inngest } from "inngest";

// is_production is inferred; with the Dev Server running locally this client
// talks to http://localhost:8288 without any key.
export const inngest = new Inngest({ id: "decision-flow" });
