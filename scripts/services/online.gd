extends Node

var thumb_cache: Dictionary = {}
var api_version: int = 0

func _ready() -> void:
	set_process(false)

func is_integrated() -> bool:
	return false

func request_player_id() -> String:
	await get_tree().process_frame
	return "offline"

func clear_cache() -> void:
	thumb_cache.clear()

func fetch_listing_chunk(_last_id: int) -> int:
	await get_tree().process_frame
	return 0

func fetch_top_downloads() -> int:
	await get_tree().process_frame
	return 0

func get_maps_page(_page_number: int, _page_size: int) -> Array:
	return []

func get_pages_count(_page_size: int) -> int:
	return 0

func fetch_thumbnail(map_code: String) -> Dictionary:
	await get_tree().process_frame
	return {"code": map_code, "image": null}

func upload_map(_map_name: String) -> String:
	await get_tree().process_frame
	return ""

func download_map(_map_code: String) -> bool:
	await get_tree().process_frame
	return false

func set_api_version(version: int) -> void:
	api_version = version
