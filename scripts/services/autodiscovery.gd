extends Node

signal scanned_server

var scanned_servers: Array = []
var is_scanning := false
var is_servering := false

func scan_lan_servers() -> void:
	scanned_servers.clear()
	is_scanning = false

func start_autodiscovery_server() -> void:
	is_servering = false

func stop_autodiscovery_server() -> void:
	is_servering = false

func abort_lan_scan() -> void:
	is_scanning = false
