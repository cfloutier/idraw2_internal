"""Unit tests for ResumeStatus's PLOB serialization of pause_path_index
(idraw2_0internal/plot_status.py), in particular backward compatibility with
resume files saved before this field existed.

Run directly: python -m unittest test_plot_status
"""
from __future__ import annotations

import unittest

from lxml import etree

from idraw2_0internal.plot_status import ResumeStatus


class ResumePathIndexSerializationTests(unittest.TestCase):
    def test_round_trips_through_svg(self) -> None:
        resume = ResumeStatus()
        resume.new.pause_dist = 1.5
        resume.new.pause_ref = 1.5
        resume.new.pause_path_index = 42
        svg = etree.Element("svg")
        resume.write_to_svg(svg)

        reloaded = ResumeStatus()
        reloaded.read_from_svg(svg)

        self.assertTrue(reloaded.read)
        self.assertEqual(reloaded.old.pause_path_index, 42)

    def test_old_format_file_without_field_falls_back_to_minus_one(self) -> None:
        # Simulates a resume SVG saved before pause_path_index existed: no
        # such attribute on the <plotdata> node at all.
        svg = etree.Element("svg")
        data_node = etree.SubElement(svg, "plotdata")
        data_node.set("application", "idraw")
        data_node.set("model", "1")
        data_node.set("plob_version", "n/a")
        data_node.set("layer", "-1")
        data_node.set("pause_dist", "12700")  # 0.5 inch, in µm
        data_node.set("pause_ref", "12700")
        data_node.set("last_x", "10.0")
        data_node.set("last_y", "20.0")
        data_node.set("rand_seed", "1")
        data_node.set("row", "0")
        # Deliberately no 'pause_path_index' attribute.

        resume = ResumeStatus()
        resume.read_from_svg(svg)

        self.assertTrue(resume.read)  # core resume data still valid
        self.assertAlmostEqual(resume.old.pause_dist, 0.5)
        self.assertEqual(resume.old.pause_path_index, -1)  # fallback sentinel

    def test_corrupt_core_data_still_discards_everything(self) -> None:
        # A malformed core field (missing pause_dist) must still invalidate
        # the whole resume record, exactly like before this change - only
        # the *new* field is allowed to be independently optional.
        svg = etree.Element("svg")
        data_node = etree.SubElement(svg, "plotdata")
        data_node.set("layer", "-1")
        # pause_dist deliberately missing -> int(None) raises TypeError

        resume = ResumeStatus()
        resume.read_from_svg(svg)

        self.assertFalse(resume.read)
        self.assertEqual(resume.old.pause_path_index, -1)  # untouched default

    def test_copy_old_carries_path_index(self) -> None:
        resume = ResumeStatus()
        resume.old.pause_path_index = 7
        resume.copy_old()
        self.assertEqual(resume.new.pause_path_index, 7)


if __name__ == "__main__":
    unittest.main()
