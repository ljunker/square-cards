"""Regression tests for repository, importer and viewer helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from square_cards.importer import parse_callerschool_file
from square_cards.repository import (
    DuplicateModuleError,
    ModuleInput,
    ModuleRepository,
    build_module_hash,
)
from square_cards.server import build_query, pick_selected_module, viewer_link


class RepositoryTests(unittest.TestCase):
    """Verify module normalization, persistence and viewer helper behavior."""

    def setUp(self) -> None:
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        self.db_path = Path(temp_dir) / "modules.sqlite3"
        self.repository = ModuleRepository(self.db_path)

    def test_duplicate_detection_uses_normalized_hash(self) -> None:
        """Whitespace-only differences must not bypass duplicate detection."""

        self.repository.create_module(
            ModuleInput(
                title="Test 1",
                level="MS",
                start_position="Static Square",
                raw_text="Heads box the gnat\nSwing thru",
            )
        )

        with self.assertRaises(DuplicateModuleError):
            self.repository.create_module(
                ModuleInput(
                    title="Test 2",
                    level="Plus",
                    start_position="Zero Box",
                    raw_text="  heads   box the gnat \n swing thru ",
                )
            )

    def test_hash_ignores_header_date_and_sd_version(self) -> None:
        """Header metadata must not influence the stored module hash."""

        clean_hash = build_module_hash("HEADS box the gnat\nSwing thru")[1]
        header_hash = build_module_hash(
            "Sun Mar 15 18:51:58 2026     Sd39.81:db39.81     Mainstream\n\n"
            "HEADS box the gnat\nSwing thru"
        )[1]

        self.assertEqual(clean_hash, header_hash)

    def test_importer_reads_sample_file(self) -> None:
        """The sample import should yield the two bundled example modules."""

        source_file = Path(__file__).resolve().parent / "fixtures" / "callerschool-pattern.txt"
        modules = parse_callerschool_file(source_file)

        self.assertEqual(len(modules), 2)
        self.assertEqual(modules[0].level, "MS")
        self.assertEqual(modules[0].start_position, "Static Square")
        self.assertTrue(modules[0].raw_text.startswith("HEADS box the gnat"))

    def test_viewer_selection_falls_back_to_first_filtered_module(self) -> None:
        """Viewer selection should fall back to the first filtered module."""

        first = self.repository.create_module(
            ModuleInput(
                title="First",
                level="MS",
                start_position="Static Square",
                raw_text="Heads square thru\nSwing thru",
            )
        )
        second = self.repository.create_module(
            ModuleInput(
                title="Second",
                level="MS",
                start_position="Static Square",
                raw_text="Heads touch a quarter\nScoot back",
            )
        )

        selected, index = pick_selected_module([first, second], "9999")

        self.assertEqual(selected.id, first.id)
        self.assertEqual(index, 0)

    def test_viewer_link_keeps_filter_context(self) -> None:
        """Viewer navigation must preserve all active filter values."""

        filters = {
            "level": "A1",
            "start": "Zero Box",
            "source": "callerschool-pattern",
            "q": "trade",
        }

        link = viewer_link(filters, 17)

        self.assertEqual(
            link,
            "/viewer?level=A1&start=Zero+Box&source=callerschool-pattern&q=trade&id=17",
        )
        self.assertEqual(
            build_query(filters),
            "level=A1&start=Zero+Box&source=callerschool-pattern&q=trade",
        )

    def test_repository_can_filter_and_list_sources(self) -> None:
        """Source filters and source listing should remain in sync."""

        self.repository.create_module(
            ModuleInput(
                title="Sample A",
                level="MS",
                start_position="Static Square",
                raw_text="Heads square thru\nSwing thru",
                source_name="alpha",
            )
        )
        self.repository.create_module(
            ModuleInput(
                title="Sample B",
                level="MS",
                start_position="Zero Box",
                raw_text="Heads touch a quarter\nScoot back",
                source_name="beta",
            )
        )

        beta_modules = self.repository.list_modules(source_name="beta")

        self.assertEqual(len(beta_modules), 1)
        self.assertEqual(beta_modules[0].source_name, "beta")
        self.assertEqual(self.repository.list_sources(), ("alpha", "beta"))


if __name__ == "__main__":
    unittest.main()
