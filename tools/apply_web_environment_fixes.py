#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TILE_CAM = ROOT / "scenes/map_editor/tile_cam.tscn"


def patch_tile_cam_environment() -> None:
    text = TILE_CAM.read_text(encoding="utf-8")
    forbidden = ("kloppenheim_03_4k.hdr", ".bptc.ctex")

    if not any(token in text for token in forbidden):
        print("Map editor tile camera environment is already Web-safe.")
        return

    marker = '[node name="tile_cam" type="Node3D"]'
    if marker not in text:
        raise RuntimeError("tile_cam scene node anchor is missing")

    first_line = text.splitlines()[0]
    if not first_line.startswith("[gd_scene "):
        raise RuntimeError("Unexpected tile_cam scene header")
    first_line = re.sub(r"load_steps=\d+", "load_steps=2", first_line, count=1)

    safe_environment = f'''{first_line}

[sub_resource type="Environment" id="Environment_gx6lk"]
background_mode = 1
background_color = Color(0.16, 0.19, 0.22, 1)
ambient_light_source = 3
ambient_light_color = Color(1, 1, 1, 1)
ambient_light_energy = 0.8
reflected_light_source = 0
tonemap_mode = 2
adjustment_enabled = true
adjustment_saturation = 1.1

'''

    patched = safe_environment + text[text.index(marker):]
    if any(token in patched for token in forbidden):
        raise RuntimeError("Desktop HDR/BPTC reference survived tile_cam Web patch")

    TILE_CAM.write_text(patched, encoding="utf-8", newline="\n")
    print("Replaced map editor HDR environment with Web-safe environment.")


def main() -> None:
    patch_tile_cam_environment()


if __name__ == "__main__":
    main()
