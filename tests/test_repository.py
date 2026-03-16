"""Regression tests for repository, importer and viewer helpers."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from square_cards.importer import parse_callerschool_file, parse_choreodb_text
from square_cards.repository import (
    DuplicateModuleError,
    ModuleInput,
    ModuleRepository,
    build_module_hash,
)
from square_cards.server import (
    build_query,
    pick_viewer_module,
    pick_selected_module,
    replace_database_file,
    validate_database_file,
    viewer_link,
)


class RepositoryTests(unittest.TestCase):
    """Verify module normalization, persistence and viewer helper behavior."""

    def setUp(self) -> None:
        temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temp_dir)
        self.db_path = temp_dir / "modules.sqlite3"
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

        source_file = Path(__file__).resolve().parent / "fixtures" / "example-pattern.txt"
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

    def test_choreodb_import_uses_file_level_metadata(self) -> None:
        """A choreodb upload should apply one metadata set to all parsed modules."""

        choreodb_text = (
            "@\n"
            "#PROOFREAD#\n"
            "#REC=8954#\n"
            "Spin Chain Thru,\n"
            "Ladies Circulate Twice,\n"
            "Right & Left Grand\n"
            "@\n"
            "#REC=1732#\n"
            "Square Thru 4,\n"
            "Ends Cross Fold,\n"
            "R.L.G\n"
        )

        modules = parse_choreodb_text(
            choreodb_text,
            level="Plus",
            start_position="Zero Box",
            source_name="ChoreoDB Upload",
        )

        self.assertEqual(len(modules), 2)
        self.assertEqual(modules[0].level, "Plus")
        self.assertEqual(modules[0].start_position, "Zero Box")
        self.assertEqual(modules[0].source_name, "ChoreoDB Upload")
        self.assertEqual(
            modules[0].raw_text,
            "Spin Chain Thru\nLadies Circulate Twice\nRight & Left Grand",
        )

    def test_repository_can_add_levels_and_start_positions(self) -> None:
        """New levels and starts should become available for validation and UI."""

        self.repository.create_level("C1")
        self.repository.create_start_position("Eight Chain Thru")

        self.assertIn("C1", self.repository.list_levels())
        self.assertIn("Eight Chain Thru", self.repository.list_start_positions())

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

    def test_uploaded_database_file_can_replace_current_database(self) -> None:
        """A valid uploaded SQLite file should replace the active database."""

        source_db = self.db_path.parent / "source.sqlite3"
        source_repository = ModuleRepository(source_db)
        source_repository.create_module(
            ModuleInput(
                title="Imported",
                level="A1",
                start_position="Zero Box",
                raw_text="Swing Thru\nRecycle",
                source_name="Imported DB",
            )
        )

        replacement_db = self.db_path.parent / "replacement.sqlite3"
        replace_database_file(source_db.read_bytes(), replacement_db)
        replacement_repository = ModuleRepository(replacement_db)
        modules = replacement_repository.list_modules()

        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0].title, "Imported")

    def test_database_validation_rejects_non_sqlite_input(self) -> None:
        """Database import must reject non-SQLite uploads."""

        invalid_db = self.db_path.parent / "invalid.sqlite3"
        invalid_db.write_text("not a database", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "SQLite-Datenbank"):
            validate_database_file(invalid_db)

    def test_random_viewer_selection_stays_within_filtered_modules(self) -> None:
        """Random viewer mode must choose one module from the filtered set."""

        first = self.repository.create_module(
            ModuleInput(
                title="First",
                level="MS",
                start_position="Static Square",
                raw_text="Heads lead right\nVeer left",
            )
        )
        second = self.repository.create_module(
            ModuleInput(
                title="Second",
                level="MS",
                start_position="Static Square",
                raw_text="Pass the ocean\nSwing thru",
            )
        )

        selected, index = pick_viewer_module(
            [first, second],
            requested_id="",
            randomize=True,
        )

        self.assertIn(selected.id, {first.id, second.id})
        self.assertIn(index, {0, 1})


if __name__ == "__main__":
    unittest.main()
