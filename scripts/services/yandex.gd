extends Node

# Yandex Games SDK bridge for the Web portal build.
# Russian is intentionally enabled only after the complete RU translation lands.
const SDK_WAIT_FRAMES := 600
const SUPPORTED_AUTO_LOCALES := ["en", "pl"]

var sdk_initialized := false
var platform_language := ""
var game_ready_sent := false


func _ready() -> void:
	if not OS.has_feature("web"):
		return
	self.call_deferred("_wait_for_sdk")


func _wait_for_sdk() -> void:
	for _frame in range(SDK_WAIT_FRAMES):
		var failed = JavaScriptBridge.eval("Boolean(window.tofYandex && window.tofYandex.failed)")
		if bool(failed):
			return

		var initialized = JavaScriptBridge.eval("Boolean(window.tofYandex && window.tofYandex.initialized)")
		if bool(initialized):
			self.sdk_initialized = true
			self.platform_language = str(JavaScriptBridge.eval("(window.tofYandex && window.tofYandex.lang) || ''"))
			self._apply_platform_language()
			return

		await self.get_tree().process_frame


func _apply_platform_language() -> void:
	var locale = self.platform_language.to_lower()
	if locale.contains("-"):
		locale = locale.get_slice("-", 0)
	if locale.contains("_"):
		locale = locale.get_slice("_", 0)

	if not SUPPORTED_AUTO_LOCALES.has(locale):
		locale = "en"

	Settings.set_option("locale", locale)


func game_ready() -> void:
	if not OS.has_feature("web") or self.game_ready_sent:
		return

	for _frame in range(SDK_WAIT_FRAMES):
		if self.sdk_initialized:
			JavaScriptBridge.eval("window.tofYandex && window.tofYandex.markReady && window.tofYandex.markReady()")
			self.game_ready_sent = true
			return
		await self.get_tree().process_frame
