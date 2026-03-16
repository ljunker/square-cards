"""HTTP server and request routing for the Square Cards web UI."""

from __future__ import annotations

from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import random
from pathlib import Path
import sqlite3
import tempfile
from urllib.parse import parse_qs, urlparse

from .importer import (
    detect_upload_format,
    parse_callerschool_file,
    parse_callerschool_text,
    parse_choreodb_text,
)
from .repository import (
    DuplicateModuleError,
    ModuleInput,
    ModuleRecord,
    ModuleRepository,
)
from .views import (
    CatalogPageData,
    PageChoices,
    ViewFilters,
    ViewerPageData,
    build_query,
    pick_selected_module,
    render_catalog_page,
    render_viewer_page,
    viewer_link as _viewer_link,
)


@dataclass(slots=True)
class AppState:
    """Shared application state used by the request handler."""

    repository: ModuleRepository
    example_file: Path
    db_path: Path


@dataclass(slots=True)
class UploadedFile:
    """Multipart file payload received from the browser."""

    filename: str
    content: bytes


def pick_viewer_module(
    modules: list[ModuleRecord],
    *,
    requested_id: str,
    randomize: bool,
) -> tuple[ModuleRecord | None, int]:
    """Select a viewer module either by id or random filtered choice."""

    if not modules:
        return None, -1
    if randomize:
        random_index = random.randrange(len(modules))
        return modules[random_index], random_index
    return pick_selected_module(modules, requested_id)


def create_app_state(workspace: Path) -> AppState:
    """Create repository-backed application state for the given workspace."""

    data_dir = workspace / "data"
    db_path = data_dir / "modules.sqlite3"
    repository = ModuleRepository(db_path)
    example_file = workspace / "callerschool-pattern"
    if example_file.exists():
        repository.create_many(parse_callerschool_file(example_file))
    return AppState(repository=repository, example_file=example_file, db_path=db_path)


class ModuleRequestHandler(BaseHTTPRequestHandler):  # pylint: disable=invalid-name
    """Serve the catalog and viewer pages plus mutation endpoints."""

    app_state: AppState

    def do_HEAD(self) -> None:  # pylint: disable=invalid-name
        """Return a lightweight health response for known routes."""

        parsed = urlparse(self.path)
        if parsed.path not in {"/", "/viewer", "/db/export"}:
            self._respond(
                HTTPStatus.NOT_FOUND,
                "",
                content_type="text/plain; charset=utf-8",
            )
            return
        self._respond(HTTPStatus.OK, "")

    def do_GET(self) -> None:  # pylint: disable=invalid-name
        """Render the catalog or single-module viewer page."""

        parsed = urlparse(self.path)
        if parsed.path == "/db/export":
            self._export_database()
            return
        if parsed.path not in {"/", "/viewer"}:
            self._respond(
                HTTPStatus.NOT_FOUND,
                "Nicht gefunden.",
                content_type="text/plain; charset=utf-8",
            )
            return

        query = parse_qs(parsed.query)
        filters = self._filters_from_query(query)
        choices = PageChoices(
            levels=self.app_state.repository.list_levels(),
            start_positions=self.app_state.repository.list_start_positions(),
            sources=self.app_state.repository.list_sources(),
        )
        modules = self.app_state.repository.list_modules(
            level=filters.level,
            start_position=filters.start,
            source_name=filters.source,
            query=filters.query,
        )
        page = (
            self._render_viewer(
                parsed.path,
                query,
                filters,
                modules,
                choices,
            )
            if parsed.path == "/viewer"
            else self._render_catalog(
                query,
                filters,
                modules,
                choices,
            )
        )
        self._respond(HTTPStatus.OK, page)

    def do_POST(self) -> None:  # pylint: disable=invalid-name
        """Handle create, update, delete and import actions."""

        parsed = urlparse(self.path)
        form, files = self._read_request_data()
        if not self._dispatch_post(parsed.path, form, files):
            self._respond(
                HTTPStatus.NOT_FOUND,
                "Nicht gefunden.",
                content_type="text/plain; charset=utf-8",
            )

    def _render_catalog(
        self,
        query: dict[str, list[str]],
        filters: ViewFilters,
        modules: list,
        choices: PageChoices,
    ) -> str:
        """Build the catalog page response."""

        edit_id = query.get("edit", [""])[0]
        editing = self.app_state.repository.get_module(int(edit_id)) if edit_id.isdigit() else None
        page = CatalogPageData(
            modules=modules,
            counts=self.app_state.repository.count_by_level(),
            choices=choices,
            filters=filters,
            editing=editing,
            message=query.get("message", [""])[0],
            message_type=query.get("type", ["success"])[0],
        )
        return render_catalog_page(page)

    def _render_viewer(
        self,
        _path: str,
        query: dict[str, list[str]],
        filters: ViewFilters,
        modules: list,
        choices: PageChoices,
    ) -> str:
        """Build the single-module viewer response."""

        selected_module, selected_index = pick_viewer_module(
            modules,
            requested_id=query.get("id", [""])[0],
            randomize=query.get("random", [""])[0] == "1",
        )
        page = ViewerPageData(
            modules=modules,
            choices=choices,
            filters=filters,
            selected_module=selected_module,
            selected_index=selected_index,
            message=query.get("message", [""])[0],
            message_type=query.get("type", ["success"])[0],
        )
        return render_viewer_page(page)

    def _dispatch_post(
        self,
        path: str,
        form: dict[str, str],
        files: dict[str, UploadedFile],
    ) -> bool:
        """Dispatch POST routes and report whether a route matched."""

        direct_handlers = {
            "/modules": lambda: self._create_module(form),
            "/import/examples": self._import_examples,
            "/import/upload": lambda: self._import_uploaded_file(form, files),
            "/db/import": lambda: self._import_database_file(files),
            "/settings/levels": lambda: self._create_level(form),
            "/settings/starts": lambda: self._create_start_position(form),
        }
        handler = direct_handlers.get(path)
        if handler is not None:
            handler()
            return True
        return self._dispatch_update(path, form) or self._dispatch_delete(path)

    def _dispatch_update(self, path: str, form: dict[str, str]) -> bool:
        """Handle module update requests and report whether a route matched."""

        if not path.endswith("/update"):
            return False
        module_id = self._module_id_from_path(path, "/update")
        if module_id is None:
            return False
        self._update_module(module_id, form)
        return True

    def _dispatch_delete(self, path: str) -> bool:
        """Handle module delete requests and report whether a route matched."""

        if not path.endswith("/delete"):
            return False
        module_id = self._module_id_from_path(path, "/delete")
        if module_id is None:
            return False
        self.app_state.repository.delete_module(module_id)
        self._redirect("/", message="Modul gelöscht.", message_type="success")
        return True

    def _create_module(self, form: dict[str, str]) -> None:
        """Create a module and redirect back to the catalog."""

        try:
            record = self.app_state.repository.create_module(
                self._module_input_from_form(form)
            )
        except DuplicateModuleError as error:
            self._redirect(
                f"/?edit={error.existing_id}#editor",
                message=(
                    f"Dieses Modul existiert bereits als Datensatz "
                    f"{error.existing_id}."
                ),
                message_type="error",
            )
            return
        except ValueError as error:
            self._redirect("/", message=str(error), message_type="error")
            return

        self._redirect(
            f"/?edit={record.id}#module-{record.id}",
            message="Modul gespeichert.",
            message_type="success",
        )

    def _update_module(self, module_id: int, form: dict[str, str]) -> None:
        """Update a module and redirect back to the catalog."""

        try:
            record = self.app_state.repository.update_module(
                module_id,
                self._module_input_from_form(form),
            )
        except DuplicateModuleError as error:
            self._redirect(
                f"/?edit={error.existing_id}#editor",
                message=(
                    "Das aktualisierte Modul entspricht bereits Datensatz "
                    f"{error.existing_id}."
                ),
                message_type="error",
            )
            return
        except ValueError as error:
            self._redirect(
                f"/?edit={module_id}#editor",
                message=str(error),
                message_type="error",
            )
            return
        except KeyError:
            self._redirect("/", message="Modul nicht gefunden.", message_type="error")
            return

        self._redirect(
            f"/?edit={record.id}#module-{record.id}",
            message="Änderungen gespeichert.",
            message_type="success",
        )

    def _import_examples(self) -> None:
        """Import the bundled example file into the SQLite database."""

        if not self.app_state.example_file.exists():
            self._redirect(
                "/",
                message="Beispieldatei nicht gefunden.",
                message_type="error",
            )
            return
        added, skipped = self.app_state.repository.create_many(
            parse_callerschool_file(self.app_state.example_file)
        )
        self._redirect(
            "/",
            message=f"Beispiele importiert: {added} neu, {skipped} übersprungen.",
            message_type="success",
        )

    def _import_uploaded_file(
        self,
        form: dict[str, str],
        files: dict[str, UploadedFile],
    ) -> None:
        """Import all modules from an uploaded choreodb export file."""

        upload = files.get("module_file")
        if upload is None or not upload.content:
            self._redirect(
                "/",
                message="Bitte eine Datei zum Import auswählen.",
                message_type="error",
            )
            return

        try:
            content = upload.content.decode("utf-8")
        except UnicodeDecodeError:
            self._redirect(
                "/",
                message="Die Datei muss UTF-8-kodierter Text sein.",
                message_type="error",
            )
            return

        source_name = form.get("import_source", "").strip() or upload.filename or "Upload"
        start_position = form.get("import_start", "Static Square")
        if detect_upload_format(content) == "callerschool":
            modules = parse_callerschool_text(
                content,
                source_name=source_name,
                start_position=start_position,
            )
        else:
            modules = parse_choreodb_text(
                content,
                level=form.get("import_level", "MS"),
                start_position=start_position,
                source_name=source_name,
            )
        if not modules:
            self._redirect(
                "/",
                message="In der Datei wurden keine importierbaren Module gefunden.",
                message_type="error",
            )
            return

        added, skipped = self.app_state.repository.create_many(modules)
        self._redirect(
            "/",
            message=(
                f"Upload importiert: {added} neu, {skipped} übersprungen "
                f"aus {upload.filename or 'Upload'}."
            ),
            message_type="success",
        )

    def _import_database_file(self, files: dict[str, UploadedFile]) -> None:
        """Replace the current SQLite database with an uploaded database file."""

        upload = files.get("db_file")
        if upload is None or not upload.content:
            self._redirect(
                "/",
                message="Bitte eine SQLite-Datei zum Datenbank-Import auswählen.",
                message_type="error",
            )
            return

        try:
            replace_database_file(upload.content, self.app_state.db_path)
        except ValueError as error:
            self._redirect("/", message=str(error), message_type="error")
            return

        self.app_state.repository = ModuleRepository(self.app_state.db_path)
        self._redirect(
            "/",
            message=f"Datenbank importiert aus {upload.filename or 'Upload'}.",
            message_type="success",
        )

    def _create_level(self, form: dict[str, str]) -> None:
        """Create a new selectable level."""

        try:
            level_name = self.app_state.repository.create_level(form.get("level_name", ""))
        except ValueError as error:
            self._redirect("/", message=str(error), message_type="error")
            return
        self._redirect(
            "/",
            message=f"Level angelegt: {level_name}.",
            message_type="success",
        )

    def _create_start_position(self, form: dict[str, str]) -> None:
        """Create a new selectable start position."""

        try:
            start_name = self.app_state.repository.create_start_position(
                form.get("start_name", "")
            )
        except ValueError as error:
            self._redirect("/", message=str(error), message_type="error")
            return
        self._redirect(
            "/",
            message=f"Startposition angelegt: {start_name}.",
            message_type="success",
        )

    def _export_database(self) -> None:
        """Send the current SQLite database as a downloadable file."""

        payload = self.app_state.db_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/x-sqlite3")
        self.send_header(
            "Content-Disposition",
            'attachment; filename="square-cards-modules.sqlite3"',
        )
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _module_input_from_form(self, form: dict[str, str]) -> ModuleInput:
        """Convert posted form values into a repository input object."""

        return ModuleInput(
            title=form.get("title", ""),
            level=form.get("level", "MS"),
            start_position=form.get("start_position", "Static Square"),
            raw_text=form.get("raw_text", ""),
            source_name=form.get("source_name", ""),
        )

    def _read_request_data(self) -> tuple[dict[str, str], dict[str, UploadedFile]]:
        """Read either URL-encoded or multipart form data from the request."""

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length)
        content_type = self.headers.get("Content-Type", "")
        if content_type.startswith("multipart/form-data"):
            return self._parse_multipart_form(content_type, payload)
        form = parse_qs(payload.decode("utf-8"))
        return {key: values[0] for key, values in form.items()}, {}

    def _redirect(self, path: str, *, message: str, message_type: str) -> None:
        """Send a redirect with a status banner encoded in the URL."""

        base_path, fragment = path.split("#", 1) if "#" in path else (path, "")
        separator = "&" if "?" in path else "?"
        query = build_query({"message": message, "type": message_type})
        location = f"{base_path}{separator}{query}"
        if fragment:
            location = f"{location}#{fragment}"
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def _respond(
        self,
        status: HTTPStatus,
        body: str,
        *,
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        """Write a plain HTTP response."""

        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(  # pylint: disable=arguments-differ,redefined-builtin
        self,
        format: str,
        *args: object,
    ) -> None:
        """Silence the default request logging."""

        del format, args

    @staticmethod
    def _filters_from_query(query: dict[str, list[str]]) -> ViewFilters:
        """Build a typed filter object from parsed query parameters."""

        return ViewFilters(
            level=query.get("level", [""])[0],
            start=query.get("start", [""])[0],
            source=query.get("source", [""])[0],
            query=query.get("q", [""])[0],
        )

    @staticmethod
    def _module_id_from_path(path: str, suffix: str) -> int | None:
        """Extract a module id from a mutation route."""

        module_id = path.removeprefix("/modules/").removesuffix(suffix)
        return int(module_id) if module_id.isdigit() else None

    @staticmethod
    def _parse_multipart_form(
        content_type: str,
        payload: bytes,
    ) -> tuple[dict[str, str], dict[str, UploadedFile]]:
        """Parse a multipart form into fields and uploaded files."""

        headers = (
            f"Content-Type: {content_type}\r\n"
            "MIME-Version: 1.0\r\n"
            "\r\n"
        ).encode("utf-8")
        message = BytesParser(policy=default).parsebytes(headers + payload)

        fields: dict[str, str] = {}
        files: dict[str, UploadedFile] = {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            file_content = part.get_payload(decode=True) or b""
            filename = part.get_filename()
            if filename:
                files[name] = UploadedFile(filename=filename, content=file_content)
            else:
                fields[name] = part.get_content().strip()
        return fields, files


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    workspace: Path | None = None,
) -> None:
    """Start the local threaded HTTP server."""

    base_path = workspace or Path.cwd()
    app_state = create_app_state(base_path)

    class BoundHandler(ModuleRequestHandler):
        """Request handler with bound application state."""

    BoundHandler.app_state = app_state

    server = ThreadingHTTPServer((host, port), BoundHandler)
    print(f"Square Cards läuft auf http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def viewer_link(filters: dict[str, str] | ViewFilters, module_id: int | None = None) -> str:
    """Re-export the viewer URL helper for callers that import it from here."""

    return _viewer_link(filters, module_id)


REQUIRED_DB_COLUMNS = {
    "id",
    "title",
    "level",
    "start_position",
    "raw_text",
    "normalized_text",
    "module_hash",
    "source_name",
    "created_at",
    "updated_at",
}


def replace_database_file(database_bytes: bytes, destination: Path) -> None:
    """Validate and replace the active SQLite database file."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=".sqlite3",
        dir=destination.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(database_bytes)

    try:
        validate_database_file(temp_path)
        temp_path.replace(destination)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def validate_database_file(db_path: Path) -> None:
    """Ensure that a database file contains the expected modules schema."""

    try:
        connection = sqlite3.connect(db_path)
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(modules)").fetchall()
        }
    except sqlite3.DatabaseError as error:
        raise ValueError("Die hochgeladene Datei ist keine gueltige SQLite-Datenbank.") from error
    finally:
        if "connection" in locals():
            connection.close()

    if not columns:
        raise ValueError("Die SQLite-Datei enthaelt keine 'modules'-Tabelle.")
    if not REQUIRED_DB_COLUMNS.issubset(columns):
        raise ValueError("Die SQLite-Datei hat nicht das erwartete Square-Cards-Schema.")
