#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    p = ROOT / path
    if not p.exists():
        raise FileNotFoundError(f"Required file is missing: {path}")
    return p.read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8", newline="\n")


def optimize_obj_imports() -> None:
    files = 0
    changed = 0
    for path in ROOT.rglob("*.obj.import"):
        files += 1
        text = path.read_text(encoding="utf-8")
        new = text
        # Portal profile disables real-time shadows, so generated shadow meshes
        # are dead weight. MagicaVoxel OBJ materials use diffuse palettes only,
        # so tangents are not needed for normal/height mapping either.
        new = new.replace("generate_tangents=true", "generate_tangents=false")
        new = new.replace("generate_lods=true", "generate_lods=false")
        new = new.replace("generate_shadow_mesh=true", "generate_shadow_mesh=false")
        if new != text:
            path.write_text(new, encoding="utf-8", newline="\n")
            changed += 1

    if files == 0:
        raise RuntimeError("No OBJ import metadata found")
    print(f"OBJ imports optimized: {changed}/{files}")


def compact_map_json() -> None:
    roots = [ROOT / "assets" / "campaigns", ROOT / "assets" / "maps"]
    compacted = 0
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
                raise RuntimeError(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
            compact = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
            before += len(raw.encode("utf-8"))
            after += len(compact.encode("utf-8"))
            if compact != raw:
                path.write_text(compact, encoding="utf-8", newline="\n")
                compacted += 1

    print(
        "Map JSON compacted: "
        f"{compacted} files, {before} -> {after} bytes "
        f"(saved {before - after} bytes)"
    )


def replace_hdr_environment() -> None:
    # The 4K HDR panorama expands into both desktop and mobile GPU texture
    # variants in a Web export. A lightweight custom-color environment keeps
    # the top-down battlefield readable without shipping the panorama.
    write(
        "assets/default_env.tres",
        '''[gd_resource type="Environment" format=3 uid="uid://bdfocgrybgkli"]

[resource]
background_mode = 1
background_color = Color(0.16, 0.19, 0.22, 1)
ambient_light_source = 3
ambient_light_color = Color(1, 1, 1, 1)
ambient_light_energy = 0.8
reflected_light_source = 0
tonemap_mode = 2
adjustment_enabled = true
adjustment_saturation = 1.05
''',
    )


def exclude_hdr_from_export() -> None:
    path = "export_presets.cfg"
    text = read(path)
    old = 'exclude_filter="docs/*,scripts/services/online/*"'
    new = 'exclude_filter="docs/*,scripts/services/online/*,assets/kloppenheim_03_4k.hdr"'
    if new in text:
        return
    if old not in text:
        raise RuntimeError("Web export exclude_filter anchor not found")
    write(path, text.replace(old, new, 1))


def main() -> int:
    optimize_obj_imports()
    compact_map_json()
    replace_hdr_environment()
    exclude_hdr_from_export()
    print("Web size optimization pass applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
