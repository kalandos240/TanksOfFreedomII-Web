
const SIZE = 40

var tile_template = preload("res://scenes/map/tile.gd")

var tiles = {}
var tile_list = []
var tile_grid = []
var scripts = {
	"stories" : {},
	"triggers" : {}
}
var metadata = {}

func _init():
	for x in range(self.SIZE):
		var column = []
		self.tile_grid.append(column)
		for y in range(self.SIZE):
			var tile = self.tile_template.new(x, y)
			self.tiles[str(x) + "_" + str(y)] = tile
			self.tile_list.append(tile)
			column.append(tile)
	self.connect_neightbours()

func wipe_metadata():
	self.metadata.clear()

func wipe_scripts():
	self.scripts["stories"].clear()
	self.scripts["triggers"].clear()

func get_tile(position: Vector2i):
	if position.x < 0 or position.x >= self.SIZE or position.y < 0 or position.y >= self.SIZE:
		return null
	return self.tile_grid[position.x][position.y]

func get_tile2(x, y):
	return self.tile_grid[int(x)][int(y)]

func get_dict():
	var tiles_dict = {}
	for tile in self.tile_list:
		if tile.has_content():
			tiles_dict[tile.cache_key] = tile.get_dict()

	return {
		"metadata" : self.metadata,
		"tiles" : tiles_dict,
		"scripts" : self.scripts
	}

func connect_neightbours():
	var tile

	for x in range(self.SIZE):
		for y in range(self.SIZE):

			tile = self.get_tile2(x, y)

			if x > 0:
				tile.add_neighbour(tile.WEST, self.get_tile2(x-1, y))

			if x < self.SIZE - 1:
				tile.add_neighbour(tile.EAST, self.get_tile2(x+1, y))

			if y > 0:
				tile.add_neighbour(tile.NORTH, self.get_tile2(x, y-1))

			if y < self.SIZE - 1:
				tile.add_neighbour(tile.SOUTH, self.get_tile2(x, y+1))


func get_player_units(side):
	var units = []
	for tile in self.tile_list:
		if tile.has_friendly_unit(side):
			units.append(tile.unit.tile)

	return units

func get_all_units_tiles():
	var units_tiles = []
	for tile in self.tile_list:
		if tile.unit.is_present():
			units_tiles.append(tile)

	return units_tiles


func get_player_buildings(side):
	var buildings = []
	for tile in self.tile_list:
		if tile.has_friendly_building(side):
			buildings.append(tile.building.tile)

	return buildings

func get_player_units_tiles(side):
	var units = []
	for tile in self.tile_list:
		if tile.has_friendly_unit(side):
			units.append(tile)

	return units

func get_player_buildings_tiles(side):
	var buildings = []
	for tile in self.tile_list:
		if tile.has_friendly_building(side):
			buildings.append(tile)

	return buildings

func get_enemy_units_tiles(side, team=null):
	var units = []
	for tile in self.tile_list:
		if tile.has_enemy_unit(side, team):
			units.append(tile)

	return units

func get_enemy_buildings_tiles(side, team=null):
	var buildings = []
	for tile in self.tile_list:
		if tile.has_enemy_building(side, team):
			buildings.append(tile)

	return buildings

func get_ai_entity_snapshot(side, team=null):
	var snapshot = {
		"own_buildings": [],
		"own_units": [],
		"enemy_buildings": [],
		"enemy_units": [],
	}

	for tile in self.tile_list:
		if tile.unit.is_present():
			if tile.unit.tile.side == side:
				snapshot["own_units"].append(tile)
			elif team == null or tile.unit.tile.team != team:
				snapshot["enemy_units"].append(tile)

		if tile.building.is_present():
			if tile.building.tile.side == side:
				snapshot["own_buildings"].append(tile)
			elif team == null or tile.building.tile.team != team:
				snapshot["enemy_buildings"].append(tile)

	return snapshot

func ingest_scripts(incoming_scripts):
	if incoming_scripts == null or incoming_scripts.is_empty():
		return

	self.scripts = incoming_scripts

func get_player_bunker_position(side):
	for tile in self.tile_list:
		if tile.has_friendly_hq(side):
			return tile.position

	return null

func get_player_bunkers(side):
	var bunkers = []

	for tile in self.tile_list:
		if tile.has_friendly_hq(side):
			bunkers.append(tile)

	return bunkers

func get_player_hero_position(side):
	for tile in self.tile_list:
		if tile.has_friendly_hero(side):
			return tile.position

	return null

func get_player_heroes(side):
	var heroes = []

	for tile in self.tile_list:
		if tile.has_friendly_hero(side):
			heroes.append(tile.unit.tile)

	return heroes

func get_unit_position(unit):
	if unit == null:
		return null

	for tile in self.tile_list:
		if tile.unit.tile == unit:
			return [tile.position.x, tile.position.y]

	return null

func wipe_all_units():
	var units = []
	for tile in self.tile_list:
		if tile.unit.is_present():
			tile.unit.clear()

	return units
