#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Patch anchor not found for {label}")
    return text.replace(old, new, 1)


def patch_web_texture_imports() -> None:
    path = "project.godot"
    text = read(path)

    etc2_setting = "textures/vram_compression/import_etc2_astc=true\n"
    s3tc_on = "textures/vram_compression/import_s3tc_bptc=true\n"
    s3tc_off = "textures/vram_compression/import_s3tc_bptc=false\n"

    if etc2_setting not in text:
        anchor = 'renderer/rendering_method.web="gl_compatibility"\n'
        addition = anchor + etc2_setting + s3tc_off
        text = replace_once(text, anchor, addition, "Web ETC2 texture imports")
    elif s3tc_on in text:
        text = text.replace(s3tc_on, s3tc_off, 1)
    elif s3tc_off not in text:
        text = text.replace(etc2_setting, etc2_setting + s3tc_off, 1)

    write(path, text)


def _remove_exclude_filter_items(text: str, items: set[str]) -> str:
    lines = text.splitlines(keepends=True)
    changed = False
    for index, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        if not stripped.startswith('exclude_filter="') or not stripped.endswith('"'):
            continue
        value = stripped[len('exclude_filter="'):-1]
        filters = [item for item in value.split(",") if item and item not in items]
        newline = "\n" if line.endswith("\n") else ""
        replacement = 'exclude_filter="' + ",".join(filters) + '"' + newline
        if replacement != line:
            lines[index] = replacement
            changed = True
    return "".join(lines) if changed else text


def patch_web_export_texture_profile() -> None:
    path = "export_presets.cfg"
    text = read(path)

    # WebGL2 uses the portable mobile texture path. This changes only GPU
    # encoding, not the source artwork/material/environment parameters.
    text = text.replace(
        "vram_texture_compression/for_desktop=true",
        "vram_texture_compression/for_desktop=false",
        1,
    )
    if "vram_texture_compression/for_mobile=true" not in text:
        raise RuntimeError("Web ETC2 export profile is missing mobile texture compression")

    runtime_filter = "assets/translations/*.ru.runtime.txt"
    if runtime_filter not in text:
        csv_filter = "assets/translations/*.ru.csv"
        if csv_filter not in text:
            raise RuntimeError("Russian CSV export filter is missing")
        text = text.replace(csv_filter, f"{csv_filter},{runtime_filter}", 1)

    # Older Web patches excluded the original 4K panorama. Remove those
    # exclusions: the original HDR must ship so Web can reproduce the desktop
    # lighting/tonemapping as closely as the Compatibility renderer allows.
    text = _remove_exclude_filter_items(
        text,
        {
            "assets/kloppenheim_03_4k.hdr",
            "assets/terrain/sky/kloppenheim_03_4k.hdr",
        },
    )
    write(path, text)


def write_ru_runtime_sources() -> None:
    for stem in ("common", "core"):
        source = f"assets/translations/{stem}.ru.csv"
        runtime = f"assets/translations/{stem}.ru.runtime.txt"
        write(runtime, read(source))


def validate_original_hdr_graphics() -> None:
    hdr = ROOT / "assets/kloppenheim_03_4k.hdr"
    if not hdr.exists() or hdr.stat().st_size == 0:
        raise RuntimeError("Original Kloppenheim 4K HDR panorama is missing")

    for rel in ("assets/default_env.tres", "scenes/map_editor/tile_cam.tscn"):
        text = read(rel)
        if "res://assets/kloppenheim_03_4k.hdr" not in text:
            raise RuntimeError(f"{rel} no longer references the original HDR panorama")
        if ".bptc.ctex" in text:
            raise RuntimeError(f"{rel} still contains a desktop-only BPTC cache path")

    print("Original HDR panorama retained; resources use source-path remapping for Web.")


def patch_browser_fullscreen() -> None:
    path = "scripts/services/settings.gd"
    text = read(path)
    old = (
        'if key == "fullscreen":\n'
        '\t\tget_window().mode = Window.MODE_EXCLUSIVE_FULLSCREEN if (self.settings[key]) else Window.MODE_WINDOWED\n'
    )
    new = (
        'if key == "fullscreen":\n'
        '\t\tif OS.has_feature("web"):\n'
        '\t\t\tget_window().mode = Window.MODE_FULLSCREEN if (self.settings[key]) else Window.MODE_WINDOWED\n'
        '\t\telse:\n'
        '\t\t\tget_window().mode = Window.MODE_EXCLUSIVE_FULLSCREEN if (self.settings[key]) else Window.MODE_WINDOWED\n'
    )
    text = replace_once(text, old, new, "browser fullscreen")
    write(path, text)


def patch_audio_focus() -> None:
    path = "scripts/services/audio.gd"
    text = read(path)

    old_vars = "var _last_requested_track = null\n\nvar master_switch = false\n"
    new_vars = (
        "var _last_requested_track = null\n"
        "var _paused_for_focus := false\n\n"
        "var master_switch = false\n"
    )
    text = replace_once(text, old_vars, new_vars, "audio focus state")

    old_play = "func play(sample_name):\n"
    new_play = (
        "func _notification(what):\n"
        "\tif what == NOTIFICATION_APPLICATION_FOCUS_OUT:\n"
        "\t\tself._paused_for_focus = self.current_track != null and self.current_track.is_playing()\n"
        "\t\tself.pause()\n"
        "\t\tfor sample in self.samples.values():\n"
        "\t\t\tsample.stop()\n"
        "\telif what == NOTIFICATION_APPLICATION_FOCUS_IN:\n"
        "\t\tif self._paused_for_focus and self.music_enabled:\n"
        "\t\t\tself.unpause()\n"
        "\t\tself._paused_for_focus = false\n\n"
        "func play(sample_name):\n"
    )
    text = replace_once(text, old_play, new_play, "audio focus notification")
    write(path, text)


def patch_missing_reflection_materials() -> None:
    # These two upstream OBJ files reference missing MTL sidecars. Recreating
    # the palette declarations prevents Godot from dropping their intended
    # diffuse textures during a clean CI import.
    template = """# MagicaVoxel @ Ephtracy

newmtl palette
illum 1
Ka 0.000 0.000 0.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
map_Kd {texture}
"""
    for stem in ("river_1_reflection", "river_2_reflection"):
        write(
            f"assets/terrain/reflections/{stem}.mtl",
            template.format(texture=f"{stem}.png"),
        )


def main() -> None:
    patch_web_texture_imports()
    patch_web_export_texture_profile()
    write_ru_runtime_sources()
    validate_original_hdr_graphics()
    patch_browser_fullscreen()
    patch_audio_focus()
    patch_missing_reflection_materials()
    print("Applied browser runtime fixes without downgrading original graphics.")


if __name__ == "__main__":
    main()
