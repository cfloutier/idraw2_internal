"""Unit tests for DocDigest.crop() (idraw2_0internal/path_objects.py),
specifically the path_index-based resume fix for dot-heavy (stippling)
drawings, where consecutive near-zero-length paths defeat the original
pure-distance skip logic.

Run directly: python -m unittest test_path_objects
"""
from __future__ import annotations

import unittest

from idraw2_0internal.path_objects import DocDigest, LayerItem, PathItem


def _path(vertices):
    item = PathItem()
    item.subpaths = [[list(v) for v in vertices]]
    return item


def _dot(x, y):
    """A near-zero-length path, like one stippling dot."""
    return _path([(x, y), (x + 0.0001, y + 0.0001)])


def _zero_length_dot(x, y):
    """A truly zero-length path: two coincident vertices. This is the exact
    degenerate case that defeats distance-only cropping unconditionally -
    dist_so_far provably never advances for it, regardless of how many are
    chained together, so distance alone cannot mark it "already plotted"."""
    return _path([(x, y), (x, y)])


def _line(x1, y1, x2, y2):
    return _path([(x1, y1), (x2, y2)])


def _digest(paths):
    digest = DocDigest()
    layer = LayerItem()
    layer.paths = list(paths)
    digest.layers = [layer]
    return digest


def _remaining_vertex_counts(digest):
    """First vertex of each remaining path, as a compact fingerprint."""
    if not digest.layers:
        return []
    return [path.subpaths[0][0] for path in digest.layers[0].paths]


class CropPathIndexTests(unittest.TestCase):
    def test_path_index_skips_exact_count_of_degenerate_dots(self) -> None:
        # 100 near-zero-length dots. Pause happened after dot #40 (pure
        # index, unambiguous). Distance barely moved (~0), matching what
        # PlotStats.down_travel_inch would actually record for real dots.
        dots = [_dot(i, 0) for i in range(100)]
        digest = _digest(dots)

        digest.crop(distance=0.0001, path_index=40)

        remaining = _remaining_vertex_counts(digest)
        self.assertEqual(len(remaining), 60)
        self.assertEqual(remaining[0], [40, 0])  # dot #40 is the first kept

    def test_distance_only_fallback_loses_dots_past_the_true_resume_point(self) -> None:
        # A run of truly zero-length dots (coincident duplicate vertices -
        # not just visually tiny) preceded by one real path that carries all
        # of the recorded pause distance. WITHOUT path_index (old behavior,
        # path_index=-1 default), dist_so_far never advances through the
        # zero-length run, so the distance check keeps matching "already
        # plotted" forever and the entire run - drawn or not - is dropped.
        paths = [_line(0, 0, 5, 0)] + [_zero_length_dot(i, 0) for i in range(50)]
        digest = _digest(paths)

        digest.crop(distance=5.0)  # path_index defaults to -1: only the real path's length

        remaining = digest.layers[0].paths if digest.layers else []
        # The bug: every zero-length dot after the real path is silently
        # dropped, whether or not it was actually plotted before the pause.
        self.assertEqual(len(remaining), 0)

    def test_path_index_fixes_the_exact_zero_length_scenario_above(self) -> None:
        # Same setup as the bug-demonstration test above, but with
        # path_index provided (say, 21 of the 50 dots were actually drawn
        # before pause: 1 real path + 20 dots = index 21).
        paths = [_line(0, 0, 5, 0)] + [_zero_length_dot(i, 0) for i in range(50)]
        digest = _digest(paths)

        digest.crop(distance=5.0, path_index=21)

        remaining = _remaining_vertex_counts(digest)
        self.assertEqual(len(remaining), 30)  # 50 - 20 dots already drawn
        self.assertEqual(remaining[0], [20, 0])

    def test_path_index_zero_keeps_everything(self) -> None:
        dots = [_dot(i, 0) for i in range(10)]
        digest = _digest(dots)

        digest.crop(distance=0.0001, path_index=0)

        self.assertEqual(len(_remaining_vertex_counts(digest)), 10)

    def test_path_index_at_end_drops_everything(self) -> None:
        dots = [_dot(i, 0) for i in range(10)]
        digest = _digest(dots)

        digest.crop(distance=0.0001, path_index=10)

        self.assertEqual(digest.layers, [])

    def test_normal_length_paths_unaffected_by_path_index_mode(self) -> None:
        # Three real 10-unit-long paths; pause happened exactly between
        # path 0 and path 1 (path_index=1), matching what distance-only
        # cropping would also conclude for paths with real length.
        paths = [
            _line(0, 0, 10, 0),
            _line(0, 0, 10, 0),
            _line(0, 0, 10, 0),
        ]
        digest_by_index = _digest(list(paths))
        digest_by_distance = _digest(
            [_line(0, 0, 10, 0), _line(0, 0, 10, 0), _line(0, 0, 10, 0)]
        )

        digest_by_index.crop(distance=10.0, path_index=1)
        digest_by_distance.crop(distance=10.0)  # old behavior, no path_index

        self.assertEqual(len(digest_by_index.layers[0].paths), 2)
        self.assertEqual(len(digest_by_distance.layers[0].paths), 2)

    def test_partial_path_still_spliced_by_distance_with_path_index(self) -> None:
        # Pause occurred partway through the second path (a real, non-zero
        # length path) - path_index identifies *which* path, distance still
        # locates *where* within it, exactly like the pre-existing behavior.
        paths = [_line(0, 0, 10, 0), _line(0, 0, 10, 0)]
        digest = _digest(paths)

        # First path (10 units) fully done, 4 units into the second.
        digest.crop(distance=14.0, path_index=1)

        remaining = digest.layers[0].paths
        self.assertEqual(len(remaining), 1)
        self.assertAlmostEqual(remaining[0].subpaths[0][0][0], 4.0)

    def test_degenerate_boundary_path_not_spliced_no_crash(self) -> None:
        # The exact path at path_index is itself a near-zero-length dot
        # (interrupted before its single move executed) - must not attempt
        # crop_by_distance (would divide by ~0) and must be kept whole.
        paths = [_line(0, 0, 10, 0), _dot(50, 50), _dot(51, 51)]
        digest = _digest(paths)

        digest.crop(distance=10.0, path_index=1)

        remaining = _remaining_vertex_counts(digest)
        self.assertEqual(len(remaining), 2)
        self.assertEqual(remaining[0], [50, 50])


if __name__ == "__main__":
    unittest.main()
