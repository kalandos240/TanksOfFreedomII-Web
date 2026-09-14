#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        raise FileNotFoundError(target)
    return target.read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def restore_pair(text: str, modified: str, original: str) -> str:
    if modified in text:
        return text.replace(modified, original)
    return text


def restore_map_scene() -> None:
    path = "scenes/map/map.tscn"
    text = read(path)
    text = restore_pair(
        text,
        "albedo_color = Color(0.035294, 0.160784, 0.278431, 1)",
        "albedo_color = Color(0, 0, 0, 1)",
    )
    text = restore_pair(
        text,
        "colors = PackedColorArray(0.035294, 0.160784, 0.278431, 1, 0.176471, 0.898039, 0.956863, 1)",
        "colors = PackedColorArray(0, 0, 0, 1, 0.176471, 0.898039, 0.956863, 1)",
    )
    text = restore_pair(text, "light_energy = 1.2", "light_energy = 1.5")
    write(path, text)


def restore_water() -> None:
    material_path = "assets/water/water_material.tres"
    text = read(material_path)
    replacements = (
        ("shader_parameter/amplitude = Vector2(0.06, 0.035)", "shader_parameter/amplitude = Vector2(0.2, 0.1)"),
        ("shader_parameter/frequency = Vector2(1.5, 1.2)", "shader_parameter/frequency = Vector2(3, 2.5)"),
        ("shader_parameter/time_factor = Vector2(0.75, 0.55)", "shader_parameter/time_factor = Vector2(2, 1)"),
        ("shader_parameter/texture_scale = Vector2(24, 24)", "shader_parameter/texture_scale = Vector2(70, 70)"),
        ("shader_parameter/uv_offset_scale = Vector2(0.12, 0.12)", "shader_parameter/uv_offset_scale = Vector2(0.2, 0.2)"),
        ("shader_parameter/uv_offset_time_scale = 0.006", "shader_parameter/uv_offset_time_scale = 0.01"),
        ("shader_parameter/uv_offset_amplitude = 0.018", "shader_parameter/uv_offset_amplitude = 0.05"),
    )
    for modified, original in replacements:
        text = restore_pair(text, modified, original)
    text = text.replace("shader_parameter/normal_strength = 0.35\n", "")
    write(material_path, text)

    shader_path = "assets/water/water.gdshader"
    shader = read(shader_path)
    shader = shader.replace("uniform float normal_strength = 0.35;\n", "")
    shader = shader.replace(
        "    vec3 sampled_normal = texture(normalmap, base_uv_offset).rgb;\n"
        "    NORMAL_MAP = mix(vec3(0.5, 0.5, 1.0), sampled_normal, normal_strength);\n"
        "    METALLIC = 0.0;\n"
        "    ROUGHNESS = 0.9;\n",
        "    NORMAL_MAP = texture(normalmap, base_uv_offset).rgb;\n"
        "    //METALLIC = 0.0;\n"
        "    //ROUGHNESS = 1.0;\n",
    )
    write(shader_path, shader)


def restore_project_quality() -> None:
    path = "project.godot"
    text = read(path)
    text = restore_pair(
        text,
        "anti_aliasing/quality/msaa_3d=0",
        "anti_aliasing/quality/msaa_3d=2",
    )
    write(path, text)


def restore_runtime_video_defaults() -> None:
    path = "scripts/services/settings.gd"
    text = read(path)

    for modified, original in (
        ('\t"shadows" : false,', '\t"shadows" : true,'),
        ('\t"dec_shadows" : false,', '\t"dec_shadows" : true,'),
        ('\t"msaa": 0.0,', '\t"msaa": 2.0,'),
        ('\t"render_scale": 90,', '\t"render_scale": 100,'),
        ('\t"tilt_shift_enabled": false', '\t"tilt_shift_enabled": true'),
        ('\tself.settings["shadows"] = false', '\tself.settings["shadows"] = true'),
        ('\tself.settings["dec_shadows"] = false', '\tself.settings["dec_shadows"] = true'),
        ('\tself.settings["msaa"] = 0.0', '\tself.settings["msaa"] = 2.0'),
        ('\tself.settings["tilt_shift_enabled"] = false', '\tself.settings["tilt_shift_enabled"] = true'),
        ('\tself.settings["render_scale"] = min(float(self.settings["render_scale"]), 90.0)', '\tself.settings["render_scale"] = 100'),
    ):
        text = restore_pair(text, modified, original)

    old_coercion = '''\tmatch key:
\t\t"shadows", "dec_shadows", "fxaa", "vsync", "tilt_shift_enabled", "edge_pan":
\t\t\treturn false
\t\t"msaa":
\t\t\treturn 0.0
\t\t"fps", "ips":
\t\t\treturn min(float(value), 60.0)
\t\t"render_scale":
\t\t\treturn min(float(value), 90.0)
\treturn value
'''
    original_visual_coercion = '''\tmatch key:
\t\t"edge_pan":
\t\t\treturn false
\t\t"fps", "ips":
\t\t\treturn min(float(value), 60.0)
\treturn value
'''
    if old_coercion in text:
        text = text.replace(old_coercion, original_visual_coercion, 1)

    text = text.replace(
        "\t# Portal build: deterministic browser-safe defaults.\n"
        "\t# Apply after loading saved settings so unsupported values cannot return.\n",
        "\t# Keep the original desktop visual defaults on Web. Only portal-only\n"
        "\t# networking/input/timing policy is forced below.\n",
        1,
    )
    write(path, text)


def restore_video_settings_ui() -> None:
    path = "scenes/ui/menu/settings/settings_video.tscn"
    text = read(path)
    text = restore_pair(text, "max_value = 90", "max_value = 100")

    # UI hardening previously marked the original graphics controls unavailable.
    # Remove only the injected line directly after the known graphics nodes.
    for node_name in ("shadows", "dec_shadows", "tilt_shift", "fxaa", "vsync"):
        marker = f'[node name="{node_name}" parent="VBoxContainer" instance=ExtResource("1")]\nlayout_mode = 2\nunavailable = true\n'
        original = f'[node name="{node_name}" parent="VBoxContainer" instance=ExtResource("1")]\nlayout_mode = 2\n'
        text = restore_pair(text, marker, original)

    msaa_marker = '[node name="msaa" parent="VBoxContainer" instance=ExtResource("2")]\nlayout_mode = 2\nunavailable = true\n'
    msaa_original = '[node name="msaa" parent="VBoxContainer" instance=ExtResource("2")]\nlayout_mode = 2\n'
    text = restore_pair(text, msaa_marker, msaa_original)
    write(path, text)


def validate_original_visual_values() -> None:
    checks = {
        "scenes/map/map.tscn": (
            "albedo_color = Color(0, 0, 0, 1)",
            "colors = PackedColorArray(0, 0, 0, 1, 0.176471, 0.898039, 0.956863, 1)",
            "light_energy = 1.5",
        ),
        "assets/water/water_material.tres": (
            "shader_parameter/amplitude = Vector2(0.2, 0.1)",
            "shader_parameter/frequency = Vector2(3, 2.5)",
            "shader_parameter/time_factor = Vector2(2, 1)",
            "shader_parameter/texture_scale = Vector2(70, 70)",
            "shader_parameter/uv_offset_amplitude = 0.05",
        ),
        "project.godot": ("anti_aliasing/quality/msaa_3d=2",),
        "scripts/services/settings.gd": (
            '\t"shadows" : true,',
            '\t"dec_shadows" : true,',
            '\t"msaa": 2.0,',
            '\t"render_scale": 100,',
            '\t"tilt_shift_enabled": true',
            '\tself.settings["shadows"] = true',
            '\tself.settings["dec_shadows"] = true',
            '\tself.settings["msaa"] = 2.0',
            '\tself.settings["render_scale"] = 100',
            '\tself.settings["tilt_shift_enabled"] = true',
        ),
    }
    for path, needles in checks.items():
        text = read(path)
        for needle in needles:
            if needle not in text:
                raise RuntimeError(f"Original visual value missing in {path}: {needle}")

    shader = read("assets/water/water.gdshader")
    if "normal_strength" in shader or "ROUGHNESS = 0.9" in shader:
        raise RuntimeError("Web water shader tuning survived original-graphics restore")

    env = read("assets/default_env.tres")
    for needle in (
        "background_mode = 2",
        "ambient_light_sky_contribution = 0.2",
        "reflected_light_source = 1",
        "tonemap_mode = 3",
        "tonemap_white = 4.0",
        "ssao_enabled = true",
        "ssil_enabled = true",
        "adjustment_saturation = 1.1",
        "res://assets/kloppenheim_03_4k.hdr",
    ):
        if needle not in env:
            raise RuntimeError(f"Original environment value missing: {needle}")

    print("Original visual parity checks passed.")


def main() -> None:
    restore_map_scene()
    restore_water()
    restore_project_quality()
    restore_runtime_video_defaults()
    restore_video_settings_ui()
    validate_original_visual_values()
    print("Restored original Tanks of Freedom II graphics for the Web build.")


if __name__ == "__main__":
    main()
