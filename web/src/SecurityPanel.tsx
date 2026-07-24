import { useState } from "react";
import { pairAccept, pairReject, setSecurityMode, unpair } from "./api";
import { loadThemeId, saveTheme, THEMES } from "./themes";
import type { SecurityState } from "./types";

type Notify = (msg: string, ok: boolean) => void;

function Appearance() {
  const [theme, setThemeId] = useState(loadThemeId());
  return (
    <section className="rounded-2xl bg-white/5 ring-1 ring-white/10 p-4 mb-4">
      <h3 className="text-sm font-semibold text-white/70 mb-3">Appearance</h3>
      <div className="flex flex-wrap gap-2">
        {THEMES.map((t) => (
          <button
            key={t.id}
            onClick={() => {
              saveTheme(t.id);
              setThemeId(t.id);
            }}
            className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm ring-1 transition ${
              theme === t.id ? "ring-white/50 bg-white/10" : "ring-white/10 hover:bg-white/5"
            }`}
          >
            <span
              className="h-4 w-4 rounded-full ring-1 ring-white/20"
              style={{ background: t.swatch, boxShadow: `inset 0 0 0 2px ${t.accent}` }}
            />
            {t.name}
          </button>
        ))}
      </div>
    </section>
  );
}

export default function SecurityPanel({
  security,
  notify,
  onChanged,
  onBack,
}: {
  security: SecurityState;
  notify: Notify;
  onChanged: () => void;
  onBack: () => void;
}) {
  const locked = security.mode === "locked";

  const run = async (fn: () => Promise<{ ok: boolean; message: string }>) => {
    const res = await fn();
    notify(res.message || (res.ok ? "done" : "failed"), res.ok);
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
        <h2 className="text-lg font-semibold">Settings</h2>
      </div>

      <Appearance />

      {/* mode */}
      <section className="rounded-2xl bg-white/5 ring-1 ring-white/10 p-4 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium">{locked ? "🔒 Locked" : "🔓 Open"}</div>
            <p className="text-xs text-white/50 mt-1 max-w-md">
              {locked
                ? "Machines must be paired before they can see devices or be controlled."
                : "Any machine on the LAN is trusted. Lock this to require pairing (do it on every machine)."}
            </p>
          </div>
          <button
            onClick={() => run(() => setSecurityMode(locked ? "open" : "locked"))}
            className={`rounded-xl px-4 py-2 text-sm font-medium ring-1 ${
              locked
                ? "bg-white/10 ring-white/10 hover:bg-white/15"
                : "bg-amber-500/80 ring-amber-400/30 hover:bg-amber-500"
            }`}
          >
            {locked ? "Switch to Open" : "Lock down"}
          </button>
        </div>
        <p className="text-[11px] text-white/30 mt-3">This machine: {security.this_node.name}</p>
      </section>

      {/* pending requests */}
      {security.pending.length > 0 && (
        <section className="mb-4">
          <h3 className="text-sm font-semibold text-amber-300 mb-2">
            Pending pairing requests ({security.pending.length})
          </h3>
          <ul className="space-y-2">
            {security.pending.map((p) => (
              <li
                key={p.node_id}
                className="rounded-xl bg-amber-500/10 ring-1 ring-amber-400/20 p-3 flex items-center gap-3"
              >
                <span className="flex-1 truncate text-sm">
                  <span className="font-medium">{p.name}</span> wants to pair
                </span>
                <button
                  onClick={() => run(() => pairAccept(p.node_id))}
                  className="rounded-lg bg-emerald-500/80 hover:bg-emerald-500 px-3 py-1.5 text-xs font-medium"
                >
                  Accept
                </button>
                <button
                  onClick={() => run(() => pairReject(p.node_id))}
                  className="rounded-lg bg-white/10 hover:bg-white/15 px-3 py-1.5 text-xs"
                >
                  Reject
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* trusted */}
      <section>
        <h3 className="text-sm font-semibold text-white/60 mb-2">
          Paired machines ({security.trusted.length})
        </h3>
        {security.trusted.length === 0 ? (
          <p className="text-sm text-white/30">None yet. Pair a machine from the fleet view.</p>
        ) : (
          <ul className="space-y-2">
            {security.trusted.map((t) => (
              <li
                key={t.node_id}
                className="rounded-xl bg-black/20 ring-1 ring-white/5 p-3 flex items-center gap-3"
              >
                <span className="flex-1 truncate text-sm text-white/85">✅ {t.name}</span>
                <button
                  onClick={() => run(() => unpair(t.node_id))}
                  className="rounded-lg bg-rose-500/80 hover:bg-rose-500 px-3 py-1.5 text-xs font-medium"
                >
                  Unpair
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
