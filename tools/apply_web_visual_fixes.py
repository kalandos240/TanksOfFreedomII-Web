#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_SCENE = ROOT / "scenes/map/map.tscn"
WATER_MATERIAL = ROOT / "assets/water/water_material.tres"
WATER_SHADER = ROOT / "assets/water/water.gdshader"
DEFAULT_ENV = ROOT / "assets/default_env.tres"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            print(f"{label}: already patched")
            return
        raise RuntimeError(f"{label}: expected source block not found in {path}")

    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one source block in {path}")

    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"{label}: patched")


def patch_map_backdrop_and_light() -> None:
    replace_once(
        MAP_SCENE,
        'albedo_color = Color(0, 0, 0, 1)',
        'albedo_color = Color(0.035294, 0.160784, 0.278431, 1)',
        "Ocean void backdrop",
    )
    replace_once(
        MAP_SCENE,
        'colors = PackedColorArray(0, 0, 0, 1, 0.176471, 0.898039, 0.956863, 1)',
        'colors = PackedColorArray(0.035294, 0.160784, 0.278431, 1, 0.176471, 0.898039, 0.956863, 1)',
        "Ocean side gradient",
    )
    replace_once(
        MAP_SCENE,
        'light_energy = 1.5',
        'light_energy = 1.2',
        "Web directional light energy",
    )


def patch_water_material() -> None:
    replacements = [
        ('shader_parameter/amplitude = Vector2(0.2, 0.1)', 'shader_parameter/amplitude = Vector2(0.06, 0.035)', "Water amplitude"),
        ('shader_parameter/frequency = Vector2(3, 2.5)', 'shader_parameter/frequency = Vector2(1.5, 1.2)', "Water frequency"),
        ('shader_parameter/time_factor = Vector2(2, 1)', 'shader_parameter/time_factor = Vector2(0.75, 0.55)', "Water animation speed"),
        ('shader_parameter/texture_scale = Vector2(70, 70)', 'shader_parameter/texture_scale = Vector2(24, 24)', "Water texture scale"),
        ('shader_parameter/uv_offset_scale = Vector2(0.2, 0.2)', 'shader_parameter/uv_offset_scale = Vector2(0.12, 0.12)', "Water UV scale"),
        ('shader_parameter/uv_offset_time_scale = 0.01', 'shader_parameter/uv_offset_time_scale = 0.006', "Water UV speed"),
        ('shader_parameter/uv_offset_amplitude = 0.05', 'shader_parameter/uv_offset_amplitude = 0.018', "Water UV amplitude"),
    ]
    for old, new, label in replacements:
        replace_once(WATER_MATERIAL, old, new, label)

    text = WATER_MATERIAL.read_text(encoding="utf-8")
    marker = 'shader_parameter/uv_offset_amplitude = 0.018\n'
    extra = 'shader_parameter/normal_strength = 0.35\n'
    if extra not in text:
        if marker not in text:
            raise RuntimeError("Water normal strength insertion anchor is missing")
        text = text.replace(marker, marker + extra, 1)
        WATER_MATERIAL.write_text(text, encoding="utf-8", newline="\n")
        print("Water normal strength: patched")
    else:
        print("Water normal strength: already patched")


def patch_water_shader() -> None:
    text = WATER_SHADER.read_text(encoding="utf-8")
    normal_uniform = 'uniform sampler2D normalmap : hint_normal;\nuniform float normal_strength = 0.35;\n'
    if normal_uniform not in text:
        old = 'uniform sampler2D normalmap : hint_normal;\n'
        if old not in text:
            raise RuntimeError("Water shader normal-map uniform anchor is missing")
        text = text.replace(old, normal_uniform, 1)

    old_fragment = '''    NORMAL_MAP = texture(normalmap, base_uv_offset).rgb;
    //METALLIC = 0.0;
    //ROUGHNESS = 1.0;
'''
    new_fragment = '''    vec3 sampled_normal = texture(normalmap, base_uv_offset).rgb;
    NORMAL_MAP = mix(vec3(0.5, 0.5, 1.0), sampled_normal, normal_strength);
    METALLIC = 0.0;
    ROUGHNESS = 0.9;
'''
    if old_fragment in text:
        text = text.replace(old_fragment, new_fragment, 1)
    elif new_fragment not in text:
        raise RuntimeError("Water shader fragment anchor is missing")

    WATER_SHADER.write_text(text, encoding="utf-8", newline="\n")
    print("Water shader normal/roughness tuning: patched")


def patch_environment_saturation() -> None:
    text = DEFAULT_ENV.read_text(encoding="utf-8")
    if 'adjustment_saturation = 1.0' in text:
        print("Web environment saturation: already patched")
        return

    candidates = ('adjustment_saturation = 1.05', 'adjustment_saturation = 1.1')
    for old in candidates:
        if old in text:
            text = text.replace(old, 'adjustment_saturation = 1.0', 1)
            DEFAULT_ENV.write_text(text, encoding="utf-8", newline="\n")
            print("Web environment saturation: patched")
            return

    raise RuntimeError("Web environment saturation setting was not found")


def main() -> None:
    patch_map_backdrop_and_light()
    patch_water_material()
    patch_water_shader()
    patch_environment_saturation()


if __name__ == "__main__":
    main()
