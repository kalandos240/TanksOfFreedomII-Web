#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "scenes/board/board.gd"
MOVEMENT_MARKERS = ROOT / "scenes/board/logic/markers/movement_markers.gd"
PATH_MARKERS = ROOT / "scenes/board/logic/markers/path_markers.gd"
INTERACTION_MARKERS = ROOT / "scenes/board/logic/markers/interaction_markers.gd"


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
    patch_movement_marker_pool()
    patch_path_marker_pool_and_cache()
    patch_interaction_marker_pool()


if __name__ == "__main__":
    main()
