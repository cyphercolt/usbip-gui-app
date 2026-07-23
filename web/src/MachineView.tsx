import { useState } from "react";
import { detach, orchestrateAttach, unshare } from "./api";
import { osBadge } from "./helpers";
import type { NodeState } from "./types";

type Notify = (msg: string, ok: boolean) => void;

function ShareableRow({
  node,
  busid,
  description,
  fleet,
  notify,
  onChanged,
}: {
  node: NodeState;
  busid: string;
  description: string;
  fleet: NodeState[];
  notify: Notify;
  onChanged: () => void;
}) {
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  const destinations = fleet.filter((n) => n.info.node_id !== node.info.node_id && n.info.reachable);

  const run = async (fn: () => Promise<{ ok: boolean; message: string }>) => {
    setBusy(true);
    const res = await fn();
    setBusy(false);
    notify(res.message || (res.ok ? "done" : "failed"), res.ok);
    onChanged();
  };

  return (
    <li className="rounded-xl bg-black/20 ring-1 ring-white/5 p-3">
      <div className="flex items-center gap-3">
        <code className="text-xs text-white/50 w-16 shrink-0">{busid}</code>
        <span className="flex-1 truncate text-sm text-white/85">{description}</span>
        <button
          disabled={busy}
          onClick={() => setPicking((p) => !p)}
          className="rounded-lg bg-sky-500/80 hover:bg-sky-500 px-3 py-1.5 text-xs font-medium disabled:opacity-40"
        >
          Send to…
        </button>
        <button
          disabled={busy}
          onClick={() => run(() => unshare(node.info.node_id, busid))}
          className="rounded-lg bg-white/10 hover:bg-white/15 px-2.5 py-1.5 text-xs disabled:opacity-40"
          title="Stop sharing (unbind)"
        >
          Unshare
        </button>
      </div>

      {picking && (
        <div className="mt-3 border-t border-white/5 pt-3">
          {destinations.length === 0 ? (
            <p className="text-xs text-white/40">No other machines available. Add one from the fleet view.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-white/40 self-center">Attach to:</span>
              {destinations.map((d) => (
                <button
                  key={d.info.node_id}
                  disabled={busy}
                  onClick={() => {
                    setPicking(false);
                    void run(() => orchestrateAttach(node.info.node_id, busid, d.info.node_id));
                  }}
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
  const doDetach = async (port: string) => {
    setBusy(true);
    const res = await detach(node.info.node_id, port);
    setBusy(false);
    notify(res.message || (res.ok ? "detached" : "failed"), res.ok);
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
        <h2 className="text-sm font-semibold text-white/60 mb-2">
          Shareable devices ({node.shareable.length})
        </h2>
        {node.shareable.length === 0 ? (
          <p className="text-sm text-white/30">No USB devices to share on this machine.</p>
        ) : (
          <ul className="space-y-2">
            {node.shareable.map((d) => (
              <ShareableRow
                key={d.busid}
                node={node}
                busid={d.busid}
                description={d.description}
                fleet={fleet}
                notify={notify}
                onChanged={onChanged}
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
    </div>
  );
}
