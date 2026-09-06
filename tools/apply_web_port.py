#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    p = ROOT / path
    if not p.exists():
        raise FileNotFoundError(f"Required upstream file is missing: {path}")
    return p.read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8", newline="\n")


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Patch anchor not found for {label}")
    return text.replace(old, new, 1)


def patch_project() -> None:
    path = "project.godot"
    text = read(path)
    text = replace_required(text, "common/physics_fps=144", "common/physics_fps=60", "physics FPS")

    if 'renderer/rendering_method="gl_compatibility"' not in text:
        text = replace_required(
            text,
            "[rendering]\n\n",
            "[rendering]\n\n"
            'renderer/rendering_method="gl_compatibility"\n'
            'renderer/rendering_method.mobile="gl_compatibility"\n'
            'renderer/rendering_method.web="gl_compatibility"\n',
            "Compatibility renderer",
        )

    text = text.replace("anti_aliasing/quality/msaa_3d=2", "anti_aliasing/quality/msaa_3d=0")
    write(path, text)


def patch_settings() -> None:
    path = "scripts/services/settings.gd"
    text = read(path)

    replacements = {
        '\t"shadows" : true,': '\t"shadows" : false,',
        '\t"dec_shadows" : true,': '\t"dec_shadows" : false,',
        '\t"msaa": 2.0,': '\t"msaa": 0.0,',
        '\t"edge_pan": true,': '\t"edge_pan": false,',
        '\t"online_domain": "api.tof.p1x.in",': '\t"online_domain": "",',
        '\t"online_port": 443,': '\t"online_port": 0,',
        '\t"relay_domain": "api.tof.p1x.in",': '\t"relay_domain": "",',
        '\t"relay_port": 9959,': '\t"relay_port": 0,',
        '\t"render_scale": 100,': '\t"render_scale": 90,',
        '\t"tilt_shift_enabled": true': '\t"tilt_shift_enabled": false',
    }
    for old, new in replacements.items():
        if old not in text:
            raise RuntimeError(f"Settings anchor not found: {old}")
        text = text.replace(old, new, 1)

    old_ready = (
        "func _ready():\n"
        "\tself._detect_steam_deck()\n"
        "\tself.load_settings_from_file()\n"
    )
    new_ready = (
        "func _ready():\n"
        "\tself._detect_steam_deck()\n"
        "\tself.load_settings_from_file()\n"
        "\tself._apply_web_profile()\n"
        "\n"
        "func _apply_web_profile():\n"
        "\t# Portal build: deterministic browser-safe defaults.\n"
        "\t# Apply after loading saved settings so unsupported values cannot return.\n"
        "\tself.settings[\"shadows\"] = false\n"
        "\tself.settings[\"dec_shadows\"] = false\n"
        "\tself.settings[\"msaa\"] = 0.0\n"
        "\tself.settings[\"fxaa\"] = false\n"
        "\tself.settings[\"vsync\"] = false\n"
        "\tself.settings[\"fps\"] = 60.0\n"
        "\tself.settings[\"ips\"] = 60.0\n"
        "\tself.settings[\"edge_pan\"] = false\n"
        "\tself.settings[\"tilt_shift_enabled\"] = false\n"
        "\tself.settings[\"online_domain\"] = \"\"\n"
        "\tself.settings[\"online_port\"] = 0\n"
        "\tself.settings[\"relay_domain\"] = \"\"\n"
        "\tself.settings[\"relay_port\"] = 0\n"
        "\tfor key in [\"msaa\", \"fxaa\", \"vsync\", \"fps\", \"ips\", \"render_scale\"]:\n"
        "\t\tself._apply_option(key)\n"
    )
    text = replace_required(text, old_ready, new_ready, "web settings profile")

    old_set_option = "func set_option(key, value):\n\tself.settings[key] = value\n"
    new_set_option = (
        "func set_option(key, value):\n"
        "\t# Keep browser-incompatible values from being re-enabled at runtime.\n"
        "\tif key == \"tilt_shift_enabled\" or key == \"edge_pan\":\n"
        "\t\tvalue = false\n"
        "\telif key == \"fps\" or key == \"ips\":\n"
        "\t\tvalue = min(float(value), 60.0)\n"
        "\tself.settings[key] = value\n"
    )
    text = replace_required(text, old_set_option, new_set_option, "web settings guard")
    write(path, text)


def patch_menu() -> None:
    path = "scenes/ui/menu/menu.gd"
    text = read(path)
    old = (
        "func _ready():\n"
        "\tself.set_process_input(true)\n"
        "\tself.campaign_button.grab_focus()\n"
        "\n"
        "\tif OS.has_feature(\"demo\"):\n"
        "\t\tself.online_button.set_disabled(true)\n"
    )
    new = (
        "func _ready():\n"
        "\tself.set_process_input(true)\n"
        "\tself.campaign_button.grab_focus()\n"
        "\n"
        "\t# Portal fork is intentionally offline.\n"
        "\tself.online_button.hide()\n"
        "\tself.multiplayer_button.hide()\n"
        "\tif OS.has_feature(\"web\"):\n"
        "\t\tself.quit_button.hide()\n"
    )
    text = replace_required(text, old, new, "main menu offline mode")
    write(path, text)


def patch_settings_menu() -> None:
    path = "scenes/ui/menu/settings/settings.gd"
    text = read(path)
    controls_anchor = '@onready var controls_button = $"widgets/tabs/controls"\n'
    if '@onready var multiplayer_button = $"widgets/tabs/multiplayer"' not in text:
        text = replace_required(
            text,
            controls_anchor,
            controls_anchor + '@onready var multiplayer_button = $"widgets/tabs/multiplayer"\n',
            "multiplayer settings tab handle",
        )

    text = replace_required(
        text,
        "func _ready():\n\tself.set_process_input(false)\n",
        "func _ready():\n\tself.set_process_input(false)\n\tself.multiplayer_button.hide()\n",
        "hide multiplayer settings tab",
    )
    write(path, text)


def patch_network_settings() -> None:
    for path in (
        "scenes/ui/menu/settings/settings_multi.gd",
        "scenes/ui/menu/settings/settings_multi.tscn",
    ):
        text = read(path)
        text = text.replace("api.tof.p1x.in", "")
        text = text.replace("9959", "0")
        text = text.replace("9939", "0")
        text = text.replace("443", "0")
        write(path, text)


def write_offline_services() -> None:
    write("scripts/services/online.gd", '''extends Node

var thumb_cache: Dictionary = {}
var api_version: int = 0

func _ready() -> void:
\tset_process(false)

func is_integrated() -> bool:
\treturn false

func request_player_id() -> String:
\tawait get_tree().process_frame
\treturn "offline"

func clear_cache() -> void:
\tthumb_cache.clear()

func fetch_listing_chunk(_last_id: int) -> int:
\tawait get_tree().process_frame
\treturn 0

func fetch_top_downloads() -> int:
\tawait get_tree().process_frame
\treturn 0

func get_maps_page(_page_number: int, _page_size: int) -> Array:
\treturn []

func get_pages_count(_page_size: int) -> int:
\treturn 0

func fetch_thumbnail(map_code: String) -> Dictionary:
\tawait get_tree().process_frame
\treturn {"code": map_code, "image": null}

func upload_map(_map_name: String) -> String:
\tawait get_tree().process_frame
\treturn ""

func download_map(_map_code: String) -> bool:
\tawait get_tree().process_frame
\treturn false

func set_api_version(version: int) -> void:
\tapi_version = version
''')

    write("scripts/services/autodiscovery.gd", '''extends Node

signal scanned_server

var scanned_servers: Array = []
var is_scanning := false
var is_servering := false

func scan_lan_servers() -> void:
\tscanned_servers.clear()
\tis_scanning = false

func start_autodiscovery_server() -> void:
\tis_servering = false

func stop_autodiscovery_server() -> void:
\tis_servering = false

func abort_lan_scan() -> void:
\tis_scanning = false
''')

    write("scripts/services/multiplayer.gd", '''extends Node

signal connection_failed
signal connection_success
signal player_connected(peer_id, player_info)
signal player_disconnected(peer_id)
signal server_disconnected
signal all_players_loaded

var players: Dictionary = {}
var players_loaded: int = 0
var player_limit: int = 0
var selected_map: String = ""
var match_in_progress: bool = false
var match_state: Dictionary = {}
var match_state_available: bool = false

func create_game(_map_name: String) -> Error:
\treturn ERR_UNAVAILABLE

func connect_server(_ip_address: String, _port: int) -> Error:
\treturn ERR_UNAVAILABLE

func close_game() -> void:
\tplayers.clear()
\tplayers_loaded = 0
\tmatch_in_progress = false
\tmatch_state.clear()
\tmatch_state_available = false

func player_loaded() -> void:
\tpass

func _set_match_state(state: Dictionary) -> void:
\tmatch_state = state
\tmatch_state_available = true

func is_server() -> bool:
\treturn false
''')

    write("scripts/services/relay.gd", '''extends Node

signal connection_failed
signal connection_success
signal session_success
signal player_connected(peer_id: int, player_info: Dictionary)
signal player_disconnected(peer_id: int)
signal server_disconnected
signal all_players_loaded
signal message_received(message_data: Dictionary)

var players: Dictionary = {}
var players_loaded: int = 0
var player_limit: int = 0
var selected_map: String = ""
var match_in_progress: bool = false
var match_state: Dictionary = {}
var match_state_available: bool = false
var peer_id: int = 0
var join_code: String = ""
var connecting: bool = false

func is_server() -> bool:
\treturn false

func create_game(_map_name: String) -> Error:
\treturn ERR_UNAVAILABLE

func connect_game(_server_join_code: String) -> Error:
\treturn ERR_UNAVAILABLE

func close_game() -> void:
\tplayers.clear()
\tplayers_loaded = 0
\tmatch_in_progress = false
\tmatch_state.clear()
\tmatch_state_available = false
\tpeer_id = 0
\tjoin_code = ""
\tconnecting = false

func message_direct(_target_peer_id: int, _payload: Dictionary) -> Error:
\treturn ERR_UNAVAILABLE

func message_broadcast(_payload: Dictionary) -> Error:
\treturn ERR_UNAVAILABLE

func game_start() -> Error:
\treturn ERR_UNAVAILABLE

func player_loaded() -> void:
\tpass

func mark_player_loaded() -> void:
\tpass

func _set_match_state(state: Dictionary) -> void:
\tmatch_state = state
\tmatch_state_available = true
''')


def write_export_preset() -> None:
    write("export_presets.cfg", '''[preset.0]

name="Web Portal"
platform="Web"
runnable=true
advanced_options=false
dedicated_server=false
custom_features="portal_offline"
export_filter="all_resources"
include_filter=""
exclude_filter="docs/*,scripts/services/online/*"
export_path="build/web/index.html"
encryption_include_filters=""
encryption_exclude_filters=""
encrypt_pck=false
encrypt_directory=false
script_export_mode=2

[preset.0.options]

custom_template/debug=""
custom_template/release=""
variant/extensions_support=false
variant/thread_support=false
vram_texture_compression/for_desktop=true
vram_texture_compression/for_mobile=true
html/export_icon=true
html/custom_html_shell=""
html/head_include=""
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
html/experimental_virtual_keyboard=true
progressive_web_app/enabled=false
progressive_web_app/ensure_cross_origin_isolation_headers=false
progressive_web_app/offline_page=""
progressive_web_app/display=1
progressive_web_app/orientation=1
progressive_web_app/icon_144x144=""
progressive_web_app/icon_180x180=""
progressive_web_app/icon_512x512=""
progressive_web_app/background_color=Color(0, 0, 0, 1)
''')

    gitignore = read(".gitignore")
    if "!export_presets.cfg" not in gitignore:
        gitignore += "\n# Web portal fork tracks its reproducible export preset.\n!export_presets.cfg\n"
    write(".gitignore", gitignore)


def scan_for_blocked_networking() -> None:
    blocked = ["api.tof.p1x.in", "ws://", "PacketPeerUDP", "UDPServer", "ENetMultiplayerPeer"]
    findings = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(".git/") or rel.startswith("docs/"):
            continue
        if rel.startswith("scripts/services/online/") or rel == "tools/apply_web_port.py":
            continue
        if p.suffix.lower() not in {".gd", ".godot", ".tscn", ".tres", ".cfg", ".md", ".json", ".csv"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for needle in blocked:
            if needle in text:
                findings.append(f"{rel}: {needle}")

    if findings:
        raise RuntimeError(
            "Blocked network/runtime references remain outside excluded source:\n" + "\n".join(findings)
        )


def main() -> int:
    if not (ROOT / "project.godot").exists():
        print("Tanks of Freedom II upstream source has not been imported yet.", file=sys.stderr)
        return 2

    patch_project()
    patch_settings()
    patch_menu()
    patch_settings_menu()
    patch_network_settings()
    write_offline_services()
    write_export_preset()
    scan_for_blocked_networking()
    write("WEB_PORT_VERSION", "1\n")
    print("Applied Tanks of Freedom II Web Portal port v1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
