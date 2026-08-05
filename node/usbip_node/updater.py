"""Fleet self-update: detect when this node is behind origin, and trigger an out-of-process update.

The node never updates itself in-process. It spawns a small platform-specific helper that
survives the node's exit, pulls the configured branch, and re-runs the install script. The
service manager (systemd / Windows scheduled task) then starts the new code.
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .core.models import UpdateState

_DEFAULT_INTERVAL = 30 * 60  # 30 minutes
_UPDATE_INTERVAL = float(os.environ.get("USBIP_NODE_UPDATE_CHECK_INTERVAL", _DEFAULT_INTERVAL))
_UPDATE_BRANCH = os.environ.get("USBIP_NODE_UPDATE_BRANCH", "main")
_UPDATE_REPO = os.environ.get("USBIP_NODE_UPDATE_REPO")

_LINUX_INSTALL_DIR = Path("/opt/usbip-node")


@dataclasses.dataclass
class _RepoProbe:
    path: Path
    branch: str
    can_update: bool
    reason: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_commit(commit: str) -> str:
    return commit[:7] if commit else ""


def _run_text(argv: list[str], cwd: Path | None = None, timeout: float = 20.0) -> tuple[bool, str]:
    try:
        res = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return res.returncode == 0, (res.stdout or res.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def _update_branch() -> str:
    return os.environ.get("USBIP_NODE_UPDATE_BRANCH", "main")


def _find_repo() -> _RepoProbe:
    """Detect the git checkout the service is running from.

    Linux packaged install lives at /opt/usbip-node. Windows and dev installs are derived from
    this module's path (__file__ is inside the installed package, not the repo root, so we walk
    up looking for .git).

    USBIP_NODE_UPDATE_REPO, if set, is authoritative: it is the only candidate checked, and if
    it is not a valid git repo the node is marked unable to update.
    """
    branch = _update_branch()
    env_repo = os.environ.get("USBIP_NODE_UPDATE_REPO")
    if env_repo:
        path = Path(env_repo)
        if not (path / ".git").is_dir():
            return _RepoProbe(
                path=path,
                branch=branch,
                can_update=False,
                reason=f"USBIP_NODE_UPDATE_REPO ({env_repo}) has no .git directory",
            )
        ok, err = _run_text(["git", "rev-parse", "--git-dir"], cwd=path)
        if ok:
            return _RepoProbe(path=path, branch=branch, can_update=True)
        return _RepoProbe(
            path=path,
            branch=branch,
            can_update=False,
            reason=f"USBIP_NODE_UPDATE_REPO ({env_repo}) is not a usable git checkout: {err}",
        )

    candidates: list[Path] = []
    if platform.system() != "Windows" and _LINUX_INSTALL_DIR.is_dir():
        candidates.append(_LINUX_INSTALL_DIR)

    # Walk up from package looking for a .git directory (editable/dev install).
    here = Path(__file__).resolve().parent
    for p in (here, *here.parents):
        if (p / ".git").is_dir():
            candidates.append(p)

    for path in dict.fromkeys(candidates):
        if not (path / ".git").is_dir():
            continue
        ok, out = _run_text(["git", "rev-parse", "--git-dir"], cwd=path)
        if ok:
            return _RepoProbe(path=path, branch=branch, can_update=True)
    return _RepoProbe(
        path=Path.cwd(),
        branch=branch,
        can_update=False,
        reason="no packaged or git checkout found",
    )


def _check_writable_and_scripts(path: Path) -> tuple[bool, str]:
    if platform.system() == "Windows":
        script = path / "packaging" / "update.ps1"
    else:
        script = path / "packaging" / "update.sh"
    if not script.exists():
        return False, f"update script not found: {script}"
    try:
        test_file = path / ".update-write-test"
        test_file.write_text("")
        test_file.unlink()
    except OSError:
        return False, "repo directory is not writable"
    return True, ""


def _parse_commit_time(out: str) -> str | None:
    # git log -1 --format=%cI yields ISO8601 like 2026-08-05T14:32:10+00:00
    line = out.strip().splitlines()[0] if out else ""
    return line or None


class Updater:
    """Owns update state for this node and runs periodic git checks."""

    def __init__(self, node_id: str, version: str) -> None:
        self._node_id = node_id
        self._version = version
        self._probe = _find_repo()
        self._state = UpdateState(
            node_id=node_id,
            current_version=version,
            branch=self._probe.branch,
            can_update=self._probe.can_update,
            update_message=self._probe.reason,
        )
        self._running = False

    def refresh_repo(self) -> None:
        """Re-detect the repo (used mainly in tests after env changes)."""
        self._probe = _find_repo()
        self._state = self._state.model_copy(
            update={
                "branch": self._probe.branch,
                "can_update": self._probe.can_update,
                "update_message": self._probe.reason,
            }
        )

    @property
    def state(self) -> UpdateState:
        return self._state

    async def check_now(self) -> UpdateState:
        if not self._probe.can_update:
            self._state = self._state.model_copy(
                update={"last_check": _now_iso(), "update_message": self._probe.reason}
            )
            return self._state

        cwd = self._probe.path
        branch = self._probe.branch

        ok, err = _check_writable_and_scripts(cwd)
        if not ok:
            self._state = self._state.model_copy(
                update={"can_update": False, "update_message": err, "last_check": _now_iso()}
            )
            return self._state

        # Fetch first so remote refs are current.
        fetch_ok, fetch_out = _run_text(["git", "fetch", "origin"], cwd=cwd, timeout=30.0)
        if not fetch_ok:
            self._state = self._state.model_copy(
                update={
                    "update_stage": "error",
                    "update_message": f"git fetch failed: {fetch_out}",
                    "last_check": _now_iso(),
                }
            )
            return self._state

        installed_ok, installed = _run_text(["git", "rev-parse", "HEAD"], cwd=cwd)
        installed_time_ok, installed_time = _run_text(
            ["git", "log", "-1", "--format=%cI", "HEAD"], cwd=cwd
        )
        remote_ok, remote = _run_text(["git", "rev-parse", f"origin/{branch}"], cwd=cwd)
        remote_time_ok, remote_time = _run_text(
            ["git", "log", "-1", "--format=%cI", f"origin/{branch}"], cwd=cwd
        )

        if not (installed_ok and remote_ok):
            self._state = self._state.model_copy(
                update={
                    "update_stage": "error",
                    "update_message": "git rev-parse failed",
                    "last_check": _now_iso(),
                }
            )
            return self._state

        update_available = installed.strip() != remote.strip()

        # Find latest pre-update tag for rollback info.
        tag_ok, tags_out = _run_text(
            ["git", "tag", "--list", "pre-update-*", "--sort=-creatordate"], cwd=cwd
        )
        rollback_tag = tags_out.splitlines()[0] if tag_ok and tags_out.strip() else None

        self._state = self._state.model_copy(
            update={
                "installed_commit": installed.strip(),
                "installed_commit_time": _parse_commit_time(installed_time),
                "remote_commit": remote.strip(),
                "remote_commit_time": _parse_commit_time(remote_time),
                "update_available": update_available,
                "update_stage": "idle" if not self._running else self._state.update_stage,
                "update_message": "",
                "last_check": _now_iso(),
                "can_update": True,
                "rollback_tag": rollback_tag,
            }
        )
        return self._state

    async def run(self) -> None:
        """Background loop. Cancelled on shutdown."""
        if _UPDATE_INTERVAL <= 0:
            return
        # Run an initial check soon after startup, then every interval.
        await self.check_now()
        while True:
            try:
                await asyncio.sleep(_UPDATE_INTERVAL)
            except asyncio.CancelledError:
                raise
            await self.check_now()

    def _set_stage(self, stage: str, message: str = "") -> None:
        self._state = self._state.model_copy(
            update={"update_stage": stage, "update_message": message}
        )

    async def start_update(self) -> UpdateState:
        """Trigger the out-of-process update helper and mark state running."""
        if self._running:
            return self._state
        if not self._probe.can_update:
            self._set_stage("error", self._probe.reason or "update not available")
            return self._state

        ok, err = _check_writable_and_scripts(self._probe.path)
        if not ok:
            self._set_stage("error", err)
            return self._state

        self._running = True
        self._state = self._state.model_copy(
            update={
                "update_running": True,
                "update_stage": "fetching",
                "update_message": "Update started",
            }
        )

        if platform.system() == "Windows":
            self._trigger_windows_update()
        else:
            self._trigger_linux_update()

        return self._state

    def _trigger_linux_update(self) -> None:
        script = self._probe.path / "packaging" / "update.sh"
        log = _linux_state_path() / "update.log"
        # Write a request marker so the helper can log who requested it.
        marker = _linux_state_path() / "update-request.json"
        try:
            marker.write_text(
                f'{{"requested_at": "{_now_iso()}", "branch": "{self._probe.branch}"}}'
            )
        except OSError:
            pass

        env = {**os.environ, "USBIP_NODE_UPDATE_BRANCH": self._probe.branch}
        # Use a unique unit name so repeated clicks don't collide. Start in 1s so the
        # requesting node has time to finish its HTTP response before the service restarts.
        unit = f"usbip-node-update-{int(time.time())}"
        # Prefer systemd-run to detach from the node process. If unavailable, fall back to
        # nohup so the shell helper survives our exit.
        try:
            subprocess.Popen(
                [
                    "systemd-run",
                    "--unit", unit,
                    "--on-active=1s",
                    "--timer-property=AccuracySec=1us",
                    "--property=StandardOutput=append:" + str(log),
                    "--property=StandardError=append:" + str(log),
                    "--setenv", f"USBIP_NODE_UPDATE_BRANCH={self._probe.branch}",
                    str(script),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError:
            with log.open("a") as f:
                subprocess.Popen(
                    ["bash", "-c", f"sleep 1; exec {script}"],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=env,
                )

    def _trigger_windows_update(self) -> None:
        script = self._probe.path / "packaging" / "update.ps1"
        # Launch an elevated PowerShell that survives the node exit.
        subprocess.Popen(
            [
                "powershell",
                "-ExecutionPolicy", "Bypass",
                "-File", str(script),
            ],
            env={**os.environ, "USBIP_NODE_UPDATE_BRANCH": self._probe.branch},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )


def _linux_state_path() -> Path:
    from .config import state_dir

    return state_dir()
