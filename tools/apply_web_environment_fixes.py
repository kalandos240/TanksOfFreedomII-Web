#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = ROOT / "assets/default_env.tres"
TILE_CAM = ROOT / "scenes/map_editor/tile_cam.tscn"
HDR = "res://assets/kloppenheim_03_4k.hdr"
HDR_UID = "uid://bieopmsruclpo"


DEFAULT_ENV_TEXT = f'''[gd_resource type="Environment" load_steps=4 format=3 uid="uid://bdfocgrybgkli"]

[ext_resource type="Texture2D" uid="{HDR_UID}" path="{HDR}" id="1_hdr"]

[sub_resource type="PanoramaSkyMaterial" id="PanoramaSkyMaterial_i00vh"]
panorama = ExtResource("1_hdr")

[sub_resource type="Sky" id="1"]
sky_material = SubResource("PanoramaSkyMaterial_i00vh")

[resource]
background_mode = 2
sky = SubResource("1")
sky_custom_fov = 70.0
ambient_light_color = Color(1, 1, 1, 1)
ambient_light_sky_contribution = 0.2
reflected_light_source = 1
tonemap_mode = 3
tonemap_white = 4.0
ssao_enabled = true
ssil_enabled = true
adjustment_enabled = true
adjustment_saturation = 1.1
'''


TILE_CAM_TEXT = f'''[gd_scene load_steps=5 format=3 uid="uid://cry3kqpb8cvim"]

[ext_resource type="Texture2D" uid="{HDR_UID}" path="{HDR}" id="1_hdr"]

[sub_resource type="PanoramaSkyMaterial" id="PanoramaSkyMaterial_i00vh"]
panorama = ExtResource("1_hdr")

[sub_resource type="Sky" id="1"]
sky_material = SubResource("PanoramaSkyMaterial_i00vh")

[sub_resource type="Environment" id="Environment_gx6lk"]
background_mode = 2
sky = SubResource("1")
sky_custom_fov = 70.0
ambient_light_color = Color(1, 1, 1, 1)
ambient_light_sky_contribution = 0.2
reflected_light_source = 1
tonemap_mode = 3
tonemap_white = 4.0
ssao_enabled = true
ssil_enabled = true
adjustment_enabled = true
adjustment_saturation = 1.1

[node name="tile_cam" type="Node3D"]

[node name="pivot" type="Node3D" parent="."]
transform = Transform3D(0.707107, 0, 0.707107, 0, 1, 0, -0.707107, 0, 0.707107, 0, 0, 0)

[node name="arm" type="Node3D" parent="pivot"]
transform = Transform3D(1, 0, 0, 0, 0.866025, 0.5, 0, -0.5, 0.866025, 0, 0, 0)

[node name="lens" type="Camera3D" parent="pivot/arm"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 20)
projection = 1
size = 20.0

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("Environment_gx6lk")

[node name="DirectionalLight3D" type="DirectionalLight3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 0.707107, 0.707107, 0, -0.707107, 0.707107, 0, 50, 50)
'''


def write_if_needed(path: Path, text: str, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    current = path.read_text(encoding="utf-8")
    if current == text:
        print(f"{label}: already preserves original graphics")
        return
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"{label}: restored original HDR/lighting parameters")


def main() -> None:
    hdr_source = ROOT / "assets/kloppenheim_03_4k.hdr"
    if not hdr_source.exists() or hdr_source.stat().st_size == 0:
        raise RuntimeError("Original Kloppenheim 4K HDR panorama is missing")

    # Upstream serialized a cache-specific .bptc.ctex path directly into these
    # resources. WebGL cannot consume that desktop cache file. Reference the
    # original HDR source instead so Godot imports a Web-compatible texture,
    # while keeping every original environment/tonemapping value unchanged.
    write_if_needed(DEFAULT_ENV, DEFAULT_ENV_TEXT, "Default environment")
    write_if_needed(TILE_CAM, TILE_CAM_TEXT, "Map editor environment")


if __name__ == "__main__":
    main()
