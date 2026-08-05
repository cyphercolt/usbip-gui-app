import { useMemo, useState } from "react";
import { checkUpdates, startAllUpdates, startUpdate } from "./api";
import { osBadge } from "./helpers";
import type { NodeState } from "./types";

type Notify = (msg: string, ok: boolean) => void;

function shortCommit(commit: string | null | undefined) {
  return commit ? commit.slice(0, 7) : "—";
}

function formatTime(iso: string | null | undefined) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function NodeUpdateRow({
  node,
  notify,
  onChanged,
}: {
  node: NodeState;
  notify: Notify;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const update = node.update;
  const running = update?.update_running;
  const available = update?.update_available && update?.can_update;
  const disabled = busy || running || !available;

  const doUpdate = async () => {
    setBusy(true);
    try {
      const res = await startUpdate(node.info.node_id);
      notify(
        res.update_running
          ? `Update started on ${node.info.display_name}`
          : res.update_message || "Update could not start",
        res.update_running,
      );
    } catch (e) {
      notify(String(e), false);
    }
    setBusy(false);
    onChanged();
  };

  return (
    <li className="rounded-xl bg-black/20 ring-1 ring-white/5 p-3">
      <div className="flex items-center gap-3">
        <span className="text-xl">{osBadge(node.info.os_name)}</span>
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate">{node.info.display_name}</div>
          <div className="text-xs text-white/40 truncate">
            v{update?.current_version || "?"} · {shortCommit(update?.installed_commit)}
            {update?.installed_commit_time && ` · ${formatTime(update.installed_commit_time)}`}
          </div>
        </div>
        {update?.update_running ? (
          <div className="text-right">
            <div className="text-xs font-medium text-amber-300 animate-pulse capitalize">
              {update.update_stage}
            </div>
            {update.update_message && (
              <div className="text-[11px] text-white/40 truncate max-w-[140px]">{update.update_message}</div>
            )}
          </div>
        ) : update?.update_available ? (
          <div className="text-right">
            <div className="text-xs font-medium text-emerald-300">Update available</div>
            <div className="text-[11px] text-white/40">→ {shortCommit(update.remote_commit)}</div>
          </div>
        ) : (
          <div className="text-right">
            <div className="text-xs text-white/40">Up to date</div>
            {update?.last_check && <div className="text-[11px] text-white/30">checked {formatTime(update.last_check)}</div>}
          </div>
        )}
        <button
          disabled={disabled}
          onClick={doUpdate}
          className="rounded-lg bg-sky-500/80 hover:bg-sky-500 disabled:opacity-40 px-3 py-1.5 text-xs font-medium"
        >
          {running ? "Updating…" : "Update"}
        </button>
      </div>
      {!update?.can_update && (
        <p className="mt-2 text-xs text-rose-300/80">{update?.update_message || "Update not available on this node"}</p>
      )}
    </li>
  );
}

export default function UpdatesPanel({
  fleet,
  notify,
  onChanged,
  onBack,
}: {
  fleet: NodeState[];
  notify: Notify;
  onChanged: () => void;
  onBack: () => void;
}) {
  const [checking, setChecking] = useState(false);
  const [updatingAll, setUpdatingAll] = useState(false);

  const nodes = useMemo(
    () => fleet.filter((n) => n.info.reachable && n.info.paired),
    [fleet],
  );

  const anyAvailable = nodes.some((n) => n.update?.update_available && n.update?.can_update && !n.update?.update_running);
  const anyRunning = nodes.some((n) => n.update?.update_running);

  const doCheck = async () => {
    setChecking(true);
    try {
      await checkUpdates();
      notify("Checked for updates", true);
    } catch (e) {
      notify(String(e), false);
    }
    setChecking(false);
    onChanged();
  };

  const doUpdateAll = async () => {
    if (!window.confirm("Update all nodes? Any active USB devices on those nodes will briefly detach during restart.")) {
      return;
    }
    setUpdatingAll(true);
    try {
      const res = await startAllUpdates();
      notify(res.message || (res.ok ? "Updates started" : "Failed"), res.ok);
    } catch (e) {
      notify(String(e), false);
    }
    setUpdatingAll(false);
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
        <h2 className="text-lg font-semibold">Updates</h2>
      </div>

      <div className="rounded-2xl bg-white/5 ring-1 ring-white/10 p-4 mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <button
            disabled={checking}
            onClick={doCheck}
            className="rounded-lg bg-white/10 hover:bg-white/15 disabled:opacity-40 px-3 py-2 text-sm"
          >
            {checking ? "Checking…" : "Check now"}
          </button>
          <button
            disabled={updatingAll || !anyAvailable}
            onClick={doUpdateAll}
            className="rounded-lg bg-sky-500/80 hover:bg-sky-500 disabled:opacity-40 px-4 py-2 text-sm font-medium"
          >
            {updatingAll ? "Starting…" : "Update all"}
          </button>
          {anyRunning && <span className="text-xs text-amber-300 animate-pulse">Update in progress…</span>}
        </div>
        <p className="mt-2 text-xs text-white/40">
          Each node checks its configured branch every 30 minutes. Updates restart the node service.
        </p>
      </div>

      {nodes.length === 0 ? (
        <p className="text-sm text-white/30">No paired machines online.</p>
      ) : (
        <ul className="space-y-2">
          {nodes.map((n) => (
            <NodeUpdateRow key={n.info.node_id} node={n} notify={notify} onChanged={onChanged} />
          ))}
        </ul>
      )}
    </div>
  );
}
