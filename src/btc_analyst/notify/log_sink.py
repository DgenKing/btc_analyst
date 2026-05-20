from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def log_message(msg: str, file_path: str | None = None) -> bool:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    if file_path:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        prior = p.read_text() if p.exists() else ""
        p.write_text(prior + line + "\n")
    else:
        print(line)
    return True
