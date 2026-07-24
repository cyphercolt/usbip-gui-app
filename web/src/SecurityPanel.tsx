import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";
import {
  disableAuth,
  logout,
  pairAccept,
  pairReject,
  setAuth,
  setSecurityMode,
  unpair,
} from "./api";
import { loadThemeId, saveTheme, THEMES } from "./themes";
import type { AuthStatus, SecurityState } from "./types";

type Notify = (msg: string, ok: boolean) => void;

const CREDITS: { group: string; items: { name: string; url: string; role: string }[] }[] = [
  {
    group: "USB/IP",
    items: [
      {
        name: "USB/IP",
        url: "https://docs.kernel.org/usb/usbip_protocol.html",
        role: "the USB-over-IP protocol + Linux tools (GPL-2.0)",
      },
      {
        name: "usbipd-win",
        url: "https://github.com/dorssel/usbipd-win",
        role: "sharing USB devices from Windows",
      },
      {
        name: "usbip-win2",
        url: "https://github.com/vadimgrn/usbip-win2",
        role: "attaching USB devices on Windows",
      },
    ],
  },
  {
    group: "Backend",
    items: [
      { name: "FastAPI", url: "https://fastapi.tiangolo.com", role: "web framework" },
      { name: "Uvicorn", url: "https://www.uvicorn.org", role: "ASGI server" },
      {
        name: "python-zeroconf",
        url: "https://github.com/python-zeroconf/python-zeroconf",
        role: "mDNS discovery",
      },
      { name: "HTTPX", url: "https://www.python-httpx.org", role: "node-to-node HTTP" },
      { name: "Pydantic", url: "https://pydantic.dev", role: "data models" },
    ],
  },
  {
    group: "Frontend",
    items: [
      { name: "React", url: "https://react.dev", role: "UI" },
      { name: "Vite", url: "https://vitejs.dev", role: "build tooling" },
      { name: "Tailwind CSS", url: "https://tailwindcss.com", role: "styling" },
      { name: "qrcode.react", url: "https://github.com/zpao/qrcode.react", role: "2FA QR codes" },
    ],
  },
];

function Credits() {
  const [version, setVersion] = useState("");
  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then((d) => setVersion(d.version || ""))
      .catch(() => {});
  }, []);

  return (
    <section className="rounded-2xl bg-white/5 ring-1 ring-white/10 p-4 mt-4">
      <h3 className="text-sm font-semibold text-white/70 mb-1">Credits</h3>
      <p className="text-xs text-white/40 mb-3">
        USB/IP Fleet{version ? ` v${version}` : ""} is built on these open-source projects:
      </p>
      <div className="space-y-3">
        {CREDITS.map((g) => (
          <div key={g.group}>
            <div className="text-[11px] uppercase tracking-wide text-white/35 mb-1">{g.group}</div>
            <ul className="space-y-1">
              {g.items.map((it) => (
                <li key={it.name} className="text-sm">
                  <a
                    href={it.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sky-300 hover:underline"
                  >
                    {it.name}
                  </a>
                  <span className="text-white/45"> — {it.role}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <p className="text-xs text-white/40 mt-3">
        Password hashing uses PBKDF2; 2FA is RFC-6238 TOTP (Python standard library). This app is MIT
        licensed —{" "}
        <a
          href="https://github.com/cyphercolt/usbip-gui-app"
          target="_blank"
          rel="noreferrer"
          className="text-sky-300 hover:underline"
        >
          source
        </a>
        .
      </p>
    </section>
  );
}

function AccessSection({
  auth,
  notify,
  onChanged,
}: {
  auth: AuthStatus;
  notify: Notify;
  onChanged: () => void;
}) {
  const [showForm, setShowForm] = useState(!auth.enabled);
  const [username, setUsername] = useState(auth.username || "");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState(auth.totp_enabled);
  const [secret, setSecret] = useState<{ secret: string; uri: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!username || !password) {
      notify("Enter a username and password", false);
      return;
    }
    setBusy(true);
    const res = await setAuth(username, password, totp);
    setBusy(false);
    notify(res.message || (res.ok ? "login set" : "failed"), res.ok);
    if (res.ok) {
      setPassword("");
      setShowForm(false);
      if (res.totp_secret && res.otpauth_uri) setSecret({ secret: res.totp_secret, uri: res.otpauth_uri });
      onChanged();
    }
  };

  return (
    <section className="rounded-2xl bg-white/5 ring-1 ring-white/10 p-4 mb-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white/70">Web login</h3>
          <p className="text-xs text-white/50 mt-1 max-w-md">
            {auth.enabled
              ? `On — user "${auth.username}"${auth.totp_enabled ? " · 2FA" : ""}. Shared with every paired machine.`
              : "Off — anyone on the network can open this page. Turn it on to require a login (it syncs to all paired machines)."}
          </p>
        </div>
        {auth.enabled && (
          <div className="flex gap-2">
            <button
              onClick={async () => {
                await logout();
                onChanged();
              }}
              className="rounded-lg bg-white/10 hover:bg-white/15 px-3 py-2 text-xs"
            >
              Log out
            </button>
          </div>
        )}
      </div>

      {secret && (
        <div className="mt-3 rounded-xl bg-emerald-500/10 ring-1 ring-emerald-400/20 p-3">
          <p className="text-xs text-emerald-200 mb-3">
            Scan with your authenticator app (shown once):
          </p>
          <div className="flex flex-col items-center gap-3">
            <div className="rounded-lg bg-white p-3">
              <QRCodeSVG value={secret.uri} size={172} />
            </div>
            <details className="w-full">
              <summary className="text-xs text-emerald-300 cursor-pointer">
                or enter the code manually
              </summary>
              <code className="block mt-1 text-sm break-all text-emerald-100">{secret.secret}</code>
              <a href={secret.uri} className="text-xs text-emerald-300 underline break-all">
                open in authenticator
              </a>
            </details>
          </div>
        </div>
      )}

      {showForm ? (
        <div className="mt-3 space-y-2">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
            className="w-full rounded-lg bg-black/30 px-3 py-2 text-sm ring-1 ring-white/10 outline-none focus:ring-sky-400"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="password"
            className="w-full rounded-lg bg-black/30 px-3 py-2 text-sm ring-1 ring-white/10 outline-none focus:ring-sky-400"
          />
          <label className="flex items-center gap-2 text-sm text-white/70">
            <input type="checkbox" checked={totp} onChange={(e) => setTotp(e.target.checked)} />
            Enable 2FA (authenticator app)
          </label>
          <div className="flex gap-2 pt-1">
            <button
              disabled={busy}
              onClick={save}
              className="rounded-lg bg-sky-500/80 hover:bg-sky-500 px-4 py-2 text-sm font-medium disabled:opacity-40"
            >
              {auth.enabled ? "Update login" : "Turn on login"}
            </button>
            {auth.enabled && (
              <button
                onClick={() => setShowForm(false)}
                className="rounded-lg bg-white/10 px-3 py-2 text-sm"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      ) : (
        auth.enabled && (
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => setShowForm(true)}
              className="rounded-lg bg-white/10 hover:bg-white/15 px-3 py-2 text-xs"
            >
              Change password / 2FA
            </button>
            <button
              onClick={async () => {
                await disableAuth();
                notify("login turned off", true);
                onChanged();
              }}
              className="rounded-lg bg-rose-500/70 hover:bg-rose-500 px-3 py-2 text-xs"
            >
              Turn off login
            </button>
          </div>
        )
      )}
    </section>
  );
}

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
  auth,
  notify,
  onChanged,
  onBack,
}: {
  security: SecurityState;
  auth: AuthStatus | null;
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

      {auth && <AccessSection auth={auth} notify={notify} onChanged={onChanged} />}
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

      <Credits />
    </div>
  );
}
