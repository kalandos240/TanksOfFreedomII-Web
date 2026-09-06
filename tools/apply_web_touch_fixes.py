#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    p = ROOT / path
    if not p.exists():
        raise FileNotFoundError(f"Required file is missing: {path}")
    return p.read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Patch anchor not found for {label}")
    return text.replace(old, new, 1)


def patch_camera_touch() -> None:
    path = "scenes/camera.gd"
    text = read(path)

    old_vars = "var camera_pan = Vector2(0, 0)\nvar _last_used_blur_magnitude = 0\n"
    new_vars = (
        "var camera_pan = Vector2(0, 0)\n"
        "var _last_used_blur_magnitude = 0\n\n"
        "# Native Web/mobile touch camera state. Mouse emulation remains enabled for\n"
        "# UI/tile taps, while camera.gd ignores those emulated mouse events to avoid\n"
        "# applying the same drag twice.\n"
        "var _touch_points: Dictionary = {}\n"
        "var _touch_pinch_distance := 0.0\n"
        "@export var touch_zoom_sensitivity := 0.05\n"
    )
    text = replace_once(text, old_vars, new_vars, "touch camera state")

    old_dispatch = (
        "\tif self.camera_in_transit or self.ai_operated or self.script_operated:\n"
        "\t\treturn\n\n"
        "\tif event is InputEventMouseButton and event.button_index in [MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_LEFT, MOUSE_BUTTON_MIDDLE]:\n"
    )
    new_dispatch = (
        "\tif event is InputEventScreenTouch:\n"
        "\t\tself._handle_screen_touch(event)\n"
        "\t\treturn\n"
        "\tif event is InputEventScreenDrag:\n"
        "\t\tself._handle_screen_drag(event)\n"
        "\t\treturn\n\n"
        "\tif self.camera_in_transit or self.ai_operated or self.script_operated:\n"
        "\t\treturn\n\n"
        "\t# Touch-to-mouse emulation is still useful for buttons and tile taps, but the\n"
        "\t# camera handles native touch directly and must not process the emulated copy.\n"
        "\tif event.device == InputEvent.DEVICE_ID_EMULATION:\n"
        "\t\treturn\n\n"
        "\tif event is InputEventMouseButton and event.button_index in [MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_LEFT, MOUSE_BUTTON_MIDDLE]:\n"
    )
    text = replace_once(text, old_dispatch, new_dispatch, "touch event dispatch")

    old_helpers_anchor = (
        "\telif event is InputEventMagnifyGesture:\n"
        "\t\tvar zoom_steps = int((event.factor - 1) * 100)\n"
        "\t\tself._mouse_zoom(self.mouse_zoom_step * zoom_steps)\n\n"
        "func _process(delta):\n"
    )
    new_helpers = (
        "\telif event is InputEventMagnifyGesture:\n"
        "\t\tvar zoom_steps = int((event.factor - 1) * 100)\n"
        "\t\tself._mouse_zoom(self.mouse_zoom_step * zoom_steps)\n\n"
        "func _handle_screen_touch(event: InputEventScreenTouch) -> void:\n"
        "\tif event.pressed:\n"
        "\t\tself._touch_points[event.index] = event.position\n"
        "\telse:\n"
        "\t\tself._touch_points.erase(event.index)\n\n"
        "\tif self._touch_points.size() >= 2:\n"
        "\t\tself._touch_pinch_distance = self._get_touch_distance()\n"
        "\telse:\n"
        "\t\tself._touch_pinch_distance = 0.0\n\n"
        "func _handle_screen_drag(event: InputEventScreenDrag) -> void:\n"
        "\tself._touch_points[event.index] = event.position\n\n"
        "\t# Keep finger state current during scripted/AI camera movement, but do not\n"
        "\t# allow the player to fight an active camera transition.\n"
        "\tif self.camera_in_transit or self.ai_operated or self.script_operated:\n"
        "\t\tif self._touch_points.size() >= 2:\n"
        "\t\t\tself._touch_pinch_distance = self._get_touch_distance()\n"
        "\t\telse:\n"
        "\t\t\tself._touch_pinch_distance = 0.0\n"
        "\t\treturn\n\n"
        "\tif self._touch_points.size() >= 2:\n"
        "\t\tvar distance = self._get_touch_distance()\n"
        "\t\tif self._touch_pinch_distance > 0.0:\n"
        "\t\t\tvar distance_delta = distance - self._touch_pinch_distance\n"
        "\t\t\tself._mouse_zoom(-distance_delta * self.touch_zoom_sensitivity)\n"
        "\t\tself._touch_pinch_distance = distance\n"
        "\t\treturn\n\n"
        "\tself._touch_pinch_distance = 0.0\n"
        "\tself._mouse_shift_camera(event.relative)\n\n"
        "func _get_touch_distance() -> float:\n"
        "\tvar ids = self._touch_points.keys()\n"
        "\tif ids.size() < 2:\n"
        "\t\treturn 0.0\n"
        "\treturn self._touch_points[ids[0]].distance_to(self._touch_points[ids[1]])\n\n"
        "func _process(delta):\n"
    )
    text = replace_once(text, old_helpers_anchor, new_helpers, "touch camera helpers")

    write(path, text)


def main() -> int:
    patch_camera_touch()
    print("Applied native Web touch camera controls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
