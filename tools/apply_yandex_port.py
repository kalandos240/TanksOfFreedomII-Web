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


def patch_project_autoload() -> None:
    path = "project.godot"
    text = read(path)
    anchor = 'Settings="*res://scripts/services/settings.gd"\n'
    addition = anchor + 'YandexBridge="*res://scripts/services/yandex.gd"\n'
    text = replace_once(text, anchor, addition, "YandexBridge autoload")
    write(path, text)


def write_yandex_bridge() -> None:
    write(
        "scripts/services/yandex.gd",
        '''extends Node

# Yandex Games SDK bridge for the Web portal build.
# Russian is intentionally enabled only after the complete RU translation lands.
const SDK_WAIT_FRAMES := 600
const SUPPORTED_AUTO_LOCALES := ["en", "pl"]

var sdk_initialized := false
var platform_language := ""
var game_ready_sent := false
var _platform_paused := false
var _tree_was_paused := false
var _master_bus_was_muted := false
var _music_was_playing := false


func _ready() -> void:
\tif not OS.has_feature("web"):
\t\treturn

\t# Yandex pause/resume must still be observed while the rest of the SceneTree
\t# is paused by the platform.
\tself.process_mode = Node.PROCESS_MODE_ALWAYS
\tself.set_process(false)
\tself.call_deferred("_wait_for_sdk")


func _wait_for_sdk() -> void:
\tfor _frame in range(SDK_WAIT_FRAMES):
\t\tvar failed = JavaScriptBridge.eval("Boolean(window.tofYandex && window.tofYandex.failed)")
\t\tif bool(failed):
\t\t\treturn

\t\tvar initialized = JavaScriptBridge.eval("Boolean(window.tofYandex && window.tofYandex.initialized)")
\t\tif bool(initialized):
\t\t\tself.sdk_initialized = true
\t\t\tself.platform_language = str(JavaScriptBridge.eval("(window.tofYandex && window.tofYandex.lang) || ''"))
\t\t\tself._apply_platform_language()
\t\t\tself.set_process(true)
\t\t\tself._sync_platform_pause_state()
\t\t\treturn

\t\tawait self.get_tree().process_frame


func _process(_delta: float) -> void:
\tself._sync_platform_pause_state()


func _sync_platform_pause_state() -> void:
\tif not self.sdk_initialized:
\t\treturn

\t# SDK events can arrive while Godot is still loading. The HTML bridge keeps
\t# an ordered queue so an early pause followed by resume is not collapsed
\t# into only the final boolean state before this autoload begins processing.
\tvar events_json = str(JavaScriptBridge.eval("(function(){var s=window.tofYandex;if(!s||!Array.isArray(s.platformEvents)){return '[]';}return JSON.stringify(s.platformEvents.splice(0,s.platformEvents.length));})()"))
\tvar events = JSON.parse_string(events_json)
\tif typeof(events) == TYPE_ARRAY:
\t\tfor event in events:
\t\t\tself._apply_platform_event(str(event))

\t# Reconcile against the authoritative final state as a safety net in case a
\t# browser/runtime drops the queue or the bridge is injected by an older page.
\tvar platform_paused = bool(JavaScriptBridge.eval("Boolean(window.tofYandex && window.tofYandex.platformPaused)"))
\tif platform_paused != self._platform_paused:
\t\tself._apply_platform_event("pause" if platform_paused else "resume")


func _apply_platform_event(event: String) -> void:
\tif event == "pause":
\t\tif self._platform_paused:
\t\t\treturn
\t\tself._platform_paused = true
\t\tself._pause_from_platform()
\telif event == "resume":
\t\tif not self._platform_paused:
\t\t\treturn
\t\tself._platform_paused = false
\t\tself._resume_from_platform()


func _pause_from_platform() -> void:
\tself._tree_was_paused = self.get_tree().paused

\tvar master_bus = AudioServer.get_bus_index("Master")
\tif master_bus >= 0:
\t\tself._master_bus_was_muted = AudioServer.is_bus_mute(master_bus)
\t\tAudioServer.set_bus_mute(master_bus, true)

\tvar audio = self.get_node_or_null("/root/SimpleAudioLibrary")
\tself._music_was_playing = false
\tif audio != null:
\t\tif audio.current_track != null:
\t\t\tself._music_was_playing = audio.current_track.is_playing() and not audio.current_track.stream_paused
\t\taudio.pause()
\t\tfor sample in audio.samples.values():
\t\t\tsample.stop()

\tif not self._tree_was_paused:
\t\tself.get_tree().paused = true

\tvar tree_paused_literal = "true" if self.get_tree().paused else "false"
\tJavaScriptBridge.eval("if (window.tofYandex) { window.tofYandex.godotPauseApplied = true; window.tofYandex.godotTreePausedAfterPause = %s; }" % tree_paused_literal)


func _resume_from_platform() -> void:
\tif not self._tree_was_paused:
\t\tself.get_tree().paused = false

\tvar audio = self.get_node_or_null("/root/SimpleAudioLibrary")
\tif audio != null and self._music_was_playing and bool(Settings.get_option("music")):
\t\taudio.unpause()
\tself._music_was_playing = false

\tvar master_bus = AudioServer.get_bus_index("Master")
\tif master_bus >= 0:
\t\tAudioServer.set_bus_mute(master_bus, self._master_bus_was_muted)

\tvar tree_paused_literal = "true" if self.get_tree().paused else "false"
\tJavaScriptBridge.eval("if (window.tofYandex) { window.tofYandex.godotResumeApplied = true; window.tofYandex.godotTreePausedAfterResume = %s; }" % tree_paused_literal)


func _apply_platform_language() -> void:
\tvar locale = self.platform_language.to_lower()
\tif locale.contains("-"):
\t\tlocale = locale.get_slice("-", 0)
\tif locale.contains("_"):
\t\tlocale = locale.get_slice("_", 0)

\tif not SUPPORTED_AUTO_LOCALES.has(locale):
\t\tlocale = "en"

\tSettings.set_option("locale", locale)


func game_ready() -> void:
\tif not OS.has_feature("web") or self.game_ready_sent:
\t\treturn

\tfor _frame in range(SDK_WAIT_FRAMES):
\t\tif self.sdk_initialized:
\t\t\tJavaScriptBridge.eval("window.tofYandex && window.tofYandex.markReady && window.tofYandex.markReady()")
\t\t\tself.game_ready_sent = true
\t\t\treturn
\t\tawait self.get_tree().process_frame
''',
    )


def patch_main_menu_ready() -> None:
    path = "scenes/main_menu/main_menu.gd"
    text = read(path)

    service_anchor = '@onready var multiplayer_srv = $"/root/Multiplayer"\n'
    service_addition = service_anchor + '@onready var yandex_bridge = $"/root/YandexBridge"\n'
    text = replace_once(text, service_anchor, service_addition, "main menu YandexBridge handle")

    ready_anchor = (
        '\tif self.match_setup.campaign_win:\n'
        '\t\tself.reopen_campaign_mission_selection_after_win()\n'
    )
    ready_addition = ready_anchor + '\n\tself.yandex_bridge.game_ready()\n'
    text = replace_once(text, ready_anchor, ready_addition, "Yandex LoadingAPI.ready hook")
    write(path, text)


def patch_export_head() -> None:
    path = "export_presets.cfg"
    text = read(path)

    head = '''<script src="/sdk.js"></script>
<script>
(function () {
  var state = window.tofYandex = {
    sdk: null,
    initialized: false,
    failed: false,
    lang: "",
    gameReadySent: false,
    platformPaused: false,
    platformEvents: [],
    godotPauseApplied: false,
    godotTreePausedAfterPause: null,
    godotResumeApplied: false,
    godotTreePausedAfterResume: null
  };

  state.markReady = function () {
    if (state.gameReadySent || !state.sdk) return;
    var features = state.sdk.features;
    var loading = features && features.LoadingAPI;
    if (loading && typeof loading.ready === "function") {
      loading.ready();
      state.gameReadySent = true;
    }
  };

  state.queuePlatformEvent = function (name) {
    state.platformEvents.push(name);
    if (state.platformEvents.length > 32) {
      state.platformEvents.shift();
    }
  };

  if (typeof YaGames === "undefined") {
    state.failed = true;
    return;
  }

  YaGames.init().then(function (ysdk) {
    state.sdk = ysdk;
    var i18n = ysdk.environment && ysdk.environment.i18n;
    state.lang = (i18n && i18n.lang) || "";

    if (typeof ysdk.on === "function") {
      ysdk.on("game_api_pause", function () {
        state.platformPaused = true;
        state.queuePlatformEvent("pause");
      });
      ysdk.on("game_api_resume", function () {
        state.platformPaused = false;
        state.queuePlatformEvent("resume");
      });
    }

    state.initialized = true;
  }).catch(function () {
    state.failed = true;
  });
})();
</script>
<style>
html, body { margin: 0; padding: 0; overflow: hidden; overscroll-behavior: none; user-select: none; -webkit-user-select: none; -webkit-touch-callout: none; }
canvas { touch-action: none; outline: none; }
</style>'''

    escaped = head.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    replacement = f'html/head_include="{escaped}"'
    text = replace_once(text, 'html/head_include=""', replacement, "Yandex SDK head include")
    write(path, text)


def patch_gitignore() -> None:
    path = ".gitignore"
    text = read(path)
    marker = "# Generated Python bytecode\n__pycache__/\n*.py[cod]\n"
    if marker not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + marker
    write(path, text)


def main() -> None:
    patch_project_autoload()
    write_yandex_bridge()
    patch_main_menu_ready()
    patch_export_head()
    patch_gitignore()
    print("Applied Yandex Games SDK integration patch.")


if __name__ == "__main__":
    main()
