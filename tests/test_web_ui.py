"""Integration-style tests for the web UI routing and HTML rendering."""

from __future__ import annotations

import http.client
import io
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from urllib.parse import urlencode
from urllib.parse import parse_qs, urlparse

from square_cards.repository import ModuleInput, ModuleRepository
from square_cards.server import AppState, ModuleRequestHandler, create_app_state
from square_cards.views import (
    CatalogPageData,
    PageChoices,
    ViewFilters,
    ViewerPageData,
    render_catalog_page,
    render_module_card,
    render_viewer_page,
)


class WebUiRenderingTests(unittest.TestCase):
    """Verify the HTML generated for catalog and viewer pages."""

    def setUp(self) -> None:
        temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temp_dir)
        self.repository = ModuleRepository(temp_dir / "modules.sqlite3")
        self.choices = PageChoices(
            levels=self.repository.list_levels(),
            start_positions=self.repository.list_start_positions(),
            sources=("alpha",),
        )

    def test_render_catalog_page_shows_empty_state_and_admin_forms(self) -> None:
        """Catalog rendering should keep the import and settings controls visible."""

        page = CatalogPageData(
            modules=[],
            counts={"MS": 0, "Plus": 0, "A1": 0, "A2": 0},
            choices=self.choices,
            filters=ViewFilters(),
            editing=None,
            message="Gespeichert",
        )

        markup = render_catalog_page(page)

        self.assertIn("Keine Module gefunden.", markup)
        self.assertIn("Level anlegen", markup)
        self.assertIn("Start anlegen", markup)
        self.assertIn("Datenbank exportieren", markup)
        self.assertIn("Datei importieren", markup)
        self.assertIn('class="banner success"', markup)

    def test_render_module_card_shows_source_and_extra_calls(self) -> None:
        """Long modules should show the source and the extra-calls summary."""

        module = self.repository.create_module(
            ModuleInput(
                title="Long Module",
                level="MS",
                start_position="Static Square",
                raw_text="\n".join(f"Call {index}" for index in range(1, 13)),
                source_name="alpha",
            )
        )

        markup = render_module_card(module, ViewFilters(level="MS"))

        self.assertIn("Quelle: <strong>alpha</strong>", markup)
        self.assertIn("… 2 weitere Calls", markup)
        self.assertIn("Komplettes Modul anzeigen", markup)
        self.assertIn("/viewer?level=MS&id=", markup)

    def test_render_viewer_page_shows_navigation_and_random_button(self) -> None:
        """Viewer rendering should include navigation, filters and random mode."""

        first = self._create_module("First", "Heads square thru\nSwing thru")
        second = self._create_module("Second", "Pass the ocean\nScoot back")
        third = self._create_module("Third", "Recycle\nFerris wheel")

        page = ViewerPageData(
            modules=[first, second, third],
            choices=self.choices,
            filters=ViewFilters(level="MS", source="alpha", query="ocean"),
            selected_module=second,
            selected_index=1,
        )

        markup = render_viewer_page(page)

        self.assertIn('name="random" value="1"', markup)
        self.assertIn('class="viewer-call-row"', markup)
        self.assertIn("Vorheriges</a>", markup)
        self.assertIn("Nächstes</a>", markup)
        self.assertIn('class="viewer-page"', markup)
        self.assertIn("/?level=MS&source=alpha&q=ocean", markup)

    def test_render_viewer_page_shows_empty_state(self) -> None:
        """Viewer rendering should produce an explicit empty state."""

        page = ViewerPageData(
            modules=[],
            choices=self.choices,
            filters=ViewFilters(),
            selected_module=None,
            selected_index=-1,
        )

        markup = render_viewer_page(page)

        self.assertIn("Keine Module für die aktuellen Filter gefunden.", markup)
        self.assertIn("0 Modul(e) in der aktuellen Auswahl", markup)

    def _create_module(self, title: str, raw_text: str) -> object:
        """Create a module record for rendering assertions."""

        return self.repository.create_module(
            ModuleInput(
                title=title,
                level="MS",
                start_position="Static Square",
                raw_text=raw_text,
                source_name="alpha",
            )
        )


class WebUiServerTests(unittest.TestCase):
    """Verify that the HTTP handler routes requests correctly."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp_dir)
        self.app_state = create_app_state(self.temp_dir)

    def test_get_routes_render_catalog_and_viewer(self) -> None:
        """Catalog and viewer pages should render over HTTP."""

        first = self._create_module("First", "Heads square thru\nSwing thru")
        self._create_module("Second", "Pass the ocean\nScoot back")

        status, headers, payload = self._request("GET", "/?level=MS")
        body = payload.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Square Cards Modulverwaltung", body)
        self.assertIn("Einzelansicht", body)

        viewer_status, _, viewer_payload = self._request(
            "GET",
            f"/viewer?level=MS&id={first.id}",
        )
        viewer_body = viewer_payload.decode("utf-8")

        self.assertEqual(viewer_status, 200)
        self.assertIn("Random", viewer_body)
        self.assertIn("viewer-call-row", viewer_body)

    def test_head_and_unknown_routes_return_expected_status(self) -> None:
        """Known HEAD routes should succeed while unknown paths return 404."""

        status, _, payload = self._request("HEAD", "/db/export")
        self.assertEqual(status, 200)
        self.assertEqual(payload, b"")

        missing_status, _, missing_payload = self._request("GET", "/missing")
        self.assertEqual(missing_status, 404)
        self.assertEqual(missing_payload.decode("utf-8"), "Nicht gefunden.")

        missing_head, _, _ = self._request("HEAD", "/unknown")
        self.assertEqual(missing_head, 404)

    def test_settings_and_module_lifecycle_routes(self) -> None:
        """Settings, create, update and delete routes should mutate the database."""

        level_status, level_headers, _ = self._form_post(
            "/settings/levels",
            {"level_name": "C1"},
        )
        start_status, _, _ = self._form_post(
            "/settings/starts",
            {"start_name": "Eight Chain Thru"},
        )

        self.assertEqual(level_status, 303)
        self.assertIn("Level+angelegt%3A+C1.", level_headers["Location"])
        self.assertEqual(start_status, 303)

        create_status, create_headers, _ = self._form_post(
            "/modules",
            {
                "title": "Created",
                "level": "C1",
                "start_position": "Eight Chain Thru",
                "raw_text": "Spin chain thru\nRecycle",
                "source_name": "manual",
            },
        )
        self.assertEqual(create_status, 303)
        self.assertIn("Modul+gespeichert.", create_headers["Location"])

        created = self.app_state.repository.list_modules(level="C1")[0]
        update_status, update_headers, _ = self._form_post(
            f"/modules/{created.id}/update",
            {
                "title": "Updated",
                "level": "C1",
                "start_position": "Eight Chain Thru",
                "raw_text": "Spin chain thru\nAcey deucey",
                "source_name": "edited",
            },
        )
        self.assertEqual(update_status, 303)
        self.assertIn("Änderungen gespeichert.", self._location_message(update_headers))
        self.assertEqual(
            self.app_state.repository.get_module(created.id).source_name,
            "edited",
        )

        delete_status, delete_headers, _ = self._form_post(
            f"/modules/{created.id}/delete",
            {},
        )
        self.assertEqual(delete_status, 303)
        self.assertIn("Modul gelöscht.", self._location_message(delete_headers))
        self.assertEqual(self.app_state.repository.list_modules(level="C1"), [])

    def test_import_routes_and_database_export_work(self) -> None:
        """Import routes should parse files and export the resulting database."""

        fixture = (
            Path(__file__).resolve().parent / "fixtures" / "example-pattern.txt"
        )
        example_file = self.temp_dir / "callerschool-pattern"
        example_file.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

        import_status, _, _ = self._form_post("/import/examples", {})
        self.assertEqual(import_status, 303)
        self.assertEqual(len(self.app_state.repository.list_modules()), 2)

        upload_status, upload_headers, _ = self._multipart_post(
            "/import/upload",
            fields={
                "import_level": "Plus",
                "import_start": "Zero Box",
                "import_source": "Upload Batch",
            },
            files={
                "module_file": (
                    "sample.in",
                    (
                        "@\n"
                        "#REC=1#\n"
                        "Spin Chain Thru,\n"
                        "Recycle\n"
                    ).encode("utf-8"),
                    "text/plain",
                )
            },
        )
        self.assertEqual(upload_status, 303)
        self.assertIn("Upload+importiert", upload_headers["Location"])

        export_status, export_headers, export_payload = self._request("GET", "/db/export")
        self.assertEqual(export_status, 200)
        self.assertEqual(export_headers["Content-Type"], "application/x-sqlite3")
        self.assertGreater(len(export_payload), 0)

        imported_db = self.temp_dir / "incoming.sqlite3"
        imported_repository = ModuleRepository(imported_db)
        imported_repository.create_module(
            ModuleInput(
                title="Imported DB Title",
                level="A1",
                start_position="Zero Box",
                raw_text="Swing thru\nRecycle",
                source_name="Imported DB",
            )
        )
        db_import_status, _, _ = self._multipart_post(
            "/db/import",
            files={
                "db_file": (
                    "incoming.sqlite3",
                    imported_db.read_bytes(),
                    "application/x-sqlite3",
                )
            },
        )
        self.assertEqual(db_import_status, 303)
        self.assertEqual(
            self.app_state.repository.list_modules()[0].title,
            "Imported DB Title",
        )

    def test_upload_route_detects_callerschool_files(self) -> None:
        """The shared upload route should auto-detect CallerSchool pattern files."""

        fixture = (
            Path(__file__).resolve().parent / "fixtures" / "example-pattern.txt"
        )

        upload_status, upload_headers, _ = self._multipart_post(
            "/import/upload",
            fields={
                "import_level": "Plus",
                "import_start": "Zero Box",
                "import_source": "Pattern Upload",
            },
            files={
                "module_file": (
                    "callerschool-pattern.txt",
                    fixture.read_bytes(),
                    "text/plain",
                )
            },
        )

        self.assertEqual(upload_status, 303)
        self.assertIn("Upload+importiert", upload_headers["Location"])
        modules = self.app_state.repository.list_modules()
        self.assertEqual(len(modules), 2)
        self.assertEqual({module.level for module in modules}, {"MS"})
        self.assertEqual({module.start_position for module in modules}, {"Zero Box"})
        self.assertEqual({module.source_name for module in modules}, {"Pattern Upload"})

    def test_import_routes_surface_errors(self) -> None:
        """Invalid uploads should redirect with an error message."""

        invalid_db_status, invalid_db_headers, _ = self._multipart_post(
            "/db/import",
            files={"db_file": ("broken.sqlite3", b"not-a-db", "application/octet-stream")},
        )
        self.assertEqual(invalid_db_status, 303)
        self.assertIn("SQLite-Datenbank", self._location_message(invalid_db_headers))

        upload_status, upload_headers, _ = self._multipart_post(
            "/import/upload",
            fields={
                "import_level": "MS",
                "import_start": "Static Square",
                "import_source": "Broken Upload",
            },
            files={"module_file": ("broken.in", b"\xff\xfe\xfd", "application/octet-stream")},
        )
        self.assertEqual(upload_status, 303)
        self.assertIn("UTF-8-kodierter Text", self._location_message(upload_headers))

    def _create_module(self, title: str, raw_text: str) -> object:
        """Insert a module into the repository backing the test server."""

        return self.app_state.repository.create_module(
            ModuleInput(
                title=title,
                level="MS",
                start_position="Static Square",
                raw_text=raw_text,
                source_name="server-test",
            )
        )

    def _form_post(
        self,
        path: str,
        fields: dict[str, str],
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        """Submit a URL-encoded POST request to the test server."""

        body = urlencode(fields)
        return self._request(
            "POST",
            path,
            body=body.encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    def _multipart_post(
        self,
        path: str,
        *,
        fields: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        """Submit a multipart POST request with fields and file uploads."""

        boundary = "square-cards-boundary"
        body = bytearray()
        for name, value in (fields or {}).items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode("utf-8")
            )
        for name, (filename, content, content_type) in (files or {}).items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                    f"Content-Type: {content_type}\r\n\r\n"
                ).encode("utf-8")
            )
            body.extend(content)
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        return self._request(
            "POST",
            path,
            body=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        """Perform one in-memory request against the handler."""

        handler = _InMemoryHandler(
            app_state=self.app_state,
            request=_RequestSpec(
                method=method,
                path=path,
                body=body or b"",
                headers=headers or {},
            ),
        )
        if method == "GET":
            handler.do_GET()
        elif method == "POST":
            handler.do_POST()
        elif method == "HEAD":
            handler.do_HEAD()
        else:
            raise ValueError(f"Unsupported test method: {method}")
        return handler.status_code, handler.response_headers, handler.wfile.getvalue()

    @staticmethod
    def _location_message(headers: http.client.HTTPMessage) -> str:
        """Extract the redirect message query parameter from a Location header."""

        location = headers["Location"]
        return parse_qs(urlparse(location).query).get("message", [""])[0]


@dataclass(slots=True)
class _RequestSpec:
    """Input data for an in-memory request to the HTTP handler."""

    method: str
    path: str
    body: bytes
    headers: dict[str, str]


class _InMemoryHandler(  # pylint: disable=super-init-not-called
    ModuleRequestHandler
):
    """Minimal request handler harness that captures responses in memory."""

    def __init__(
        self,
        *,
        app_state: AppState,
        request: _RequestSpec,
    ) -> None:
        self.app_state = app_state
        self.path = request.path
        self.headers = Message()
        for key, value in request.headers.items():
            self.headers[key] = value
        self.headers["Content-Length"] = str(len(request.body))
        self.rfile = io.BytesIO(request.body)
        self.wfile = io.BytesIO()
        self.status_code = 0
        self.response_headers = Message()

    def send_response(self, code: int, message: str | None = None) -> None:
        """Capture the response status code."""

        del message
        self.status_code = code

    def send_header(self, keyword: str, value: str) -> None:
        """Capture outgoing response headers."""

        self.response_headers[keyword] = value

    def end_headers(self) -> None:
        """Complete the in-memory response without writing to a socket."""

    def log_message(  # pylint: disable=arguments-differ
        self,
        format_string: str,
        *args: object,
    ) -> None:
        """Silence logging in tests."""

        del format_string, args


if __name__ == "__main__":
    unittest.main()
