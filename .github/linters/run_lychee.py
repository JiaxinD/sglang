#!/usr/bin/env python3
"""Cross-platform pre-commit wrapper for lychee.

This avoids depending on shell-specific launchers (e.g. /bin/bash) on Windows.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

LYCHEE_VERSION = "v0.22.0"
RELEASE_BASE = (
    "https://github.com/lycheeverse/lychee/releases/download/"
    f"lychee-{LYCHEE_VERSION}"
)


def _asset_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        if machine in {"amd64", "x86_64"}:
            return "lychee-x86_64-windows.exe"
        raise RuntimeError(f"Unsupported Windows architecture: {machine}")

    if system == "linux":
        if machine in {"x86_64", "amd64"}:
            return "lychee-x86_64-unknown-linux-gnu.tar.gz"
        if machine in {"aarch64", "arm64"}:
            return "lychee-aarch64-unknown-linux-gnu.tar.gz"
        raise RuntimeError(f"Unsupported Linux architecture: {machine}")

    if system == "darwin":
        if machine in {"x86_64", "amd64"}:
            return "lychee-x86_64-macos.tar.gz"
        if machine in {"arm64", "aarch64"}:
            return "lychee-arm64-macos.tar.gz"
        raise RuntimeError(f"Unsupported macOS architecture: {machine}")

    raise RuntimeError(f"Unsupported OS: {system}")


def _cache_dir() -> Path:
    return Path(".git") / "tools" / "lychee" / LYCHEE_VERSION


def _download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, target.open("wb") as f:
        shutil.copyfileobj(response, f)


def _extract_archive(archive_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(output_dir)
    else:
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(output_dir)

    candidate = output_dir / "lychee"
    if os.name == "nt":
        candidate = output_dir / "lychee.exe"

    if not candidate.exists():
        # Fallback: find first matching binary name after extraction.
        matches = list(output_dir.rglob("lychee*"))
        if not matches:
            raise RuntimeError(f"Cannot find lychee binary in {output_dir}")
        candidate = matches[0]

    if os.name != "nt":
        candidate.chmod(candidate.stat().st_mode | 0o111)
    return candidate


def ensure_lychee() -> str:
    env_bin = os.environ.get("LYCHEE_BIN")
    if env_bin and Path(env_bin).exists():
        return env_bin

    system_bin = shutil.which("lychee")
    if system_bin:
        return system_bin

    asset = _asset_name()
    cache = _cache_dir()
    binary_name = "lychee.exe" if os.name == "nt" else "lychee"
    cached_binary = cache / binary_name
    if cached_binary.exists():
        return str(cached_binary)

    url = f"{RELEASE_BASE}/{asset}"
    downloaded = cache / asset
    print(f"[lychee-wrapper] Downloading {url}", file=sys.stderr)
    _download_file(url, downloaded)

    if asset.endswith(".exe"):
        downloaded.replace(cached_binary)
        return str(cached_binary)

    return str(_extract_archive(downloaded, cache))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run lychee in pre-commit.")
    parser.add_argument("--config", required=True, help="Path to lychee config.")
    parser.add_argument("files", nargs="*", help="Files passed by pre-commit.")
    args = parser.parse_args()

    if not args.files:
        # Keep behavior deterministic when no files matched.
        print("[lychee-wrapper] No files matched; skipping.", file=sys.stderr)
        return 0

    try:
        lychee_bin = ensure_lychee()
    except Exception as exc:  # pragma: no cover
        print(f"[lychee-wrapper] Failed to prepare lychee: {exc}", file=sys.stderr)
        return 1

    cmd = [lychee_bin, "--config", args.config, *args.files]
    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
