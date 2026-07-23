// Same-origin API client. The page is served by a node; that node acts as the hub and forwards
// per-node commands to the right peer, so the browser only ever talks to this one origin.
import type { CommandResponse, NodeState } from "./types";

async function post(path: string, body?: unknown): Promise<CommandResponse> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok && res.status !== 200) {
    return { ok: false, message: `HTTP ${res.status}` };
  }
  return res.json();
}

export async function getFleet(): Promise<NodeState[]> {
  const res = await fetch("/api/fleet");
  if (!res.ok) throw new Error(`fleet: ${res.status}`);
  return res.json();
}

export const addPeer = (url: string) => post("/api/peers", { url });

export async function removePeer(url: string): Promise<CommandResponse> {
  const res = await fetch("/api/peers", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  return res.json();
}

// "Release" = detach on the destination AND unbind on the source, so the user only thinks in
// terms of send / detach — never share/unshare.
export const release = (destNodeId: string, port: string) =>
  post("/api/detach", { dest_node_id: destNodeId, port });

export const orchestrateAttach = (sourceNodeId: string, busid: string, destNodeId: string) =>
  post("/api/attach", {
    source_node_id: sourceNodeId,
    busid,
    dest_node_id: destNodeId,
  });

// A WebSocket to the serving node; we use any message as a "something changed, refetch fleet" nudge.
export function watchChanges(onNudge: () => void, onStatus: (up: boolean) => void): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let retry: ReturnType<typeof setTimeout> | undefined;
  const open = () => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => onStatus(true);
    ws.onmessage = () => onNudge();
    ws.onclose = () => {
      onStatus(false);
      if (!closed) retry = setTimeout(open, 2000);
    };
    ws.onerror = () => ws?.close();
  };
  open();
  return () => {
    closed = true;
    if (retry) clearTimeout(retry);
    ws?.close();
  };
}
