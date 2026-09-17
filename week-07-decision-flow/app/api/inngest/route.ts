import { serve } from "inngest/next";

import { functions } from "@/lib/functions";
import { inngest } from "@/lib/inngest";

export const { GET, POST, PUT } = serve({ client: inngest, functions });
