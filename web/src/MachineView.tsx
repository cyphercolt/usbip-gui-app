import { useState } from "react";
import { orchestrateAttach, release, setAutoReconnect } from "./api";
import { osBadge } from "./helpers";
import type { NodeState } from "./types";

type Notify = (msg: string, ok: boolean) => void;

interface Sent {
  destNode: NodeState;
  port: string;
  description: string;
}

interface MoveReq {
  fromName: string;
  toName: string;
  run: () => Promise<void>;
}

// Where (if anywhere) each of this machine's devices is currently attached, derived from the whole
// fleet's attached lists (an attachment records its source host + busid). An attachment may have
// been made via any of the source's interfaces, so match against every address it answers on.
function sentIndex(node: NodeState, fleet: NodeState[]): Map<string, Sent> {
  const mine = new Set([node.info.host, ...(node.info.hosts ?? [])]);
  const map = new Map<string, Sent>();
  for (const n of fleet) {
    for (const a of n.attached) {
      if (a.remote_host && mine.has(a.remote_host) && a.busid) {
        map.set(a.busid, { destNode: n, port: a.port, description: a.description });
      }
    }
  }
  return map;
}

function DeviceRow({
  node,
  busid,
  description,
  sent,
  destinations,
  notify,
  onChanged,
  askMove,
}: {
  node: NodeState;
  busid: string;
  description: string;
  sent?: Sent;
  destinations: NodeState[];
  notify: Notify;
  onChanged: () => void;
  askMove: (req: MoveReq) => void;
}) {
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);

  const send = async (destNodeId: string) => {
    setPicking(false);
    setBusy(true);
    const res = await orchestrateAttach(node.info.node_id, busid, destNodeId);
    setBusy(false);
    notify(res.message || (res.ok ? "sent" : "failed"), res.ok);
    onChanged();
  };

  const detach = async () => {
    if (!sent) return;
    setBusy(true);
    const res = await release(sent.destNode.info.node_id, sent.port);
    setBusy(false);
    notify(res.message || (res.ok ? "detached" : "failed"), res.ok);
    onChanged();
  };

  const move = (dest: NodeState) => {
    if (!sent) return;
    setPicking(false);
    askMove({
      fromName: sent.destNode.info.display_name,
      toName: dest.info.display_name,
      run: async () => {
        setBusy(true);
        const r1 = await release(sent.destNode.info.node_id, sent.port);
        if (!r1.ok) {
          setBusy(false);
          notify(`couldn't detach: ${r1.message}`, false);
          onChanged();
          return;
        }
        const r2 = await orchestrateAttach(node.info.node_id, busid, dest.info.node_id);
        setBusy(false);
        notify(r2.message || (r2.ok ? "moved" : "failed"), r2.ok);
        onChanged();
      },
    });
  };

  const pickList = sent ? destinations.filter((d) => d.info.node_id !== sent.destNode.info.node_id) : destinations;

  return (
    <li className="rounded-xl bg-black/20 ring-1 ring-white/5 p-3">
      <div className="flex items-center gap-3">
        <code className="text-xs text-white/50 w-16 shrink-0">{busid}</code>
        <span className="flex-1 min-w-0">
          <span className="block truncate text-sm text-white/85">{description}</span>
          {sent && (
            <span className="text-xs text-emerald-300/80">→ on {sent.destNode.info.display_name}</span>
          )}
        </span>
        <button
          disabled={busy}
          onClick={() => setPicking((p) => !p)}
          className="rounded-lg bg-sky-500/80 hover:bg-sky-500 px-3 py-1.5 text-xs font-medium disabled:opacity-40"
        >
          {sent ? "Move" : "Send to…"}
        </button>
        {sent && (
          <button
            disabled={busy}
            onClick={detach}
            title="Detach (and free the device)"
            className="rounded-lg bg-rose-500/80 hover:bg-rose-500 w-8 h-8 grid place-items-center text-sm font-bold disabled:opacity-40"
          >
            ✕
          </button>
        )}
      </div>

      {picking && (
        <div className="mt-3 border-t border-white/5 pt-3">
          {pickList.length === 0 ? (
            <p className="text-xs text-white/40">No other paired machines available.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-white/40 self-center">{sent ? "Move to:" : "Attach to:"}</span>
              {pickList.map((d) => (
                <button
                  key={d.info.node_id}
                  disabled={busy}
                  onClick={() => (sent ? move(d) : send(d.info.node_id))}
                  className="rounded-lg bg-violet-500/80 hover:bg-violet-500 px-3 py-1.5 text-xs font-medium disabled:opacity-40"
                >
                  {osBadge(d.info.os_name)} {d.info.display_name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </li>
  );
}

export default function MachineView({
  node,
  fleet,
  notify,
  onChanged,
  onBack,
}: {
  node: NodeState;
  fleet: NodeState[];
  notify: Notify;
  onChanged: () => void;
  onBack: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [moveReq, setMoveReq] = useState<MoveReq | null>(null);

  const destinations = fleet.filter(
    (n) => n.info.node_id !== node.info.node_id && n.info.reachable && n.info.paired,
  );

  // Combine shareable devices with any that are currently sent (they can drop out of `usbip list -l`).
  const sent = sentIndex(node, fleet);
  const seen = new Set<string>();
  const rows: { busid: string; description: string; sent?: Sent }[] = [];
  for (const d of node.shareable) {
    rows.push({ busid: d.busid, description: d.description, sent: sent.get(d.busid) });
    seen.add(d.busid);
  }
  for (const [busid, s] of sent) {
    if (!seen.has(busid)) rows.push({ busid, description: s.description, sent: s });
  }

  const doDetach = async (port: string) => {
    setBusy(true);
    const res = await release(node.info.node_id, port);
    setBusy(false);
    notify(res.message || (res.ok ? "detached" : "failed"), res.ok);
    onChanged();
  };

  const toggleAuto = async (remoteHost: string, busid: string, description: string, on: boolean) => {
    setBusy(true);
    const res = await setAutoReconnect(node.info.node_id, remoteHost, busid, description, on);
    setBusy(false);
    notify(on ? "auto-reconnect on" : "auto-reconnect off", res.ok);
    onChanged();
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={onBack}
          className="rounded-xl bg-white/10 hover:bg-white/15 px-3 py-2 text-sm ring-1 ring-white/10"
        >
          ← Fleet
        </button>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{osBadge(node.info.os_name)}</span>
          <div>
            <div className="font-semibold leading-tight">{node.info.display_name}</div>
            <div className="text-xs text-white/40">
              {node.info.host} · {node.info.os_name}
            </div>
          </div>
        </div>
      </div>

      <section className="mb-6">
        <h2 className="text-sm font-semibold text-white/60 mb-2">Devices ({rows.length})</h2>
        {rows.length === 0 ? (
          <p className="text-sm text-white/30">No USB devices to share on this machine.</p>
        ) : (
          <ul className="space-y-2">
            {rows.map((row) => (
              <DeviceRow
                key={row.busid}
                node={node}
                busid={row.busid}
                description={row.description}
                sent={row.sent}
                destinations={destinations}
                notify={notify}
                onChanged={onChanged}
                askMove={setMoveReq}
              />
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-white/60 mb-2">
          Attached devices ({node.attached.length})
        </h2>
        {node.attached.length === 0 ? (
          <p className="text-sm text-white/30">Nothing attached here.</p>
        ) : (
          <ul className="space-y-2">
            {node.attached.map((a) => (
              <li
                key={a.port}
                className="rounded-xl bg-black/20 ring-1 ring-white/5 p-3 flex items-center gap-3"
              >
                <code className="text-xs text-white/50 w-14 shrink-0">port {a.port}</code>
                <span className="flex-1 truncate text-sm text-white/85">
                  {a.description}
                  {a.remote_host && <span className="text-white/40"> · from {a.remote_host}</span>}
                </span>
                {a.remote_host && (
                  <button
                    disabled={busy}
                    onClick={() => toggleAuto(a.remote_host!, a.busid, a.description, !a.auto)}
                    title="Auto-reconnect: re-attach this device automatically if it drops"
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium ring-1 disabled:opacity-40 ${
                      a.auto
                        ? "bg-emerald-500/80 ring-emerald-400/30 text-white"
                        : "bg-white/10 ring-white/10 text-white/60 hover:bg-white/15"
                    }`}
                  >
                    🔁 Auto {a.auto ? "on" : "off"}
                  </button>
                )}
                <button
                  disabled={busy}
                  onClick={() => doDetach(a.port)}
                  className="rounded-lg bg-rose-500/80 hover:bg-rose-500 px-3 py-1.5 text-xs font-medium disabled:opacity-40"
                >
                  Detach
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* in-app move confirmation (no browser popup) */}
      {moveReq && (
        <div className="fixed inset-0 z-20 grid place-items-center bg-black/60 px-4">
          <div className="w-full max-w-sm rounded-2xl bg-[#141a2e] ring-1 ring-white/10 p-5 shadow-2xl">
            <h3 className="font-semibold text-lg">Move device?</h3>
            <p className="text-sm text-white/60 mt-2">
              This will detach it from <span className="text-white/90">{moveReq.fromName}</span> and
              attach it to <span className="text-white/90">{moveReq.toName}</span>.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setMoveReq(null)}
                className="rounded-lg bg-white/10 hover:bg-white/15 px-4 py-2 text-sm"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const req = moveReq;
                  setMoveReq(null);
                  void req.run();
                }}
                className="rounded-lg bg-violet-500/90 hover:bg-violet-500 px-4 py-2 text-sm font-medium"
              >
                Move
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
