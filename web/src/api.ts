// Same-origin API client. The page is served by a node; that node acts as the hub and forwards
// per-node commands to the right peer, so the browser only ever talks to this one origin.
import type {
  AuthStatus,
  CommandResponse,
  NodeState,
  SecurityState,
  SetAuthResponse,
  UpdateLogEntry,
  UpdateState,
} from "./types";

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

// Arm/disarm auto-reconnect for a device on the node that currently holds it.
export const setAutoReconnect = (
  nodeId: string,
  remoteHost: string,
  busid: string,
  description: string,
  enabled: boolean,
) =>
  post(`/api/node/${nodeId}/autoreconnect`, {
    remote_host: remoteHost,
    busid,
    description,
    enabled,
  });

export const orchestrateAttach = (sourceNodeId: string, busid: string, destNodeId: string) =>
  post("/api/attach", {
    source_node_id: sourceNodeId,
    busid,
    dest_node_id: destNodeId,
  });

// ---- updates ----
export async function getUpdateStatus(): Promise<UpdateState> {
  const res = await fetch("/api/update/status");
  if (!res.ok) throw new Error(`update status: ${res.status}`);
  return res.json();
}

export async function checkUpdates(): Promise<UpdateState> {
  const res = await fetch("/api/update/check", { method: "POST" });
  if (!res.ok) throw new Error(`update check: ${res.status}`);
  return res.json();
}

export async function startUpdate(nodeId: string): Promise<UpdateState> {
  const res = await fetch(`/api/node/${nodeId}/update/start`, { method: "POST" });
  if (!res.ok) throw new Error(`update start: ${res.status}`);
  return res.json();
}

export async function startAllUpdates(): Promise<CommandResponse> {
  return post("/api/update/start-all", {});
}

export async function getUpdateLogs(): Promise<UpdateLogEntry[]> {
  const res = await fetch("/api/update/logs");
  if (!res.ok) throw new Error(`update logs: ${res.status}`);
  return res.json();
}

// ---- security / pairing ----
export async function getSecurity(): Promise<SecurityState> {
  const res = await fetch("/api/security");
  if (!res.ok) throw new Error(`security: ${res.status}`);
  return res.json();
}

export const setSecurityMode = (mode: "open" | "locked") =>
  post("/api/security/mode", { mode });
export const pairInitiate = (peerNodeId: string) => post(`/api/pair/initiate/${peerNodeId}`);
export const pairAccept = (nodeId: string) => post("/api/pair/accept", { node_id: nodeId });
export const pairReject = (nodeId: string) => post("/api/pair/reject", { node_id: nodeId });

export async function unpair(nodeId: string): Promise<CommandResponse> {
  const res = await fetch(`/api/pair/${nodeId}`, { method: "DELETE" });
  return res.json();
}

// ---- web login ----
export async function getAuthStatus(): Promise<AuthStatus> {
  const res = await fetch("/api/auth/status");
  return res.json();
}

export async function login(
  username: string,
  password: string,
  code?: string,
): Promise<{ ok: boolean; status: number }> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, code: code || null }),
  });
  return { ok: res.ok, status: res.status };
}

export const logout = () => post("/api/auth/logout");
export const disableAuth = () => post("/api/auth/disable");

export async function setAuth(
  username: string,
  password: string,
  totpEnabled: boolean,
): Promise<SetAuthResponse> {
  const res = await fetch("/api/auth/set", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, totp_enabled: totpEnabled }),
  });
  return res.json();
}

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
