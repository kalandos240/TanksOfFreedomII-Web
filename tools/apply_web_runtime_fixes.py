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


def patch_web_export_texture_profile() -> None:
    path = "export_presets.cfg"
    text = read(path)

    # WebGL2 has a portable ETC2 path. Do not package desktop S3TC/BPTC
    # variants into the portal build; Chromium/SwiftShader can advertise a
    # partial desktop compression path and then reject individual mip levels.
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

    # The 4K desktop panorama is not used by the Web environment and is not a
    # valid WebGL2 payload. Keep both historical upstream locations excluded in
    # case a future upstream sync restores either one.
    root_hdr = "assets/kloppenheim_03_4k.hdr"
    legacy_hdr = "assets/terrain/sky/kloppenheim_03_4k.hdr"
    if root_hdr in text and legacy_hdr not in text:
        text = text.replace(root_hdr, f"{root_hdr},{legacy_hdr}", 1)

    write(path, text)


def write_ru_runtime_sources() -> None:
    # Translation CSV files are imported by Godot and the original source path
    # is not guaranteed to exist inside an exported PCK. Keep byte-equivalent
    # raw text copies under an unimported extension for FileAccess at runtime.
    for stem in ("common", "core"):
        source = f"assets/translations/{stem}.ru.csv"
        runtime = f"assets/translations/{stem}.ru.runtime.txt"
        write(runtime, read(source))


def remove_desktop_hdr_assets() -> None:
    # The Web scene graph uses assets/default_env.tres and does not need the
    # Kloppenheim 4K panorama. Godot 4.4 can regenerate its desktop import as a
    # BPTC-only .ctex while exporting, even when the source HDR itself is
    # excluded. That leaves a stale remap inside the PCK and crashes WebGL2 at
    # runtime. Remove the source + import metadata before Godot scans the Web
    # project so no BPTC remap can be generated or embedded.
    needle = "kloppenheim_03_4k.hdr"
    unexpected_refs: list[str] = []
    for base in ("scenes", "scripts", "assets"):
        root = ROOT / base
        if not root.exists():
            continue
        for candidate in root.rglob("*"):
            if not candidate.is_file() or candidate.suffix.lower() not in {".tscn", ".tres", ".gd"}:
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if needle in text:
                unexpected_refs.append(candidate.relative_to(ROOT).as_posix())

    if unexpected_refs:
        joined = ", ".join(sorted(unexpected_refs))
        raise RuntimeError(f"Desktop HDR is still referenced by Web resources: {joined}")

    removed: list[str] = []
    for rel in (
        "assets/kloppenheim_03_4k.hdr",
        "assets/kloppenheim_03_4k.hdr.import",
        "assets/terrain/sky/kloppenheim_03_4k.hdr",
        "assets/terrain/sky/kloppenheim_03_4k.hdr.import",
    ):
        target = ROOT / rel
        if target.exists():
            target.unlink()
            removed.append(rel)

    if removed:
        print("Removed desktop-only HDR assets: " + ", ".join(removed))
    else:
        print("Desktop-only HDR assets already absent.")


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
    patch_web_export_texture_profile()
    write_ru_runtime_sources()
    remove_desktop_hdr_assets()
    patch_browser_fullscreen()
    patch_audio_focus()
    patch_missing_reflection_materials()
    print("Applied browser runtime and Web export fixes.")


if __name__ == "__main__":
    main()
