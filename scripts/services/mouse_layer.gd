extends Node

var initialized = false
var mouse_layer = Node3D.new()
var ground_points = {}
var mouse_collision_template = preload("res://scenes/tiles/ground/mouse_collision.tscn")

func initialize(size, tile_size):
	if self.initialized:
		return

	self.initialized = true
	var key
	for x in range(size):
		for y in range(size):
			key = str(x) + "_" + str(y)
			var ground_point = self.mouse_collision_template.instantiate()
			self.ground_points[key] = ground_point
			self.mouse_layer.add_child(ground_point)
			ground_point.mouse_entered.connect(ground_point._on_mouse_collision_mouse_entered)

			var point_position = ground_point.position
			point_position.x = x * tile_size
			point_position.z = y * tile_size
			ground_point.position = point_position


func detach():
	var parent = self.mouse_layer.get_parent()
	if parent != null:
		parent.remove_child(self.mouse_layer)

func destroy():
	self.mouse_layer.free()
