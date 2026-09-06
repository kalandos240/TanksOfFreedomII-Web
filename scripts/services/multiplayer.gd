extends Node

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
	return ERR_UNAVAILABLE

func connect_server(_ip_address: String, _port: int) -> Error:
	return ERR_UNAVAILABLE

func close_game() -> void:
	players.clear()
	players_loaded = 0
	match_in_progress = false
	match_state.clear()
	match_state_available = false

func player_loaded() -> void:
	pass

func _set_match_state(state: Dictionary) -> void:
	match_state = state
	match_state_available = true

func is_server() -> bool:
	return false
