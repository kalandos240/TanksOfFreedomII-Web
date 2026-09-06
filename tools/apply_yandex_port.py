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


func _ready() -> void:
\tif not OS.has_feature("web"):
\t\treturn
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
\t\t\treturn

\t\tawait self.get_tree().process_frame


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

    head = r'''<script src="/sdk.js"></script>
<script>
(function () {
  var state = window.tofYandex = {
    sdk: null,
    initialized: false,
    failed: false,
    lang: "",
    gameReadySent: false
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

  if (typeof YaGames === "undefined") {
    state.failed = true;
    return;
  }

  YaGames.init().then(function (ysdk) {
    state.sdk = ysdk;
    var i18n = ysdk.environment && ysdk.environment.i18n;
    state.lang = (i18n && i18n.lang) || "";
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
