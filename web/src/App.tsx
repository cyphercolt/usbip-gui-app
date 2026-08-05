import { useCallback, useEffect, useRef, useState } from "react";
import { getAuthStatus, getFleet, getSecurity, watchChanges } from "./api";
import FleetView from "./FleetView";
import { useFullscreen } from "./helpers";
import LoginScreen from "./LoginScreen";
import MachineView from "./MachineView";
import SecurityPanel from "./SecurityPanel";
import UpdatesPanel from "./UpdatesPanel";
import type { AuthStatus, NodeState, SecurityState } from "./types";

interface Toast {
  id: number;
  msg: string;
  ok: boolean;
}

export default function App() {
  const [fleet, setFleet] = useState<NodeState[]>([]);
  const [security, setSecurity] = useState<SecurityState | null>(null);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [showSecurity, setShowSecurity] = useState(false);
  const [showUpdates, setShowUpdates] = useState(false);
  const [live, setLive] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [isFs, toggleFs] = useFullscreen();
  const toastId = useRef(0);
  const prevPending = useRef(0);
  const prevReach = useRef<Map<string, { name: string; reachable: boolean }> | null>(null);

  const notify = useCallback((msg: string, ok: boolean) => {
    const id = ++toastId.current;
    setToasts((t) => [...t, { id, msg, ok }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), ok ? 4000 : 12000);
  }, []);

  const copyToast = useCallback((text: string) => {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).catch(() => {});
      return;
    }
    // Fallback for non-secure origins or browsers without navigator.clipboard.
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch {}
    document.body.removeChild(ta);
  }, []);

  const refresh = useCallback(() => {
    getAuthStatus()
      .then(setAuth)
      .catch(() => {});
    getFleet()
      .then((f) => {
        setFleet(f);
        // machine online/offline notifications (skip the very first load)
        const cur = new Map(f.map((n) => [n.info.node_id, { name: n.info.display_name, reachable: n.info.reachable }]));
        const prev = prevReach.current;
        if (prev) {
          for (const [id, { name, reachable }] of cur) {
            const was = prev.get(id);
            if (was && was.reachable && !reachable) notify(`${name} went offline`, false);
            else if (was && !was.reachable && reachable) notify(`${name} came online`, true);
          }
        }
        prevReach.current = cur;
      })
      .catch(() => {});
    getSecurity()
      .then((s) => {
        setSecurity(s);
        if (s.pending.length > prevPending.current) {
          const newest = s.pending[s.pending.length - 1];
          notify(`${newest?.name ?? "A machine"} wants to pair`, true);
        }
        prevPending.current = s.pending.length;
      })
      .catch(() => {});
  }, [notify]);

  useEffect(() => {
    refresh();
    const poll = setInterval(refresh, 3000);
    const stop = watchChanges(refresh, setLive);
    return () => {
      clearInterval(poll);
      stop();
    };
  }, [refresh]);

  // Hash routing: #/m/<id> machine view, #/settings, #/updates, else fleet. Enables deep links + Android back.
  useEffect(() => {
    const apply = () => {
      const h = location.hash;
      if (h.startsWith("#/m/")) {
        setSelected(decodeURIComponent(h.slice(4)));
        setShowSecurity(false);
        setShowUpdates(false);
      } else if (h === "#/settings") {
        setShowSecurity(true);
        setShowUpdates(false);
        setSelected(null);
      } else if (h === "#/updates") {
        setShowUpdates(true);
        setShowSecurity(false);
        setSelected(null);
      } else {
        setSelected(null);
        setShowSecurity(false);
        setShowUpdates(false);
      }
    };
    apply();
    window.addEventListener("hashchange", apply);
    return () => window.removeEventListener("hashchange", apply);
  }, []);

  const selectedNode = selected ? fleet.find((n) => n.info.node_id === selected) : undefined;
  const pending = security?.pending.length ?? 0;
  const updateCount = fleet.filter(
    (n) => n.update?.update_available && n.update?.can_update && !n.update?.update_running && n.info.reachable,
  ).length;

  if (auth?.enabled && !auth.authed) {
    return <LoginScreen status={auth} onLoggedIn={refresh} />;
  }

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
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              location.hash = showUpdates ? "#/" : "#/updates";
            }}
            className="relative rounded-xl bg-white/10 hover:bg-white/15 active:scale-95 transition px-3 py-2 text-sm font-medium ring-1 ring-white/10"
            title="Updates"
          >
            🔄
            {updateCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 h-5 min-w-5 px-1 rounded-full bg-emerald-500 text-[11px] font-bold grid place-items-center">
                {updateCount}
              </span>
            )}
          </button>
          <button
            onClick={() => {
              location.hash = showSecurity ? "#/" : "#/settings";
            }}
            className="relative rounded-xl bg-white/10 hover:bg-white/15 active:scale-95 transition px-3 py-2 text-sm font-medium ring-1 ring-white/10"
            title="Settings"
          >
            ⚙️
            {pending > 0 && (
              <span className="absolute -top-1.5 -right-1.5 h-5 min-w-5 px-1 rounded-full bg-amber-500 text-[11px] font-bold grid place-items-center">
                {pending}
              </span>
            )}
          </button>
          <button
            onClick={toggleFs}
            className="rounded-xl bg-white/10 hover:bg-white/15 active:scale-95 transition px-4 py-2 text-sm font-medium ring-1 ring-white/10"
          >
            {isFs ? "Exit" : "⛶"}
          </button>
        </div>
      </header>

      {showUpdates ? (
        <UpdatesPanel
          fleet={fleet}
          notify={notify}
          onChanged={refresh}
          onBack={() => {
            location.hash = "#/";
          }}
        />
      ) : showSecurity && security ? (
        <SecurityPanel
          security={security}
          auth={auth}
          notify={notify}
          onChanged={refresh}
          onBack={() => {
            location.hash = "#/";
          }}
        />
      ) : selectedNode ? (
        <MachineView
          node={selectedNode}
          fleet={fleet}
          notify={notify}
          onChanged={refresh}
          onBack={() => {
            location.hash = "#/";
          }}
        />
      ) : fleet.length === 0 ? (
        <div className="mt-16 text-center text-white/40">Looking for machines…</div>
      ) : (
        <FleetView
          fleet={fleet}
          onOpen={(id) => {
            location.hash = "#/m/" + id;
          }}
          notify={notify}
          onChanged={refresh}
        />
      )}

      {/* toasts */}
      <div className="fixed inset-x-0 bottom-4 flex flex-col items-center gap-2 px-4 z-50">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`max-w-lg w-full rounded-xl px-4 py-2.5 text-sm shadow-lg ring-1 flex items-start gap-2 ${
              t.ok
                ? "bg-emerald-500/15 ring-emerald-400/30 text-emerald-100"
                : "bg-rose-500/15 ring-rose-400/30 text-rose-100"
            }`}
          >
            <span className="flex-1 break-words">{t.msg}</span>
            <button
              onClick={() => copyToast(t.msg)}
              className="shrink-0 rounded-md bg-white/10 hover:bg-white/20 px-2 py-1 text-[11px]"
              title="Copy"
            >
              Copy
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
