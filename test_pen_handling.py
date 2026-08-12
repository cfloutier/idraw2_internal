"""Unit tests for PenLiftTiming.update() (idraw2_0internal/pen_handling.py).

Run directly: python -m unittest test_pen_handling
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from idraw2_0internal.pen_handling import PenLiftTiming


def _make_ad_ref(*, pen_pos_up, pen_rate_raise=5000, pen_rate_lower=5000,
                  pen_delay_up=0, pen_delay_down=0):
    params = SimpleNamespace(
        servo_sweep_time=200,
        servo_move_min=45,
        servo_move_slope=2.69,
        nb_servo_sweep_time=70,
        nb_servo_move_min=20,
        nb_servo_move_slope=1.28,
    )
    options = SimpleNamespace(
        pen_pos_up=pen_pos_up,
        pen_rate_raise=pen_rate_raise,
        pen_rate_lower=pen_rate_lower,
        pen_delay_up=pen_delay_up,
        pen_delay_down=pen_delay_down,
    )
    return SimpleNamespace(params=params, options=options)


class PenLiftTimingTests(unittest.TestCase):
    def test_nonzero_travel_produces_nonzero_times(self) -> None:
        ad_ref = _make_ad_ref(pen_pos_up=1.0)
        timing = PenLiftTiming()

        timing.update(ad_ref, False, pen_down_pos=5.0)

        self.assertGreater(timing.raise_time, 0)
        self.assertGreater(timing.lower_time, 0)

    def test_equal_positions_yield_zero_delay(self) -> None:
        ad_ref = _make_ad_ref(pen_pos_up=5.0)
        timing = PenLiftTiming()

        timing.update(ad_ref, False, pen_down_pos=5.0)

        self.assertEqual(timing.raise_time, 0)
        self.assertEqual(timing.lower_time, 0)

    def test_sub_threshold_travel_yields_zero_delay(self) -> None:
        # v_dist < 0.9 is treated as "no travel" per the upstream model.
        ad_ref = _make_ad_ref(pen_pos_up=5.0)
        timing = PenLiftTiming()

        timing.update(ad_ref, False, pen_down_pos=5.5)

        self.assertEqual(timing.raise_time, 0)
        self.assertEqual(timing.lower_time, 0)

    def test_narrow_band_uses_nb_servo_constants(self) -> None:
        standard_ad_ref = _make_ad_ref(pen_pos_up=1.0)
        narrow_ad_ref = _make_ad_ref(pen_pos_up=1.0)
        standard_timing = PenLiftTiming()
        narrow_timing = PenLiftTiming()

        standard_timing.update(standard_ad_ref, False, pen_down_pos=5.0)
        narrow_timing.update(narrow_ad_ref, True, pen_down_pos=5.0)

        # Narrow-band constants (70/20/1.28) are all smaller than the
        # standard ones (200/45/2.69), so travel time should be shorter.
        self.assertLess(narrow_timing.raise_time, standard_timing.raise_time)
        self.assertLess(narrow_timing.lower_time, standard_timing.lower_time)

    def test_pen_delay_adds_to_travel_time(self) -> None:
        ad_ref = _make_ad_ref(pen_pos_up=1.0, pen_delay_up=100, pen_delay_down=250)
        timing = PenLiftTiming()

        timing.update(ad_ref, False, pen_down_pos=5.0)

        without_delay = _make_ad_ref(pen_pos_up=1.0)
        baseline = PenLiftTiming()
        baseline.update(without_delay, False, pen_down_pos=5.0)

        self.assertEqual(timing.raise_time, baseline.raise_time + 100)
        self.assertEqual(timing.lower_time, baseline.lower_time + 250)


if __name__ == "__main__":
    unittest.main()
