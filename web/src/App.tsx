import { useEffect, useState } from "react";
import { connectState, getFleet } from "./api";
import type { NodeState } from "./types";

function osBadge(os: string): string {
  if (os.includes("win")) return "🪟";
  if (os.includes("linux")) return "🐧";
  return "💻";
}

function useFullscreen(): [boolean, () => void] {
  const [fs, setFs] = useState(!!document.fullscreenElement);
  useEffect(() => {
    const onChange = () => setFs(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);
  const toggle = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void document.documentElement.requestFullscreen().catch(() => {});
    }
  };
  return [fs, toggle];
}

function NodeCard({ node }: { node: NodeState }) {
  return (
    <div className="rounded-2xl bg-white/5 ring-1 ring-white/10 p-4 shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">{osBadge(node.info.os_name)}</span>
          <div>
            <div className="font-semibold leading-tight">{node.info.display_name}</div>
            <div className="text-xs text-white/40">
              {node.info.os_name} · v{node.info.version}
            </div>
          </div>
        </div>
        <span
          className={`h-2.5 w-2.5 rounded-full ${node.info.reachable ? "bg-emerald-400" : "bg-white/20"}`}
        />
      </div>

      <div className="mt-3 flex gap-2 text-xs">
        <span className="rounded-full bg-sky-500/15 text-sky-300 px-2.5 py-1">
          {node.shareable.length} shareable
        </span>
        <span className="rounded-full bg-violet-500/15 text-violet-300 px-2.5 py-1">
          {node.attached.length} attached
        </span>
      </div>

      {node.shareable.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {node.shareable.map((d) => (
            <li key={d.busid} className="flex items-center gap-2 text-sm">
              <code className="text-white/50 text-xs w-16 shrink-0">{d.busid}</code>
              <span className="truncate text-white/80">{d.description}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function App() {
  const [fleet, setFleet] = useState<NodeState[]>([]);
  const [live, setLive] = useState(false);
  const [isFs, toggleFs] = useFullscreen();

  useEffect(() => {
    getFleet().then(setFleet).catch(() => {});
    // Live updates for the node serving this page; merge into the fleet list by node_id.
    const stop = connectState(
      (s) =>
        setFleet((prev) => {
          const next = prev.filter((n) => n.info.node_id !== s.info.node_id);
          return [s, ...next].sort((a, b) => a.info.display_name.localeCompare(b.info.display_name));
        }),
      setLive,
    );
    return stop;
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 pb-16 pt-[max(1rem,env(safe-area-inset-top))]">
      <header className="flex items-center justify-between py-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">USB/IP Fleet</h1>
          <p className="flex items-center gap-1.5 text-xs text-white/40">
            <span className={`h-2 w-2 rounded-full ${live ? "bg-emerald-400" : "bg-amber-400"}`} />
            {live ? "live" : "connecting…"}
          </p>
        </div>
        <button
          onClick={toggleFs}
          className="rounded-xl bg-white/10 hover:bg-white/15 active:scale-95 transition px-4 py-2 text-sm font-medium ring-1 ring-white/10"
        >
          {isFs ? "Exit fullscreen" : "⛶ Fullscreen"}
        </button>
      </header>

      {fleet.length === 0 ? (
        <div className="mt-16 text-center text-white/40">Looking for machines…</div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {fleet.map((n) => (
            <NodeCard key={n.info.node_id} node={n} />
          ))}
        </div>
      )}
    </div>
  );
}
