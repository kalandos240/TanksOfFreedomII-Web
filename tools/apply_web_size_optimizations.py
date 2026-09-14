#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compact_map_json() -> None:
    roots = [ROOT / "assets" / "campaigns", ROOT / "assets" / "maps"]
    compacted = 0
    skipped = 0
    before = 0
    after = 0

    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*.json"):
            raw = path.read_text(encoding="utf-8")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                skipped += 1
                print(f"Skipping non-strict JSON: {path.relative_to(ROOT)} ({exc})")
                continue

            compact = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
            before += len(raw.encode("utf-8"))
            after += len(compact.encode("utf-8"))
            if compact != raw:
                path.write_text(compact, encoding="utf-8", newline="\n")
                compacted += 1

    print(
        "Map JSON compacted: "
        f"{compacted} files, skipped {skipped}, {before} -> {after} bytes "
        f"(saved {before - after} bytes)"
    )


def main() -> int:
    # Only byte-level data compaction is allowed here. Previous revisions also
    # disabled OBJ tangents/LODs/shadow meshes and replaced/excluded the HDR
    # environment. Those operations changed the game's appearance and are
    # intentionally forbidden now: Web must retain the original visual assets.
    compact_map_json()
    print("Web size optimization pass applied without visual changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
