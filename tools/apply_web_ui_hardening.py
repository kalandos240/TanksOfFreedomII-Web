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


def patch_menu_cancel_focus() -> None:
    path = "scenes/ui/menu/menu.gd"
    text = read(path)
    old = (
        '\tif event.is_action_pressed("ui_cancel"):\n'
        '\t\tself.quit_button.grab_focus()\n'
    )
    new = (
        '\tif event.is_action_pressed("ui_cancel"):\n'
        '\t\t# Quit is hidden in the browser build. Never move keyboard/gamepad\n'
        '\t\t# focus to an invisible control. Keep native behavior unchanged.\n'
        '\t\tif self.quit_button.is_visible_in_tree() and not self.quit_button.disabled:\n'
        '\t\t\tself.quit_button.grab_focus()\n'
        '\t\telse:\n'
        '\t\t\tself.settings_button.grab_focus()\n'
    )
    text = replace_once(text, old, new, "Web menu cancel focus")
    write(path, text)


def patch_settings_runtime_guards() -> None:
    path = "scripts/services/settings.gd"
    text = read(path)

    old_profile = (
        'func _apply_web_profile():\n'
        '\t# Portal build: deterministic browser-safe defaults.\n'
    )
    new_profile = (
        'func _apply_web_profile():\n'
        '\tif not OS.has_feature("web"):\n'
        '\t\treturn\n\n'
        '\t# Portal build: deterministic browser-safe defaults.\n'
    )
    text = replace_once(text, old_profile, new_profile, "Web profile feature guard")

    old_scale = (
        '\tself.settings["tilt_shift_enabled"] = false\n'
        '\tself.settings["online_domain"] = ""\n'
    )
    new_scale = (
        '\tself.settings["tilt_shift_enabled"] = false\n'
        '\tself.settings["render_scale"] = min(float(self.settings["render_scale"]), 90.0)\n'
        '\tself.settings["online_domain"] = ""\n'
    )
    text = replace_once(text, old_scale, new_scale, "Web render scale cap")

    old_load = (
        'func load_settings_from_file():\n'
        '\tvar loaded_settings = self.filesystem.read_json_from_file(self.SETTINGS_FILE_PATH)\n\n'
        '\tfor settings_key in loaded_settings:\n'
        '\t\tself.settings[settings_key] = loaded_settings[settings_key]\n'
        '\t\tself._apply_option(settings_key)\n'
    )
    new_load = (
        'func _coerce_web_option(key, value):\n'
        '\tif not OS.has_feature("web"):\n'
        '\t\treturn value\n\n'
        '\tmatch key:\n'
        '\t\t"shadows", "dec_shadows", "fxaa", "vsync", "tilt_shift_enabled", "edge_pan":\n'
        '\t\t\treturn false\n'
        '\t\t"msaa":\n'
        '\t\t\treturn 0.0\n'
        '\t\t"fps", "ips":\n'
        '\t\t\treturn min(float(value), 60.0)\n'
        '\t\t"render_scale":\n'
        '\t\t\treturn min(float(value), 90.0)\n'
        '\treturn value\n\n'
        'func load_settings_from_file():\n'
        '\tvar loaded_settings = self.filesystem.read_json_from_file(self.SETTINGS_FILE_PATH)\n\n'
        '\tfor settings_key in loaded_settings:\n'
        '\t\tself.settings[settings_key] = self._coerce_web_option(settings_key, loaded_settings[settings_key])\n'
        '\t\tself._apply_option(settings_key)\n'
    )
    text = replace_once(text, old_load, new_load, "Web saved settings coercion")

    old_set = (
        'func set_option(key, value):\n'
        '\t# Keep browser-incompatible values from being re-enabled at runtime.\n'
        '\tif key == "tilt_shift_enabled" or key == "edge_pan":\n'
        '\t\tvalue = false\n'
        '\telif key == "fps" or key == "ips":\n'
        '\t\tvalue = min(float(value), 60.0)\n'
        '\tself.settings[key] = value\n'
    )
    new_set = (
        'func set_option(key, value):\n'
        '\t# Apply the same browser policy to UI changes and programmatic writes.\n'
        '\tvalue = self._coerce_web_option(key, value)\n'
        '\tself.settings[key] = value\n'
    )
    text = replace_once(text, old_set, new_set, "Web runtime settings coercion")

    write(path, text)


def patch_video_settings_ui() -> None:
    path = "scenes/ui/menu/settings/settings_video.tscn"
    text = read(path)

    text = replace_once(
        text,
        'max_value = 100\n',
        'max_value = 90\n',
        "Web render scale UI cap",
    )

    for node_name in ("shadows", "dec_shadows", "tilt_shift", "fxaa", "vsync"):
        old = f'[node name="{node_name}" parent="VBoxContainer" instance=ExtResource("1")]\nlayout_mode = 2\n'
        new = old + 'unavailable = true\n'
        text = replace_once(text, old, new, f"disable {node_name} on Web")

    old_msaa = (
        '[node name="msaa" parent="VBoxContainer" instance=ExtResource("2")]\n'
        'layout_mode = 2\n'
    )
    new_msaa = old_msaa + 'unavailable = true\n'
    text = replace_once(text, old_msaa, new_msaa, "disable MSAA on Web")

    old_fps = (
        '[node name="fps" parent="VBoxContainer" instance=ExtResource("2")]\n'
        'layout_mode = 2\n'
        'option_name = "TR_FPS_L"\n'
        'option_key = "fps"\n'
        'help_tip = "TR_FPS_L_DESC"\n'
        'available_values = [30.0, 60.0, 90.0, 120.0, 144.0]\n'
    )
    new_fps = old_fps.replace(
        'available_values = [30.0, 60.0, 90.0, 120.0, 144.0]',
        'available_values = [30.0, 60.0]',
    )
    text = replace_once(text, old_fps, new_fps, "Web FPS choices")

    old_ips = (
        '[node name="ips" parent="VBoxContainer" instance=ExtResource("2")]\n'
        'layout_mode = 2\n'
        'option_name = "TR_IPS_L"\n'
        'option_key = "ips"\n'
        'help_tip = "TR_IPS_L_DESC"\n'
        'available_values = [30.0, 60.0, 90.0, 120.0, 144.0]\n'
    )
    new_ips = old_ips.replace(
        'available_values = [30.0, 60.0, 90.0, 120.0, 144.0]',
        'available_values = [30.0, 60.0]',
    )
    text = replace_once(text, old_ips, new_ips, "Web IPS choices")

    write(path, text)


def main() -> None:
    patch_menu_cancel_focus()
    patch_settings_runtime_guards()
    patch_video_settings_ui()
    print("Applied Web UI and graphics hardening fixes.")


if __name__ == "__main__":
    main()
