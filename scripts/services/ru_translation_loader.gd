extends Node

# Godot imports *.csv files as translation resources, so FileAccess cannot rely
# on the original CSV path being present inside an exported PCK. Web builds copy
# the same source text to *.runtime.txt; editor/dev runs can still fall back to
# the source CSV files.
const RU_TRANSLATION_FILES := [
	[
		"res://assets/translations/common.ru.runtime.txt",
		"res://assets/translations/common.ru.csv",
	],
	[
		"res://assets/translations/core.ru.runtime.txt",
		"res://assets/translations/core.ru.csv",
	],
]


func _ready() -> void:
	var translation := Translation.new()
	translation.locale = "ru"

	var loaded_messages := 0
	for candidates in RU_TRANSLATION_FILES:
		loaded_messages += _append_csv_translation(translation, _find_translation_source(candidates))

	if loaded_messages == 0:
		push_error("Russian translation runtime loaded no messages.")
		return

	TranslationServer.add_translation(translation)


func _find_translation_source(candidates: Array) -> String:
	for candidate in candidates:
		var path := str(candidate)
		if FileAccess.file_exists(path):
			return path
	return str(candidates[0])


func _append_csv_translation(translation: Translation, path: String) -> int:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Cannot open Russian translation source: %s" % path)
		return 0

	if file.eof_reached():
		push_error("Russian translation source is empty: %s" % path)
		return 0

	var header := file.get_csv_line()
	var key_index := header.find("keys")
	var ru_index := header.find("ru")
	if key_index < 0 or ru_index < 0:
		push_error("Russian translation CSV has invalid header: %s" % path)
		return 0

	var loaded := 0
	while not file.eof_reached():
		var row := file.get_csv_line()
		if row.size() <= max(key_index, ru_index):
			continue

		var key := row[key_index].strip_edges()
		if key.is_empty():
			continue

		translation.add_message(key, row[ru_index])
		loaded += 1

	return loaded
