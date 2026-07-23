import { useState } from "react";
import { addPeer } from "./api";
import { osBadge } from "./helpers";
import type { NodeState } from "./types";

function Card({ node, onOpen }: { node: NodeState; onOpen: () => void }) {
  const reachable = node.info.reachable;
  return (
    <button
      onClick={onOpen}
      disabled={!reachable}
      className={`text-left rounded-2xl p-4 ring-1 transition active:scale-[0.99] ${
        reachable
          ? "bg-white/5 ring-white/10 hover:bg-white/10"
          : "bg-white/5 ring-white/5 opacity-50"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">{osBadge(node.info.os_name)}</span>
          <div>
            <div className="font-semibold leading-tight">{node.info.display_name}</div>
            <div className="text-xs text-white/40">{node.info.host}</div>
          </div>
        </div>
        <span className={`h-2.5 w-2.5 rounded-full ${reachable ? "bg-emerald-400" : "bg-white/20"}`} />
      </div>
      <div className="mt-3 flex gap-2 text-xs">
        <span className="rounded-full bg-sky-500/15 text-sky-300 px-2.5 py-1">
          {node.shareable.length} shareable
        </span>
        <span className="rounded-full bg-violet-500/15 text-violet-300 px-2.5 py-1">
          {node.attached.length} attached
        </span>
      </div>
    </button>
  );
}

export default function FleetView({
  fleet,
  onOpen,
  notify,
  onChanged,
}: {
  fleet: NodeState[];
  onOpen: (nodeId: string) => void;
  notify: (msg: string, ok: boolean) => void;
  onChanged: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [url, setUrl] = useState("http://");

  const submit = async () => {
    const res = await addPeer(url.trim());
    notify(res.message, res.ok);
    if (res.ok) {
      setAdding(false);
      setUrl("http://");
      onChanged();
    }
  };

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {fleet.map((n) => (
        <Card key={n.info.node_id} node={n} onOpen={() => onOpen(n.info.node_id)} />
      ))}

      {adding ? (
        <div className="rounded-2xl p-4 ring-1 ring-white/10 bg-white/5 sm:col-span-2">
          <label className="text-xs text-white/50">Machine address (its node URL)</label>
          <div className="mt-2 flex gap-2">
            <input
              autoFocus
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="http://192.168.2.50:4820"
              className="flex-1 rounded-lg bg-black/30 px-3 py-2 text-sm ring-1 ring-white/10 outline-none focus:ring-sky-400"
            />
            <button onClick={submit} className="rounded-lg bg-sky-500/80 px-4 py-2 text-sm font-medium">
              Add
            </button>
            <button onClick={() => setAdding(false)} className="rounded-lg bg-white/10 px-3 py-2 text-sm">
              ✕
            </button>
          </div>
          <p className="mt-2 text-xs text-white/30">
            Auto-discovery arrives in Phase 2 — for now, add each machine once.
          </p>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="rounded-2xl p-4 ring-1 ring-dashed ring-white/15 text-white/50 hover:text-white/80 hover:ring-white/30 transition sm:col-span-2"
        >
          + Add a machine
        </button>
      )}
    </div>
  );
}
