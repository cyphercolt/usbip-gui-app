"""Tests for the fleet self-update module.

Uses a temporary git repository so the suite is isolated from the real repo.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import pytest_asyncio

from usbip_node import updater as updater_mod
from usbip_node.updater import Updater, _find_repo, _parse_commit_time


@pytest_asyncio.fixture()
async def tmp_git(tmp_path, monkeypatch):
    """Create a temp git repo with two commits and an origin remote."""
    repo = tmp_path / "repo"
    repo.mkdir()
    # Initialize repo and create a file to commit.
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("v1")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "v1"], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("v2")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "v2"], cwd=repo, check=True, capture_output=True)
    # Set up a fake origin so fetch doesn't error. We'll create a bare repo and push to it.
    origin = tmp_path / "origin.git"
    origin.mkdir()
    subprocess.run(["git", "init", "--bare", "--initial-branch=main"], cwd=origin, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(origin)], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(["git", "push", "origin", "main"], cwd=repo, check=True, capture_output=True)

    # Provide a fake packaging/update.sh so the node believes it can update.
    packaging = repo / "packaging"
    packaging.mkdir()
    (packaging / "update.sh").write_text("#!/bin/bash\nexit 0\n")
    (packaging / "update.sh").chmod(0o755)

    monkeypatch.setenv("USBIP_NODE_UPDATE_CHECK_INTERVAL", "0")
    monkeypatch.setenv("USBIP_NODE_UPDATE_REPO", str(repo))
    monkeypatch.chdir(repo)
    return repo


async def test_find_repo_detects_cwd(tmp_git):
    probe = _find_repo()
    assert probe.can_update
    assert probe.path == Path(tmp_git)


async def test_update_state_no_update_when_up_to_date(tmp_git):
    updater = Updater("abc", "3.0.0")
    updater.refresh_repo()
    state = updater.state
    assert state.node_id == "abc"
    assert not state.update_available
    assert state.can_update


async def test_check_now_populates_state(tmp_git):
    updater = Updater("abc", "3.0.0")
    updater.refresh_repo()
    state = await updater.check_now()
    assert state.installed_commit
    assert state.remote_commit
    assert state.installed_commit == state.remote_commit
    assert not state.update_available
    assert state.last_check


async def test_update_available_when_remote_ahead(tmp_git):
    origin_url = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=tmp_git, check=True, capture_output=True, text=True
    ).stdout.strip()
    clone = tmp_git.parent / "origin-clone"
    subprocess.run(
        ["git", "clone", "--branch", "main", origin_url, str(clone)],
        check=True, capture_output=True,
    )
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=clone, check=True, capture_output=True)
    (clone / "file.txt").write_text("v3")
    subprocess.run(["git", "add", "."], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "v3"], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=clone, check=True, capture_output=True)

    updater = Updater("abc", "3.0.0")
    updater.refresh_repo()
    state = await updater.check_now()
    assert state.update_available
    assert state.installed_commit != state.remote_commit


async def test_start_update_sets_running(tmp_git, monkeypatch):
    updater = Updater("abc", "3.0.0")
    updater.refresh_repo()
    # Mock the actual spawn so we don't start a real update process.
    spawn_called = []

    def fake_spawn(self):
        spawn_called.append(True)

    monkeypatch.setattr(Updater, "_spawn_update_helper", fake_spawn)

    state = await updater.start_update()
    assert state.update_running
    assert state.update_stage == "fetching"
    assert spawn_called


async def test_start_update_refuses_when_no_repo(tmp_path, monkeypatch):
    no_repo = tmp_path / "no-repo"
    no_repo.mkdir()
    monkeypatch.setenv("USBIP_NODE_UPDATE_REPO", str(no_repo))
    updater = Updater("abc", "3.0.0")
    updater.refresh_repo()
    state = await updater.start_update()
    assert not state.update_running
    assert "no .git directory" in state.update_message


def test_find_repo_env_path_is_authoritative(tmp_path, monkeypatch):
    """If USBIP_NODE_UPDATE_REPO points at a valid git repo, use it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("v1")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "v1"], cwd=repo, check=True, capture_output=True)

    monkeypatch.setenv("USBIP_NODE_UPDATE_REPO", str(repo))
    probe = _find_repo()
    assert probe.can_update
    assert probe.path == repo


def test_find_repo_env_path_missing_dotgit(tmp_path, monkeypatch):
    """If USBIP_NODE_UPDATE_REPO points at a non-git directory, fail with a clear reason."""
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setenv("USBIP_NODE_UPDATE_REPO", str(plain))
    probe = _find_repo()
    assert not probe.can_update
    assert "no .git directory" in probe.reason


def test_find_repo_env_path_reports_git_error(tmp_path, monkeypatch):
    """If .git exists but git rev-parse fails, surface the actual stderr."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    # Empty .git dir makes git complain "not a git repository".
    monkeypatch.setenv("USBIP_NODE_UPDATE_REPO", str(repo))
    probe = _find_repo()
    assert not probe.can_update
    assert "not a git repository" in probe.reason or "usable git checkout" in probe.reason


def test_parse_commit_time_handles_iso():
    assert _parse_commit_time("2026-08-05T14:32:10+00:00") == "2026-08-05T14:32:10+00:00"
