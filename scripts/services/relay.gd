extends Node

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
	return false

func create_game(_map_name: String) -> Error:
	return ERR_UNAVAILABLE

func connect_game(_server_join_code: String) -> Error:
	return ERR_UNAVAILABLE

func close_game() -> void:
	players.clear()
	players_loaded = 0
	match_in_progress = false
	match_state.clear()
	match_state_available = false
	peer_id = 0
	join_code = ""
	connecting = false

func message_direct(_target_peer_id: int, _payload: Dictionary) -> Error:
	return ERR_UNAVAILABLE

func message_broadcast(_payload: Dictionary) -> Error:
	return ERR_UNAVAILABLE

func game_start() -> Error:
	return ERR_UNAVAILABLE

func player_loaded() -> void:
	pass

func mark_player_loaded() -> void:
	pass

func _set_match_state(state: Dictionary) -> void:
	match_state = state
	match_state_available = true
