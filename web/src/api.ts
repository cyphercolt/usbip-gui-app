// Same-origin API client. The page is served by a node, and it talks to that same node;
// that node fans out to peers server-side (Phase 2).
import type { NodeState } from "./types";

export async function getFleet(): Promise<NodeState[]> {
  const res = await fetch("/api/fleet");
  if (!res.ok) throw new Error(`fleet: ${res.status}`);
  return res.json();
}

export async function getHealth(): Promise<boolean> {
  try {
    const res = await fetch("/health");
    return res.ok;
  } catch {
    return false;
  }
}

// Live state push for the node serving this page. Returns a cleanup function.
export function connectState(onState: (s: NodeState) => void, onStatus: (up: boolean) => void): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let retry: ReturnType<typeof setTimeout> | undefined;

  const open = () => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => onStatus(true);
    ws.onmessage = (ev) => {
      try {
        onState(JSON.parse(ev.data) as NodeState);
      } catch {
        /* ignore malformed frame */
      }
    };
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
