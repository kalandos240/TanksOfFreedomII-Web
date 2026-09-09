#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "scenes/board/board.gd"
MOVEMENT_MARKERS = ROOT / "scenes/board/logic/markers/movement_markers.gd"
PATH_MARKERS = ROOT / "scenes/board/logic/markers/path_markers.gd"


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
        'if tile != self.last_hover_tile or true:',
        'if tile != self.last_hover_tile:',
        "Board hover repeat guard",
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


def main() -> None:
    patch_board_hover()
    patch_movement_marker_pool()
    patch_path_marker_pool_and_cache()


if __name__ == "__main__":
    main()
