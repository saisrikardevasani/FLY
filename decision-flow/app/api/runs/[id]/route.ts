import { NextResponse } from "next/server";

import { getRun } from "@/lib/runs";

/** In Next 16 the route params arrive as a promise and have to be awaited. */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const run = getRun(id);
  if (!run) {
    return NextResponse.json({ error: `no run with id ${id}` }, { status: 404 });
  }
  return NextResponse.json(run);
}
