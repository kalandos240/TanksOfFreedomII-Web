extends Node

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
	if not OS.has_feature("web"):
		return

	# Yandex pause/resume must still be observed while the rest of the SceneTree
	# is paused by the platform.
	self.process_mode = Node.PROCESS_MODE_ALWAYS
	self.set_process(false)
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
			self.set_process(true)
			self._sync_platform_pause_state()
			return

		await self.get_tree().process_frame


func _process(_delta: float) -> void:
	self._sync_platform_pause_state()


func _sync_platform_pause_state() -> void:
	if not self.sdk_initialized:
		return

	# SDK events can arrive while Godot is still loading. The HTML bridge keeps
	# an ordered queue so an early pause followed by resume is not collapsed
	# into only the final boolean state before this autoload begins processing.
	var events_json = str(JavaScriptBridge.eval("(function(){var s=window.tofYandex;if(!s||!Array.isArray(s.platformEvents)){return '[]';}return JSON.stringify(s.platformEvents.splice(0,s.platformEvents.length));})()"))
	var events = JSON.parse_string(events_json)
	if typeof(events) == TYPE_ARRAY:
		for event in events:
			self._apply_platform_event(str(event))

	# Reconcile against the authoritative final state as a safety net in case a
	# browser/runtime drops the queue or the bridge is injected by an older page.
	var platform_paused = bool(JavaScriptBridge.eval("Boolean(window.tofYandex && window.tofYandex.platformPaused)"))
	if platform_paused != self._platform_paused:
		self._apply_platform_event("pause" if platform_paused else "resume")


func _apply_platform_event(event: String) -> void:
	if event == "pause":
		if self._platform_paused:
			return
		self._platform_paused = true
		self._pause_from_platform()
	elif event == "resume":
		if not self._platform_paused:
			return
		self._platform_paused = false
		self._resume_from_platform()


func _pause_from_platform() -> void:
	self._tree_was_paused = self.get_tree().paused

	var master_bus = AudioServer.get_bus_index("Master")
	if master_bus >= 0:
		self._master_bus_was_muted = AudioServer.is_bus_mute(master_bus)
		AudioServer.set_bus_mute(master_bus, true)

	var audio = self.get_node_or_null("/root/SimpleAudioLibrary")
	self._music_was_playing = false
	if audio != null:
		if audio.current_track != null:
			self._music_was_playing = audio.current_track.is_playing() and not audio.current_track.stream_paused
		audio.pause()
		for sample in audio.samples.values():
			sample.stop()

	if not self._tree_was_paused:
		self.get_tree().paused = true

	var tree_paused_literal = "true" if self.get_tree().paused else "false"
	JavaScriptBridge.eval("if (window.tofYandex) { window.tofYandex.godotPauseApplied = true; window.tofYandex.godotTreePausedAfterPause = %s; }" % tree_paused_literal)


func _resume_from_platform() -> void:
	if not self._tree_was_paused:
		self.get_tree().paused = false

	var audio = self.get_node_or_null("/root/SimpleAudioLibrary")
	if audio != null and self._music_was_playing and bool(Settings.get_option("music")):
		audio.unpause()
	self._music_was_playing = false

	var master_bus = AudioServer.get_bus_index("Master")
	if master_bus >= 0:
		AudioServer.set_bus_mute(master_bus, self._master_bus_was_muted)

	var tree_paused_literal = "true" if self.get_tree().paused else "false"
	JavaScriptBridge.eval("if (window.tofYandex) { window.tofYandex.godotResumeApplied = true; window.tofYandex.godotTreePausedAfterResume = %s; }" % tree_paused_literal)


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
