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

    if "textures/vram_compression/import_etc2_astc=true" not in text:
        anchor = 'renderer/rendering_method.web="gl_compatibility"\n'
        addition = (
            anchor
            + "textures/vram_compression/import_etc2_astc=true\n"
            + "textures/vram_compression/import_s3tc_bptc=true\n"
        )
        text = replace_once(text, anchor, addition, "Web texture import formats")

    write(path, text)


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
    # Upstream contains two river reflection OBJ files that reference MTL files
    # which are absent from the repository. Godot imports the geometry without
    # them, but emits hard ERROR lines and the surfaces lose their palette map.
    # Recreate the deterministic MagicaVoxel material definitions so clean Web
    # imports are error-free and visually match the neighboring reflection assets.
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
    patch_browser_fullscreen()
    patch_audio_focus()
    patch_missing_reflection_materials()
    print("Applied browser runtime and Web export fixes.")


if __name__ == "__main__":
    main()
