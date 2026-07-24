import { useState } from "react";
import { login } from "./api";
import type { AuthStatus } from "./types";

export default function LoginScreen({
  status,
  onLoggedIn,
}: {
  status: AuthStatus;
  onLoggedIn: () => void;
}) {
  const [username, setUsername] = useState(status.username || "");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    const res = await login(username, password, code);
    setBusy(false);
    if (res.ok) onLoggedIn();
    else setError("Incorrect credentials.");
  };

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-2xl bg-white/5 ring-1 ring-white/10 p-6 shadow-2xl"
      >
        <h1 className="text-2xl font-bold tracking-tight">USB/IP Fleet</h1>
        <p className="text-sm text-white/40 mb-5">Sign in to continue</p>

        <label className="text-xs text-white/50">Username</label>
        <input
          autoFocus
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="mt-1 mb-3 w-full rounded-lg bg-black/30 px-3 py-2 text-sm ring-1 ring-white/10 outline-none focus:ring-sky-400"
        />

        <label className="text-xs text-white/50">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 mb-3 w-full rounded-lg bg-black/30 px-3 py-2 text-sm ring-1 ring-white/10 outline-none focus:ring-sky-400"
        />

        {status.totp_enabled && (
          <>
            <label className="text-xs text-white/50">Authenticator code</label>
            <input
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="123456"
              className="mt-1 mb-3 w-full rounded-lg bg-black/30 px-3 py-2 text-sm tracking-widest ring-1 ring-white/10 outline-none focus:ring-sky-400"
            />
          </>
        )}

        {error && <p className="text-sm text-rose-300 mb-3">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-sky-500/90 hover:bg-sky-500 active:scale-[0.99] transition px-4 py-2.5 text-sm font-semibold disabled:opacity-40"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
