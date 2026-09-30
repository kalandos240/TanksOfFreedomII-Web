#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "scenes/board/board.gd"
MOVEMENT_MARKERS = ROOT / "scenes/board/logic/markers/movement_markers.gd"
PATH_MARKERS = ROOT / "scenes/board/logic/markers/path_markers.gd"
INTERACTION_MARKERS = ROOT / "scenes/board/logic/markers/interaction_markers.gd"
MAP_TILE = ROOT / "scenes/map/tile.gd"
AI_PATHFINDER = ROOT / "scenes/board/logic/ai/pathfinder.gd"
AI_COLLECTOR = ROOT / "scenes/board/logic/ai/collector.gd"
AI_UNIT_BRAIN = ROOT / "scenes/board/logic/ai/brains/abstract_unit_brain.gd"
MAP_MODEL = ROOT / "scenes/map/model.gd"
UNIT_SCRIPT = ROOT / "scenes/tiles/units/unit.gd"
CAMERA = ROOT / "scenes/camera.gd"
MAP_SCENE = ROOT / "scenes/map/map.gd"
EXPLOSION_SCRIPT = ROOT / "scenes/fx/explosion.gd"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            print(f"{label}: already patched")
            return
        raise RuntimeError(f"{label}: expected source block not found in {path}")

    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one source block in {path}")

    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"{label}: patched")


def patch_board_hover() -> None:
    replace_once(
        BOARD,
        '''\t\tif tile != self.last_hover_tile or true:
\t\t\tself.last_hover_tile = tile

\t\t\tself.update_tile_highlight(tile)

\t\t\tself.path_markers.reset()
\t\t\tif self.should_draw_move_path(tile):
\t\t\t\tvar path = self.movement_markers.get_path_to_tile(tile)
\t\t\t\tself.path_markers.draw_path(path)
''',
        '''\t\tif tile != self.last_hover_tile:
\t\t\tself.last_hover_tile = tile

\t\t\tself.update_tile_highlight(tile)

\t\t\tif self.should_draw_move_path(tile):
\t\t\t\tvar path = self.movement_markers.get_path_to_tile(tile)
\t\t\t\tself.path_markers.draw_path(path)
\t\t\telse:
\t\t\t\tself.path_markers.reset()
''',
        "Board hover/path repeat guard",
    )



def patch_board_fx_prewarm() -> None:
    replace_once(
        BOARD,
        '''func _ready():
\tself.set_up_ui()
\tself.set_up_map()
\tself.set_up_board()
\t_ready_start()
''',
        '''func _ready():
\tself.set_up_ui()
\tself.set_up_map()
\tself.set_up_board()
\tif OS.has_feature("web"):
\t\tself.call_deferred("_prewarm_web_fx")
\t_ready_start()

func _prewarm_web_fx():
\tvar prewarm_explosion = self.explosion_template.instantiate()
\tself.explosion_anchor.add_child(prewarm_explosion)
\tprewarm_explosion.hide()
\tawait self.get_tree().process_frame
\tprewarm_explosion.queue_free()

\tvar prewarm_projectile = self.projectile_template.instantiate()
\tself.explosion_anchor.add_child(prewarm_projectile)
\tprewarm_projectile.hide()
\tawait self.get_tree().process_frame
\tprewarm_projectile.queue_free()
''',
        "Board Web FX prewarm",
    )


def patch_cached_tile_keys() -> None:
    replace_once(
        MAP_TILE,
        'var position = Vector2i(0, 0)\n',
        'var position = Vector2i(0, 0)\nvar cache_key = ""\n',
        "Map tile cached key state",
    )

    replace_once(
        MAP_TILE,
        '''func _init(x, y):
\tself.position.x = x
\tself.position.y = y
''',
        '''func _init(x, y):
\tself.position.x = x
\tself.position.y = y
\tself.cache_key = str(x) + "_" + str(y)
''',
        "Map tile cached key initialization",
    )

    replace_once(
        MOVEMENT_MARKERS,
        '''func _get_key(tile):
\treturn str(tile.position.x) + "_" + str(tile.position.y)
''',
        '''func _get_key(tile):
\treturn tile.cache_key
''',
        "Movement marker cached tile keys",
    )

    replace_once(
        AI_PATHFINDER,
        '''func _get_key(tile):
\treturn str(tile.position.x) + "_" + str(tile.position.y)
''',
        '''func _get_key(tile):
\treturn tile.cache_key
''',
        "AI pathfinder cached tile keys",
    )



def patch_ai_entity_snapshot() -> None:
    replace_once(
        MAP_MODEL,
        '''var tiles = {}
var scripts = {
''',
        '''var tiles = {}
var tile_list = []
var scripts = {
''',
        "Map model flat tile list state",
    )

    replace_once(
        MAP_MODEL,
        '''func _init():
\tfor x in range(self.SIZE):
\t\tfor y in range(self.SIZE):
\t\t\tself.tiles[str(x) + "_" + str(y)] = self.tile_template.new(x, y)
\tself.connect_neightbours()
''',
        '''func _init():
\tfor x in range(self.SIZE):
\t\tfor y in range(self.SIZE):
\t\t\tvar tile = self.tile_template.new(x, y)
\t\t\tself.tiles[str(x) + "_" + str(y)] = tile
\t\t\tself.tile_list.append(tile)
\tself.connect_neightbours()
''',
        "Map model flat tile list initialization",
    )

    replace_once(
        MAP_MODEL,
        '''func get_enemy_buildings_tiles(side, team=null):
\tvar buildings = []
\tfor i in self.tiles.keys():
\t\tif self.tiles[i].has_enemy_building(side, team):
\t\t\tbuildings.append(self.tiles[i])

\treturn buildings

func ingest_scripts(incoming_scripts):
''',
        '''func get_enemy_buildings_tiles(side, team=null):
\tvar buildings = []
\tfor i in self.tiles.keys():
\t\tif self.tiles[i].has_enemy_building(side, team):
\t\t\tbuildings.append(self.tiles[i])

\treturn buildings

func get_ai_entity_snapshot(side, team=null):
\tvar snapshot = {
\t\t"own_buildings": [],
\t\t"own_units": [],
\t\t"enemy_buildings": [],
\t\t"enemy_units": [],
\t}

\tfor tile in self.tile_list:
\t\tif tile.unit.is_present():
\t\t\tif tile.unit.tile.side == side:
\t\t\t\tsnapshot["own_units"].append(tile)
\t\t\telif team == null or tile.unit.tile.team != team:
\t\t\t\tsnapshot["enemy_units"].append(tile)

\t\tif tile.building.is_present():
\t\t\tif tile.building.tile.side == side:
\t\t\t\tsnapshot["own_buildings"].append(tile)
\t\t\telif team == null or tile.building.tile.team != team:
\t\t\t\tsnapshot["enemy_buildings"].append(tile)

\treturn snapshot

func ingest_scripts(incoming_scripts):
''',
        "Map model single-pass AI entity snapshot",
    )

    replace_once(
        AI_COLLECTOR,
        '''\tvar buildings = self.board.map.model.get_player_buildings_tiles(side)
\tvar units = self.board.map.model.get_player_units_tiles(side)

\t#if OS.is_debug_build():
\t#\tprint("Units: " + str(units.size()))
\t#\tprint("Buildings: " + str(buildings.size()))

\tvar enemy_buildings = self.board.map.model.get_enemy_buildings_tiles(side, team)
\tvar enemy_units = self.board.map.model.get_enemy_units_tiles(side, team)
''',
        '''\tvar entity_snapshot = self.board.map.model.get_ai_entity_snapshot(side, team)
\tvar buildings = entity_snapshot["own_buildings"]
\tvar units = entity_snapshot["own_units"]

\t#if OS.is_debug_build():
\t#\tprint("Units: " + str(units.size()))
\t#\tprint("Buildings: " + str(buildings.size()))

\tvar enemy_buildings = entity_snapshot["enemy_buildings"]
\tvar enemy_units = entity_snapshot["enemy_units"]
''',
        "AI collector single map scan",
    )


def patch_neighbour_iteration() -> None:
    replace_once(
        MAP_TILE,
        '''var neighbours = {}
''',
        '''var neighbours = {}
var neighbour_tiles = []
''',
        "Map tile neighbour array state",
    )

    replace_once(
        MAP_TILE,
        '''func add_neighbour(direction, tile):
\tself.neighbours[direction] = tile
''',
        '''func add_neighbour(direction, tile):
\tself.neighbours[direction] = tile
\tself.neighbour_tiles.append(tile)
''',
        "Map tile neighbour array population",
    )

    replace_once(
        MAP_TILE,
        '''func is_neighbour(tile):
\tfor direction in self.neighbours.keys():
\t\tif self.neighbours[direction] == tile:
\t\t\treturn true
\treturn false
''',
        '''func is_neighbour(tile):
\treturn tile in self.neighbour_tiles
''',
        "Map tile allocation-free neighbour lookup",
    )

    replace_once(
        MAP_TILE,
        '''func neighbours_enemy_unit(side, team=null):
\tfor direction in self.neighbours.keys():
\t\tif self.neighbours[direction].has_enemy_unit(side, team):
\t\t\treturn true
\treturn false
''',
        '''func neighbours_enemy_unit(side, team=null):
\tfor neighbour in self.neighbour_tiles:
\t\tif neighbour.has_enemy_unit(side, team):
\t\t\treturn true
\treturn false
''',
        "Map tile enemy-unit neighbour iteration",
    )

    replace_once(
        MAP_TILE,
        '''func can_attack_neightbour_enemy_unit(attacking_unit):
\tfor direction in self.neighbours.keys():
\t\tif self.neighbours[direction].has_enemy_unit(attacking_unit.side, attacking_unit.team):
\t\t\tif attacking_unit.can_attack(self.neighbours[direction].unit.tile):
\t\t\t\treturn true
\treturn false
''',
        '''func can_attack_neightbour_enemy_unit(attacking_unit):
\tfor neighbour in self.neighbour_tiles:
\t\tif neighbour.has_enemy_unit(attacking_unit.side, attacking_unit.team):
\t\t\tif attacking_unit.can_attack(neighbour.unit.tile):
\t\t\t\treturn true
\treturn false
''',
        "Map tile attack neighbour iteration",
    )

    replace_once(
        MAP_TILE,
        '''func neighbours_enemy_building(side, team=null):
\tfor direction in self.neighbours.keys():
\t\tif self.neighbours[direction].has_enemy_building(side, team):
\t\t\treturn true
\treturn false
''',
        '''func neighbours_enemy_building(side, team=null):
\tfor neighbour in self.neighbour_tiles:
\t\tif neighbour.has_enemy_building(side, team):
\t\t\treturn true
\treturn false
''',
        "Map tile enemy-building neighbour iteration",
    )

    replace_once(
        AI_PATHFINDER,
        '''\tfor key in tile.neighbours.keys():
\t\tneighbour = tile.get_neighbour(key)

\t\tneighbour_cost = self.get_tile_cost(neighbour)
''',
        '''\tfor neighbour_tile in tile.neighbour_tiles:
\t\tneighbour = neighbour_tile

\t\tneighbour_cost = self.get_tile_cost(neighbour)
''',
        "AI pathfinder allocation-free neighbour iteration",
    )

    replace_once(
        AI_UNIT_BRAIN,
        '''func _get_interaction_tiles(tile, source_tile):
\tvar tiles = []
\tfor neighbour in tile.neighbours:
\t\tif not tile.neighbours[neighbour].can_acommodate_unit(source_tile.unit.tile):
\t\t\tcontinue
\t\tif not self.pathfinder.is_tile_reachable(tile.neighbours[neighbour]):
\t\t\tcontinue

\t\ttiles.append(tile.neighbours[neighbour])

\treturn tiles
''',
        '''func _get_interaction_tiles(tile, source_tile):
\tvar tiles = []
\tfor neighbour in tile.neighbour_tiles:
\t\tif not neighbour.can_acommodate_unit(source_tile.unit.tile):
\t\t\tcontinue
\t\tif not self.pathfinder.is_tile_reachable(neighbour):
\t\t\tcontinue

\t\ttiles.append(neighbour)

\treturn tiles
''',
        "AI interaction allocation-free neighbour iteration",
    )


def patch_hot_dictionary_reuse() -> None:
    replace_once(
        AI_PATHFINDER,
        '''func reset():
\tself.visited_tiles = {}
\tself.explored_tiles = {}
\tself.tile_path = {}
\tself.enemy_units = {}
\tself.enemy_buildings = {}
\tself.own_units = {}
\tself.own_buildings = {}
\tself.allied_units = {}
\tself.allied_buildings = {}
''',
        '''func reset():
\tself.visited_tiles.clear()
\tself.explored_tiles.clear()
\tself.tile_path.clear()
\tself.enemy_units.clear()
\tself.enemy_buildings.clear()
\tself.own_units.clear()
\tself.own_buildings.clear()
\tself.allied_units.clear()
\tself.allied_buildings.clear()
''',
        "AI pathfinder dictionary reuse",
    )


def patch_ai_path_cache() -> None:
    replace_once(
        AI_PATHFINDER,
        '''var visited_tiles = {}
var explored_tiles = {}
var tile_path = {}
''',
        '''var visited_tiles = {}
var explored_tiles = {}
var tile_path = {}
var path_cache = {}
''',
        "AI pathfinder path cache state",
    )

    replace_once(
        AI_PATHFINDER,
        '''func reset():
\tself.visited_tiles.clear()
\tself.explored_tiles.clear()
\tself.tile_path.clear()
\tself.enemy_units.clear()
''',
        '''func reset():
\tself.visited_tiles.clear()
\tself.explored_tiles.clear()
\tself.tile_path.clear()
\tself.path_cache.clear()
\tself.enemy_units.clear()
''',
        "AI pathfinder path cache reset",
    )

    replace_once(
        AI_PATHFINDER,
        '''func get_path_to_tile(destination_tile):
\tvar path = []
\tvar key = self._get_key(destination_tile)

\twhile key != null:
\t\tpath.append(key)
\t\tif not self.tile_path.has(key):
\t\t\treturn []
\t\tkey = self.tile_path[key]

\treturn path
''',
        '''func get_path_to_tile(destination_tile):
\tvar destination_key = self._get_key(destination_tile)
\tif self.path_cache.has(destination_key):
\t\treturn self.path_cache[destination_key]

\tvar path = []
\tvar key = destination_key

\twhile key != null:
\t\tpath.append(key)
\t\tif not self.tile_path.has(key):
\t\t\tself.path_cache[destination_key] = []
\t\t\treturn self.path_cache[destination_key]
\t\tkey = self.tile_path[key]

\tself.path_cache[destination_key] = path
\treturn path
''',
        "AI pathfinder reconstructed path cache",
    )


def patch_unit_hot_stat_reads() -> None:
    replace_once(
        UNIT_SCRIPT,
        '''func get_move():
\tvar stats = self.get_stats_with_modifiers()
\treturn stats["move"]
''',
        '''func get_move():
\treturn self.move + self.modifiers.get("move", 0)
''',
        "Unit move stat allocation-free read",
    )

    replace_once(
        UNIT_SCRIPT,
        '''func get_attack():
\tvar stats = self.get_stats_with_modifiers()
\treturn stats["attack"]
''',
        '''func get_attack():
\treturn self.attack + self.modifiers.get("attack", 0)
''',
        "Unit attack stat allocation-free read",
    )

    replace_once(
        UNIT_SCRIPT,
        '''func get_armor():
\tvar stats = self.get_stats_with_modifiers()
\treturn stats["armor"]
''',
        '''func get_armor():
\tvar value = self.armor + self.modifiers.get("armor", 0)
\tif self.level > 1:
\t\tvalue += 1
\treturn value
''',
        "Unit armor stat allocation-free read",
    )

    replace_once(
        AI_UNIT_BRAIN,
        '''\tif entity_tile.unit.tile.can_kill(target_tile.unit.tile):
\t\tvalue += 100
\telse:
\t\tif target_tile.unit.tile.can_retaliate(entity_tile.unit.tile):
\t\t\tvalue -= 10
\t\tif target_tile.unit.tile.can_retaliate(entity_tile.unit.tile) and target_tile.unit.tile.has_enough_power_to_kill(entity_tile.unit.tile):
\t\t\tvalue -= self.counter_death_penalty
''',
        '''\tif entity_tile.unit.tile.can_kill(target_tile.unit.tile):
\t\tvalue += 100
\telse:
\t\tvar can_retaliate = target_tile.unit.tile.can_retaliate(entity_tile.unit.tile)
\t\tif can_retaliate:
\t\t\tvalue -= 10
\t\tif can_retaliate and target_tile.unit.tile.has_enough_power_to_kill(entity_tile.unit.tile):
\t\t\tvalue -= self.counter_death_penalty
''',
        "AI retaliation duplicate check removal",
    )



def patch_idle_transform_updates() -> None:
    replace_once(
        CAMERA,
        '''var shakes_left = 0
var last_shake_time = 0
''',
        '''var shakes_left = 0
var last_shake_time = 0
var shake_needs_reset = false
''',
        "Camera shake idle state",
    )

    replace_once(
        CAMERA,
        '''func shake():
\tself.shakes_left = 3
\tself.last_shake_time = 900.0

func _perform_shake(delta):
\tvar shake_offset = Vector2(0, 0)
\tself.last_shake_time += delta

\tif self.last_shake_time > 0.04:
\t\tself.last_shake_time = 0.0
\t\tif self.shakes_left > 0:
\t\t\tself.shakes_left -= 1
\t\t\tshake_offset.x = self.SHAKE_MAX_MAGNITUDE * randf_range(-1, 1)
\t\t\tshake_offset.y = self.SHAKE_MAX_MAGNITUDE * randf_range(-1, 1)

\t\tself._set_camera_translation(self.camera_lens, shake_offset)
\t\tself._set_camera_translation(self.camera_tof, shake_offset)
\t\tself._set_camera_translation(self.camera_aw, shake_offset)
''',
        '''func shake():
\tself.shakes_left = 3
\tself.last_shake_time = 900.0
\tself.shake_needs_reset = true

func _perform_shake(delta):
\tif self.shakes_left <= 0 and not self.shake_needs_reset:
\t\treturn

\tvar shake_offset = Vector2(0, 0)
\tself.last_shake_time += delta

\tif self.last_shake_time > 0.04:
\t\tself.last_shake_time = 0.0
\t\tif self.shakes_left > 0:
\t\t\tself.shakes_left -= 1
\t\t\tshake_offset.x = self.SHAKE_MAX_MAGNITUDE * randf_range(-1, 1)
\t\t\tshake_offset.y = self.SHAKE_MAX_MAGNITUDE * randf_range(-1, 1)
\t\telse:
\t\t\tself.shake_needs_reset = false

\t\tself._set_camera_translation(self.camera_lens, shake_offset)
\t\tself._set_camera_translation(self.camera_tof, shake_offset)
\t\tself._set_camera_translation(self.camera_aw, shake_offset)
''',
        "Camera shake idle transform suppression",
    )

    replace_once(
        MAP_SCENE,
        '''func snap_tile_box():
\tvar box_position = self.tile_box.get_position()
\tvar placement = self.map_to_local(self.tile_box_position)

\tplacement.y = box_position.y

\tself.tile_box.set_position(placement)
''',
        '''func snap_tile_box():
\tvar box_position = self.tile_box.get_position()
\tvar placement = self.map_to_local(self.tile_box_position)

\tplacement.y = box_position.y
\tif box_position == placement:
\t\treturn

\tself.tile_box.set_position(placement)
''',
        "Map tile-box redundant transform suppression",
    )



def patch_healthbar_viewport_updates() -> None:
    replace_once(
        UNIT_SCRIPT,
        '''var enable_healthbar = false
@onready var healthbar_sprite = $"mesh_anchor/healthbar"
''',
        '''var enable_healthbar = false
@onready var healthbar_sprite = $"mesh_anchor/healthbar"
@onready var healthbar_viewport = $"mesh_anchor/healthbar/SubViewport"
''',
        "Unit healthbar viewport handle",
    )

    replace_once(
        UNIT_SCRIPT,
        '''func _ready():
\tself.animations.animation_finished.connect(_on_animation_finished)
\t$"mesh_anchor/healthbar".texture = $"mesh_anchor/healthbar/SubViewport".get_texture()
''',
        '''func _ready():
\tself.animations.animation_finished.connect(_on_animation_finished)
\t$"mesh_anchor/healthbar".texture = self.healthbar_viewport.get_texture()
\tif OS.has_feature("web"):
\t\tself.healthbar_viewport.render_target_update_mode = SubViewport.UPDATE_ONCE

func _refresh_healthbar_viewport():
\tif OS.has_feature("web") and self.healthbar_viewport != null:
\t\tself.healthbar_viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
''',
        "Unit healthbar Web update-on-demand setup",
    )

    replace_once(
        UNIT_SCRIPT,
        '''func _update_healthbar():
\tif self.healthbar != null:
\t\tself.healthbar.value = self.hp
''',
        '''func _update_healthbar():
\tif self.healthbar != null:
\t\tself.healthbar.value = self.hp
\t\tself._refresh_healthbar_viewport()
''',
        "Unit healthbar value refresh",
    )

    replace_once(
        UNIT_SCRIPT,
        '''\tif self.level == 3:
\t\tself.healthbar_lv3.show()

func _update_energy():
''',
        '''\tif self.level == 3:
\t\tself.healthbar_lv3.show()
\tself._refresh_healthbar_viewport()

func _update_energy():
''',
        "Unit level indicator viewport refresh",
    )

    replace_once(
        UNIT_SCRIPT,
        '''func _update_energy():
\tif self.energybar != null:
\t\tself.energybar.value = self.move
\t\tself.energybar.max_value = self.max_move
''',
        '''func _update_energy():
\tif self.energybar != null:
\t\tself.energybar.value = self.move
\t\tself.energybar.max_value = self.max_move
\t\tself._refresh_healthbar_viewport()
''',
        "Unit energybar viewport refresh",
    )

    replace_once(
        UNIT_SCRIPT,
        '''func show_health():
\tif not self.enable_healthbar:
\t\treturn
\tself.healthbar_sprite.show()
''',
        '''func show_health():
\tif not self.enable_healthbar:
\t\treturn
\tself._refresh_healthbar_viewport()
\tself.healthbar_sprite.show()
''',
        "Unit healthbar show refresh",
    )



def patch_explosion_pool() -> None:
    replace_once(
        BOARD,
        '''var explosion_template = preload("res://scenes/fx/explosion.tscn")
var projectile_template = preload("res://scenes/fx/projectile.tscn")
''',
        '''var explosion_template = preload("res://scenes/fx/explosion.tscn")
var projectile_template = preload("res://scenes/fx/projectile.tscn")
var explosion_pool = []
''',
        "Board explosion pool state",
    )

    replace_once(
        BOARD,
        '''\tvar prewarm_explosion = self.explosion_template.instantiate()
\tself.explosion_anchor.add_child(prewarm_explosion)
\tprewarm_explosion.hide()
\tawait self.get_tree().process_frame
\tprewarm_explosion.queue_free()
''',
        '''\tvar prewarm_explosion = self.explosion_template.instantiate()
\tself.explosion_anchor.add_child(prewarm_explosion)
\tprewarm_explosion.reset_for_pool()
\tprewarm_explosion.hide()
\tself.explosion_pool.append(prewarm_explosion)
\tawait self.get_tree().process_frame
''',
        "Board explosion pool Web prewarm",
    )

    replace_once(
        BOARD,
        '''func destroy_explosion_with_delay(explosion_object, delay):
\tawait self.get_tree().create_timer(delay).timeout
\texplosion_object.queue_free()
''',
        '''func destroy_explosion_with_delay(explosion_object, delay):
\tawait self.get_tree().create_timer(delay).timeout
\tif not is_instance_valid(explosion_object):
\t\treturn
\texplosion_object.reset_for_pool()
\texplosion_object.hide()
\tself.explosion_pool.append(explosion_object)
''',
        "Board explosion recycle",
    )

    replace_once(
        BOARD,
        '''func _spawn_temporary_explosion_instance_on_tile(tile, free_delay=1.5):
\tvar explosion_position = self.map.map_to_local(tile.position)
\tvar new_explosion = self.explosion_template.instantiate()
\tself.explosion_anchor.add_child(new_explosion)
\tnew_explosion.set_position(Vector3(explosion_position.x, 0, explosion_position.z))
\tself.destroy_explosion_with_delay(new_explosion, free_delay)

\treturn new_explosion
''',
        '''func _spawn_temporary_explosion_instance_on_tile(tile, free_delay=1.5):
\tvar explosion_position = self.map.map_to_local(tile.position)
\tvar new_explosion
\tif self.explosion_pool.is_empty():
\t\tnew_explosion = self.explosion_template.instantiate()
\t\tself.explosion_anchor.add_child(new_explosion)
\telse:
\t\tnew_explosion = self.explosion_pool.pop_back()
\t\tnew_explosion.show()

\tnew_explosion.set_position(Vector3(explosion_position.x, 0, explosion_position.z))
\tself.destroy_explosion_with_delay(new_explosion, free_delay)

\treturn new_explosion
''',
        "Board explosion pooled allocation",
    )

    replace_once(
        EXPLOSION_SCRIPT,
        '''func rain_heal():
\tself.heal.set_emitting(true)
''',
        '''func rain_heal():
\tself.heal.set_emitting(true)

func reset_for_pool():
\tself.main.set_emitting(false)
\tself.smoke.set_emitting(false)
\tself.small_main.set_emitting(false)
\tself.bless.set_emitting(false)
\tself.heal.set_emitting(false)

\tfor audio_player in $"audio".get_children():
\t\taudio_player.stop()
\t\taudio_player.queue_free()
''',
        "Explosion pooled reset",
    )


def patch_movement_marker_pool() -> None:
    replace_once(
        MOVEMENT_MARKERS,
        'var created_markers = {}\nvar tile_path = {}',
        'var created_markers = {}\nvar marker_pool = []\nvar tile_path = {}',
        "Movement marker pool state",
    )

    replace_once(
        MOVEMENT_MARKERS,
        '''func _ready():
\tself.map_obj = self.get_node(self.map)
''',
        '''func _ready():
\tself.map_obj = self.get_node(self.map)
\tif OS.has_feature("web"):
\t\tself.call_deferred("_prewarm_marker_pool")

func _prewarm_marker_pool():
\tconst PREWARM_COUNT = 24
\tconst BATCH_SIZE = 4
\tfor i in PREWARM_COUNT:
\t\tvar marker = self.marker_template.instantiate()
\t\tself.add_child(marker)
\t\tmarker.hide()
\t\tself.marker_pool.append(marker)
\t\tif (i + 1) % BATCH_SIZE == 0:
\t\t\tawait self.get_tree().process_frame
''',
        "Movement marker Web prewarm",
    )

    replace_once(
        MOVEMENT_MARKERS,
        '''func destroy_markers():
\tvar marker
\tfor key in self.created_markers.keys():
\t\tmarker = self.created_markers[key]
\t\tmarker.hide()
\t\tmarker.queue_free()
\tself.created_markers = {}
''',
        '''func destroy_markers():
\tvar marker
\tfor key in self.created_markers.keys():
\t\tmarker = self.created_markers[key]
\t\tmarker.hide()
\t\tself.marker_pool.append(marker)
\tself.created_markers = {}
''',
        "Movement marker pooling reset",
    )

    replace_once(
        MOVEMENT_MARKERS,
        '''func place_movement_marker(marker_position):
\tvar new_marker = self.marker_template.instantiate()
\tself.add_child(new_marker)
\tvar placement = self.map_obj.map_to_local(marker_position)
\tnew_marker.set_position(placement)

\tself.created_markers[str(marker_position.x) + "_" + str(marker_position.y)] = new_marker
''',
        '''func place_movement_marker(marker_position):
\tvar new_marker
\tif self.marker_pool.is_empty():
\t\tnew_marker = self.marker_template.instantiate()
\t\tself.add_child(new_marker)
\telse:
\t\tnew_marker = self.marker_pool.pop_back()
\t\tnew_marker.show()

\tvar placement = self.map_obj.map_to_local(marker_position)
\tnew_marker.set_position(placement)

\tself.created_markers[str(marker_position.x) + "_" + str(marker_position.y)] = new_marker
''',
        "Movement marker pooling allocation",
    )


def patch_path_marker_pool_and_cache() -> None:
    replace_once(
        PATH_MARKERS,
        'var created_markers = {}\n\nvar rotations = {',
        'var created_markers = {}\nvar marker_pool = []\nvar last_path = []\n\nvar rotations = {',
        "Path marker pool/cache state",
    )

    replace_once(
        PATH_MARKERS,
        '''func _ready():
\tself.map_obj = self.get_node(self.map)
''',
        '''func _ready():
\tself.map_obj = self.get_node(self.map)
\tif OS.has_feature("web"):
\t\tself.call_deferred("_prewarm_marker_pool")

func _prewarm_marker_pool():
\tconst PREWARM_COUNT = 12
\tconst BATCH_SIZE = 4
\tfor i in PREWARM_COUNT:
\t\tvar marker = self.marker_template.instantiate()
\t\tself.add_child(marker)
\t\tmarker.hide()
\t\tself.marker_pool.append(marker)
\t\tif (i + 1) % BATCH_SIZE == 0:
\t\t\tawait self.get_tree().process_frame
''',
        "Path marker Web prewarm",
    )

    replace_once(
        PATH_MARKERS,
        '''func reset():
\tself.destroy_markers()
''',
        '''func reset():
\tself.last_path = []
\tself.destroy_markers()
''',
        "Path marker cache reset",
    )

    replace_once(
        PATH_MARKERS,
        '''func destroy_markers():
\tvar marker
\tfor key in self.created_markers.keys():
\t\tmarker = self.created_markers[key]
\t\tmarker.hide()
\t\tmarker.queue_free()
\tself.created_markers = {}
''',
        '''func destroy_markers():
\tvar marker
\tfor key in self.created_markers.keys():
\t\tmarker = self.created_markers[key]
\t\tmarker.hide()
\t\tself.marker_pool.append(marker)
\tself.created_markers = {}
''',
        "Path marker pooling reset",
    )

    replace_once(
        PATH_MARKERS,
        '''func draw_path(path):
\tself.reset()

\tfor i in path.size():
\t\tif i < path.size() - 1:
\t\t\tself.place_marker(path[i])

\tself.rotate_markers(path)
''',
        '''func draw_path(path):
\tif path == self.last_path:
\t\treturn

\tself.destroy_markers()
\tself.last_path = path.duplicate()

\tfor i in path.size():
\t\tif i < path.size() - 1:
\t\t\tself.place_marker(path[i])

\tself.rotate_markers(path)
''',
        "Path marker unchanged-path cache",
    )

    replace_once(
        PATH_MARKERS,
        '''func place_marker(tile_key):
\tvar tile = self.map_obj.model.tiles[tile_key]
\tvar new_marker = self.marker_template.instantiate()
\tself.add_child(new_marker)
\tvar placement = self.map_obj.map_to_local(tile.position)
\tnew_marker.set_position(placement)

\tself.created_markers[tile_key] = new_marker
''',
        '''func place_marker(tile_key):
\tvar tile = self.map_obj.model.tiles[tile_key]
\tvar new_marker
\tif self.marker_pool.is_empty():
\t\tnew_marker = self.marker_template.instantiate()
\t\tself.add_child(new_marker)
\telse:
\t\tnew_marker = self.marker_pool.pop_back()
\t\tnew_marker.show()

\tvar placement = self.map_obj.map_to_local(tile.position)
\tnew_marker.set_position(placement)

\tself.created_markers[tile_key] = new_marker
''',
        "Path marker pooling allocation",
    )


def patch_interaction_marker_pool() -> None:
    replace_once(
        INTERACTION_MARKERS,
        'var created_markers = {}\n',
        'var created_markers = {}\nvar attack_marker_pool = []\nvar capture_marker_pool = []\n',
        "Interaction marker pool state",
    )

    replace_once(
        INTERACTION_MARKERS,
        '''func _ready():
\tself.map_obj = self.get_node(self.map)
''',
        '''func _ready():
\tself.map_obj = self.get_node(self.map)
\tif OS.has_feature("web"):
\t\tself.call_deferred("_prewarm_marker_pools")

func _prewarm_marker_pools():
\tconst PREWARM_PER_TYPE = 4
\tfor i in PREWARM_PER_TYPE:
\t\tvar attack_marker = self.attack_marker_template.instantiate()
\t\tattack_marker.set_meta("tof_pool_type", "attack")
\t\tself.add_child(attack_marker)
\t\tattack_marker.hide()
\t\tself.attack_marker_pool.append(attack_marker)

\t\tvar capture_marker = self.capture_marker_template.instantiate()
\t\tcapture_marker.set_meta("tof_pool_type", "capture")
\t\tself.add_child(capture_marker)
\t\tcapture_marker.hide()
\t\tself.capture_marker_pool.append(capture_marker)

\t\tawait self.get_tree().process_frame
''',
        "Interaction marker Web prewarm",
    )

    replace_once(
        INTERACTION_MARKERS,
        '''func destroy_markers():
\tvar marker
\tfor key in self.created_markers.keys():
\t\tmarker = self.created_markers[key]
\t\tmarker.hide()
\t\tmarker.queue_free()
\tself.created_markers = {}
''',
        '''func destroy_markers():
\tvar marker
\tfor key in self.created_markers.keys():
\t\tmarker = self.created_markers[key]
\t\tmarker.hide()
\t\tvar pool_type = marker.get_meta("tof_pool_type", "")
\t\tif pool_type == "attack":
\t\t\tself.attack_marker_pool.append(marker)
\t\telif pool_type == "capture":
\t\t\tself.capture_marker_pool.append(marker)
\t\telse:
\t\t\tmarker.queue_free()
\tself.created_markers = {}
''',
        "Interaction marker pooling reset",
    )

    replace_once(
        INTERACTION_MARKERS,
        '''func mark_tile_for_capture(tile):
\tself.place_marker(self.capture_marker_template.instantiate(), tile)
''',
        '''func mark_tile_for_capture(tile):
\tself.place_marker("capture", self.capture_marker_template, tile)
''',
        "Capture marker pooled allocation",
    )

    replace_once(
        INTERACTION_MARKERS,
        '''func mark_tile_for_attack(tile):
\tself.place_marker(self.attack_marker_template.instantiate(), tile)
''',
        '''func mark_tile_for_attack(tile):
\tself.place_marker("attack", self.attack_marker_template, tile)
''',
        "Attack marker pooled allocation",
    )

    replace_once(
        INTERACTION_MARKERS,
        '''func place_marker(new_marker, tile):
\tself.add_child(new_marker)
\tvar placement = self.map_obj.map_to_local(tile.position)
\tnew_marker.set_position(placement)

\tself.created_markers[str(tile.position.x) + "_" + str(tile.position.y)] = new_marker
''',
        '''func place_marker(pool_type, marker_template, tile):
\tvar pool = self.attack_marker_pool if pool_type == "attack" else self.capture_marker_pool
\tvar new_marker
\tif pool.is_empty():
\t\tnew_marker = marker_template.instantiate()
\t\tnew_marker.set_meta("tof_pool_type", pool_type)
\t\tself.add_child(new_marker)
\telse:
\t\tnew_marker = pool.pop_back()
\t\tnew_marker.show()

\tvar placement = self.map_obj.map_to_local(tile.position)
\tnew_marker.set_position(placement)

\tself.created_markers[str(tile.position.x) + "_" + str(tile.position.y)] = new_marker
''',
        "Interaction marker pooled placement",
    )


def main() -> None:
    patch_board_hover()
    patch_board_fx_prewarm()
    patch_cached_tile_keys()
    patch_ai_entity_snapshot()
    patch_neighbour_iteration()
    patch_hot_dictionary_reuse()
    patch_ai_path_cache()
    patch_unit_hot_stat_reads()
    patch_idle_transform_updates()
    patch_healthbar_viewport_updates()
    patch_explosion_pool()
    patch_movement_marker_pool()
    patch_path_marker_pool_and_cache()
    patch_interaction_marker_pool()


if __name__ == "__main__":
    main()
