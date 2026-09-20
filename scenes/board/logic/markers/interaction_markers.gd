extends Node3D

@export var map: NodePath
var map_obj: Node

var attack_marker_template = preload("res://scenes/ui/markers/attack_marker.tscn")
var capture_marker_template = preload("res://scenes/ui/markers/capture_marker.tscn")

var created_markers = {}
var attack_marker_pool = []
var capture_marker_pool = []

func _ready():
	self.map_obj = self.get_node(self.map)
	if OS.has_feature("web"):
		self.call_deferred("_prewarm_marker_pools")

func _prewarm_marker_pools():
	const PREWARM_PER_TYPE = 4
	for i in PREWARM_PER_TYPE:
		var attack_marker = self.attack_marker_template.instantiate()
		attack_marker.set_meta("tof_pool_type", "attack")
		self.add_child(attack_marker)
		attack_marker.hide()
		self.attack_marker_pool.append(attack_marker)

		var capture_marker = self.capture_marker_template.instantiate()
		capture_marker.set_meta("tof_pool_type", "capture")
		self.add_child(capture_marker)
		capture_marker.hide()
		self.capture_marker_pool.append(capture_marker)

		await self.get_tree().process_frame

func reset():
	self.destroy_markers()

func destroy_markers():
	var marker
	for key in self.created_markers.keys():
		marker = self.created_markers[key]
		marker.hide()
		var pool_type = marker.get_meta("tof_pool_type", "")
		if pool_type == "attack":
			self.attack_marker_pool.append(marker)
		elif pool_type == "capture":
			self.capture_marker_pool.append(marker)
		else:
			marker.queue_free()
	self.created_markers = {}

func show_interaction_markers_for_tile(tile, ap_limit):
	self.reset()
	if not tile.unit.is_present() || ap_limit < 1:
		return

	var unit = tile.unit.tile
	var neighbour
	for key in tile.neighbours.keys():
		neighbour = tile.get_neighbour(key)

		if self.should_place_attack_marker(neighbour, unit):
			self.mark_tile_for_attack(neighbour)

		if self.should_place_catpure_marker(neighbour, unit):
			self.mark_tile_for_capture(neighbour)

func should_place_catpure_marker(tile, unit):
	if not tile.has_enemy_building(unit.side, unit.team):
		return false

	if unit.move < 1:
		return false

	if not unit.can_capture:
		return false

	return true

func mark_tile_for_capture(tile):
	self.place_marker("capture", self.capture_marker_template, tile)


func should_place_attack_marker(tile, unit):
	if not tile.has_enemy_unit(unit.side, unit.team):
		return false

	if unit.move < 1 || not unit.has_attacks():
		return false

	if not unit.can_attack(tile.unit.tile):
		return false

	return true


func mark_tile_for_attack(tile):
	self.place_marker("attack", self.attack_marker_template, tile)


func place_marker(pool_type, marker_template, tile):
	var pool = self.attack_marker_pool if pool_type == "attack" else self.capture_marker_pool
	var new_marker
	if pool.is_empty():
		new_marker = marker_template.instantiate()
		new_marker.set_meta("tof_pool_type", pool_type)
		self.add_child(new_marker)
	else:
		new_marker = pool.pop_back()
		new_marker.show()

	var placement = self.map_obj.map_to_local(tile.position)
	new_marker.set_position(placement)

	self.created_markers[str(tile.position.x) + "_" + str(tile.position.y)] = new_marker
