import { useCallback, useEffect, useRef, useState } from "react";
import { getFleet, watchChanges } from "./api";
import FleetView from "./FleetView";
import { useFullscreen } from "./helpers";
import MachineView from "./MachineView";
import type { NodeState } from "./types";

interface Toast {
  id: number;
  msg: string;
  ok: boolean;
}

export default function App() {
  const [fleet, setFleet] = useState<NodeState[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [isFs, toggleFs] = useFullscreen();
  const toastId = useRef(0);

  const refresh = useCallback(() => {
    getFleet()
      .then(setFleet)
      .catch(() => {});
  }, []);

  const notify = useCallback((msg: string, ok: boolean) => {
    const id = ++toastId.current;
    setToasts((t) => [...t, { id, msg, ok }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  useEffect(() => {
    refresh();
    const poll = setInterval(refresh, 3000); // fleet includes peers; poll to catch their changes
    const stop = watchChanges(refresh, setLive); // instant nudge on local changes
    return () => {
      clearInterval(poll);
      stop();
    };
  }, [refresh]);

  const selectedNode = selected ? fleet.find((n) => n.info.node_id === selected) : undefined;

  return (
    <div className="mx-auto max-w-3xl px-4 pb-16 pt-[max(1rem,env(safe-area-inset-top))]">
      <header className="flex items-center justify-between py-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">USB/IP Fleet</h1>
          <p className="flex items-center gap-1.5 text-xs text-white/40">
            <span className={`h-2 w-2 rounded-full ${live ? "bg-emerald-400" : "bg-amber-400"}`} />
            {live ? "live" : "connecting…"} · {fleet.length} machine{fleet.length === 1 ? "" : "s"}
          </p>
        </div>
        <button
          onClick={toggleFs}
          className="rounded-xl bg-white/10 hover:bg-white/15 active:scale-95 transition px-4 py-2 text-sm font-medium ring-1 ring-white/10"
        >
          {isFs ? "Exit fullscreen" : "⛶ Fullscreen"}
        </button>
      </header>

      {selectedNode ? (
        <MachineView
          node={selectedNode}
          fleet={fleet}
          notify={notify}
          onChanged={refresh}
          onBack={() => setSelected(null)}
        />
      ) : fleet.length === 0 ? (
        <div className="mt-16 text-center text-white/40">Looking for machines…</div>
      ) : (
        <FleetView fleet={fleet} onOpen={setSelected} notify={notify} onChanged={refresh} />
      )}

      {/* toasts */}
      <div className="fixed inset-x-0 bottom-4 flex flex-col items-center gap-2 px-4 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`max-w-lg w-full rounded-xl px-4 py-2.5 text-sm shadow-lg ring-1 ${
              t.ok
                ? "bg-emerald-500/15 ring-emerald-400/30 text-emerald-100"
                : "bg-rose-500/15 ring-rose-400/30 text-rose-100"
            }`}
          >
            {t.msg}
          </div>
        ))}
      </div>
    </div>
  );
}
