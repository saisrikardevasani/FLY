# AI Decision Flow (FlyRank, Week 7)

A visual workflow builder where every node is an AI decision that answers YES or NO, and the
answer picks which edge the run follows next. You draw the graph in the browser with React Flow;
Inngest executes it, one step per node.

## Run it

Node 20+, and two terminals. From this `decision-flow/` folder:

```bash
# terminal 1, the app
npm install
cp .env.example .env.local
npm run dev
```

```bash
# terminal 2, the Inngest Dev Server
npx inngest-cli@latest dev -u http://localhost:3000/api/inngest
```

The canvas is at http://localhost:3000 and the Inngest dashboard at http://localhost:8288.

The decisions run on a local Ollama by default, so there is no account, key or card:

```bash
ollama serve
ollama pull gemma3:4b
```

Three environment variables point it somewhere else if you prefer, and nothing in the code
changes.

## Stack

| Piece | What it does |
| --- | --- |
| Next.js (App Router) | the app and its API routes |
| React Flow (`@xyflow/react`) | the canvas, nodes and edges |
| Inngest | runs the workflow, one step per node |
| OpenAI SDK | talks to the model, pointed at Ollama by default |
| shadcn/ui + Tailwind | the panels and controls |
