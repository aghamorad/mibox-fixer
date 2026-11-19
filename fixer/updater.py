"""Commit-based self-updater for MoBox (checks aghamorad/mibox-fixer main)."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

REPO_OWNER = "aghamorad"
REPO_NAME = "mibox-fixer"
REPO_BRANCH = "main"
REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class UpdateStatus:
    local_commit: str
    remote_commit: Optional[str]
    remote_message: str
    update_available: bool
    error: Optional[str] = None

    @property
    def short_local(self) -> str:
        return self.local_commit[:7] if self.local_commit else "unknown"

    @property
    def short_remote(self) -> str:
        return self.remote_commit[:7] if self.remote_commit else "unknown"


def get_local_commit(repo_root: Path = REPO_ROOT) -> str:
    env_sha = os.environ.get("MOBOX_BUILD_COMMIT", "").strip()
    if env_sha and env_sha != "unknown":
        return env_sha
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def check_for_updates(repo_root: Path = REPO_ROOT, timeout: float = 8.0) -> UpdateStatus:
    """Compare local HEAD commit against GitHub main without modifying anything."""
    local = get_local_commit(repo_root)
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{REPO_BRANCH}"
    req = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "MoBox-Updater",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        remote = str(data.get("sha", "")).strip()
        msg = str(data.get("commit", {}).get("message", "")).splitlines()[0]
        available = bool(local and remote and local != remote)
        return UpdateStatus(
            local_commit=local,
            remote_commit=remote or None,
            remote_message=msg,
            update_available=available,
        )
    except (URLError, OSError, ValueError, KeyError) as exc:
        return UpdateStatus(
            local_commit=local,
            remote_commit=None,
            remote_message="",
            update_available=False,
            error=str(exc),
        )


def apply_update(repo_root: Path = REPO_ROOT) -> tuple[bool, str]:
    """Fast-forward pull the latest commits from origin/main."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "pull", "--ff-only", "origin", REPO_BRANCH],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = (proc.stdout + "\n" + proc.stderr).strip()
        if proc.returncode == 0:
            return True, out or "Updated successfully. Restart MoBox to use the new version."
        return False, out or "Could not fast-forward update."
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
