"""Unit tests for dripfeed.feed_sm()'s preview-mode split of pt_estimate into
down_motion_ms/up_motion_ms (idraw2_0internal/plot_status.py's PlotStats),
gated on the same z_up flag add_dist() already uses to split distance.

Run directly: python -m unittest test_dripfeed
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from idraw2_0internal.dripfeed import feed_sm
from idraw2_0internal.plot_status import PlotStats


def _make_ad_ref(*, z_up, mode="plot"):
    stats = PlotStats()
    return SimpleNamespace(
        options=SimpleNamespace(preview=True, mode=mode),
        plot_status=SimpleNamespace(
            stats=stats,
            progress=SimpleNamespace(update_auto=lambda _stats: None),
        ),
        pen=SimpleNamespace(phys=SimpleNamespace(z_up=z_up, xpos=0.0, ypos=0.0)),
        preview=SimpleNamespace(log_sm_move=lambda _ad_ref, _move: None),
    )


def _move(move_time, move_dist=1.0):
    # ['SM', (move_steps2, move_steps1, move_time), seg_data]
    return ["SM", (0, 0, move_time), (5.0, 5.0, False, move_dist)]


class FeedSmEstimateSplitTests(unittest.TestCase):
    def test_pen_up_short_move_adds_to_up_motion_only(self) -> None:
        ad_ref = _make_ad_ref(z_up=True)

        feed_sm(ad_ref, _move(30), drip_logger=None)

        stats = ad_ref.plot_status.stats
        self.assertEqual(stats.up_motion_ms, 30)
        self.assertEqual(stats.down_motion_ms, 0)
        self.assertEqual(stats.pt_estimate, 30)

    def test_pen_down_short_move_adds_to_down_motion_only(self) -> None:
        ad_ref = _make_ad_ref(z_up=False)

        feed_sm(ad_ref, _move(30), drip_logger=None)

        stats = ad_ref.plot_status.stats
        self.assertEqual(stats.down_motion_ms, 30)
        self.assertEqual(stats.up_motion_ms, 0)
        self.assertEqual(stats.pt_estimate, 30)

    def test_long_move_uses_discounted_time_in_the_split(self) -> None:
        # move_time > 50 -> the existing -30ms real-mode mirror applies;
        # the split must use that same discounted value, not the raw one.
        ad_ref = _make_ad_ref(z_up=True)

        feed_sm(ad_ref, _move(80), drip_logger=None)

        stats = ad_ref.plot_status.stats
        self.assertEqual(stats.up_motion_ms, 50)  # 80 - 30
        self.assertEqual(stats.pt_estimate, 50)

    def test_manual_mode_does_not_apply_discount(self) -> None:
        ad_ref = _make_ad_ref(z_up=False, mode="manual")

        feed_sm(ad_ref, _move(80), drip_logger=None)

        stats = ad_ref.plot_status.stats
        self.assertEqual(stats.down_motion_ms, 80)  # no -30ms discount
        self.assertEqual(stats.pt_estimate, 80)

    def test_split_sums_back_to_pt_estimate_across_mixed_moves(self) -> None:
        ad_ref = _make_ad_ref(z_up=True)
        feed_sm(ad_ref, _move(30), drip_logger=None)  # up, short
        ad_ref.pen.phys.z_up = False
        feed_sm(ad_ref, _move(20), drip_logger=None)  # down, short
        ad_ref.pen.phys.z_up = True
        feed_sm(ad_ref, _move(80), drip_logger=None)  # up, long -> discounted

        stats = ad_ref.plot_status.stats
        self.assertEqual(stats.down_motion_ms, 20)
        self.assertEqual(stats.up_motion_ms, 30 + 50)
        self.assertEqual(stats.down_motion_ms + stats.up_motion_ms, stats.pt_estimate)


if __name__ == "__main__":
    unittest.main()
