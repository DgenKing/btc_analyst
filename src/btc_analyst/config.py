from __future__ import annotations

import os
from pathlib import Path

import yaml


def _load_env_file(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE) without external deps."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = val


def load_config(path=None):
    root = Path(__file__).resolve().parents[2]
    cfg_path = Path(path) if path else root / "config" / "default.yaml"
    # Load secrets file early so env-backed clients (e.g. CoinGlass) just work.
    _load_env_file(root / "config" / "secrets.env")
    return yaml.safe_load(cfg_path.read_text())
