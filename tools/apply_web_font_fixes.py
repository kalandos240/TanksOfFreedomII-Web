#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_SOURCE_CANDIDATES = (
    Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf"),
)
WEB_FONT = ROOT / "assets/fonts/ttf/tof_web_cyrillic.ttf"
PRIMARY_FONT = "res://assets/fonts/ttf/courier.ttf"
PRIMARY_UID = "uid://dkpcsi5rudp7j"
COMPOSITE_FONT = "res://assets/fonts/courier.tres"
COMPOSITE_UID = "uid://btstgc45ggura"
WEB_FONT_RES = "res://assets/fonts/ttf/tof_web_cyrillic.ttf"


def install_cyrillic_font() -> None:
    source = next((path for path in FONT_SOURCE_CANDIDATES if path.is_file()), None)
    if source is None:
        raise RuntimeError(
            "Noto Sans Regular is missing. Install the fonts-noto-core package before running the Web font patch."
        )

    WEB_FONT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, WEB_FONT)

    data = WEB_FONT.read_bytes()
    if len(data) < 100_000 or data[:4] not in (b"\x00\x01\x00\x00", b"OTTO"):
        raise RuntimeError("Generated Web Cyrillic font is not a valid SFNT font file")

    print(f"Installed deterministic Cyrillic Web font: {WEB_FONT.relative_to(ROOT)} ({len(data)} bytes)")


def write_composite_font() -> None:
    path = ROOT / "assets/fonts/courier.tres"
    text = '''[gd_resource type="FontFile" load_steps=3 format=3 uid="uid://btstgc45ggura"]

[ext_resource type="FontFile" uid="uid://dkpcsi5rudp7j" path="res://assets/fonts/ttf/courier.ttf" id="1"]
[ext_resource type="FontFile" path="res://assets/fonts/ttf/tof_web_cyrillic.ttf" id="2"]

[resource]
fallbacks = Array[Font]([ExtResource("1"), ExtResource("2")])
cache/0/16/0/ascent = 0.0
cache/0/16/0/descent = 0.0
cache/0/16/0/underline_position = 0.0
cache/0/16/0/underline_thickness = 0.0
cache/0/16/0/scale = 1.0
cache/0/16/0/kerning_overrides/16/0 = Vector2(0, 0)
cache/0/16/0/kerning_overrides/50/0 = Vector2(0, 0)
cache/0/50/0/ascent = 0.0
cache/0/50/0/descent = 0.0
cache/0/50/0/underline_position = 0.0
cache/0/50/0/underline_thickness = 0.0
cache/0/50/0/scale = 1.0
cache/0/50/0/kerning_overrides/16/0 = Vector2(0, 0)
cache/0/50/0/kerning_overrides/50/0 = Vector2(0, 0)
'''
    path.write_text(text, encoding="utf-8", newline="\n")
    print("Rebuilt courier.tres with embedded Noto Sans Cyrillic fallback.")


def write_legacy_size_font(path_name: str, size: int) -> None:
    path = ROOT / "assets/fonts" / path_name
    text = f'''[gd_resource type="FontFile" load_steps=3 format=3]

[ext_resource path="res://assets/fonts/ttf/courier.ttf" type="FontFile" id="1"]
[ext_resource path="res://assets/fonts/ttf/tof_web_cyrillic.ttf" type="FontFile" id="2"]

[resource]
fallbacks = Array[Font]([ExtResource("1"), ExtResource("2")])
size = {size}
outline_size = 1
outline_color = Color(0, 0, 0, 1)
font_data = ExtResource("1")
'''
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Rebuilt {path_name} with Cyrillic fallback.")


def _patch_reference_line(line: str) -> tuple[str, int]:
    count = line.count(PRIMARY_FONT)
    if count == 0:
        return line, 0

    patched = line.replace(PRIMARY_FONT, COMPOSITE_FONT)

    # Godot 4 ext_resource declarations may carry a UID as well as a path.
    # Leaving courier.ttf's UID next to courier.tres can make the loader resolve
    # the original TTF and silently bypass our embedded fallback.
    if patched.lstrip().startswith("[ext_resource "):
        patched = re.sub(
            r'uid="uid://[^"]+"',
            f'uid="{COMPOSITE_UID}"',
            patched,
            count=1,
        )

    return patched, count


def patch_direct_courier_references() -> None:
    patched_files = 0
    patched_refs = 0
    roots = (ROOT / "scenes", ROOT / "assets")

    for base in roots:
        for path in base.rglob("*"):
            if path.suffix not in {".tscn", ".tres"}:
                continue
            if path.parent == ROOT / "assets/fonts":
                continue

            text = path.read_text(encoding="utf-8")
            if PRIMARY_FONT not in text:
                continue

            patched_lines: list[str] = []
            file_refs = 0
            for line in text.splitlines(keepends=True):
                patched_line, count = _patch_reference_line(line)
                patched_lines.append(patched_line)
                file_refs += count

            patched = "".join(patched_lines)
            if text and not text.endswith(("\n", "\r")) and patched.endswith("\n"):
                patched = patched[:-1]

            path.write_text(patched, encoding="utf-8", newline="\n")
            patched_files += 1
            patched_refs += file_refs

    print(
        "Redirected direct Courier UI references to the composite font: "
        f"{patched_refs} reference(s) in {patched_files} file(s)."
    )


def validate_font_patch() -> None:
    if not WEB_FONT.is_file():
        raise RuntimeError("Web Cyrillic font was not generated")

    courier = (ROOT / "assets/fonts/courier.tres").read_text(encoding="utf-8")
    if WEB_FONT_RES not in courier:
        raise RuntimeError("courier.tres does not reference the embedded Cyrillic fallback")

    unresolved: list[str] = []
    stale_uids: list[str] = []
    for base in (ROOT / "scenes", ROOT / "assets"):
        for path in base.rglob("*"):
            if path.suffix not in {".tscn", ".tres"}:
                continue
            if path.parent == ROOT / "assets/fonts":
                continue

            text = path.read_text(encoding="utf-8")
            if PRIMARY_FONT in text:
                unresolved.append(str(path.relative_to(ROOT)))

            for line in text.splitlines():
                if COMPOSITE_FONT in line and PRIMARY_UID in line:
                    stale_uids.append(str(path.relative_to(ROOT)))
                    break

    if unresolved:
        raise RuntimeError(
            "Direct Courier references survived Web font patch: " + ", ".join(unresolved[:20])
        )
    if stale_uids:
        raise RuntimeError(
            "Courier path was redirected but old TTF UID survived: " + ", ".join(stale_uids[:20])
        )


def main() -> None:
    install_cyrillic_font()
    write_composite_font()
    write_legacy_size_font("courier_30.tres", 30)
    write_legacy_size_font("courier_big.tres", 42)
    patch_direct_courier_references()
    validate_font_patch()
    print("Applied deterministic Web Cyrillic font coverage.")


if __name__ == "__main__":
    main()
