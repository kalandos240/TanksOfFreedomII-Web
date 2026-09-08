#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_SOURCE_CANDIDATES = (
    Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf"),
)
WEB_FONT = ROOT / "assets/fonts/ttf/tof_web_cyrillic.ttf"
PRIMARY_FONT = "res://assets/fonts/ttf/courier.ttf"
COMPOSITE_FONT = "res://assets/fonts/courier.tres"
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
            count = text.count(PRIMARY_FONT)
            if count == 0:
                continue

            path.write_text(
                text.replace(PRIMARY_FONT, COMPOSITE_FONT),
                encoding="utf-8",
                newline="\n",
            )
            patched_files += 1
            patched_refs += count

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
    for base in (ROOT / "scenes", ROOT / "assets"):
        for path in base.rglob("*"):
            if path.suffix not in {".tscn", ".tres"}:
                continue
            if path.parent == ROOT / "assets/fonts":
                continue
            if PRIMARY_FONT in path.read_text(encoding="utf-8"):
                unresolved.append(str(path.relative_to(ROOT)))

    if unresolved:
        raise RuntimeError(
            "Direct Courier references survived Web font patch: " + ", ".join(unresolved[:20])
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
