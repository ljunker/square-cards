"""HTTP server and request routing for the Square Cards web UI."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .importer import parse_callerschool_file
from .repository import DuplicateModuleError, ModuleInput, ModuleRepository
from .views import (
    CatalogPageData,
    ViewFilters,
    ViewerPageData,
    build_query,
    pick_selected_module,
    render_catalog_page,
    render_viewer_page,
    viewer_link,
)


@dataclass(slots=True)
class AppState:
    """Shared application state used by the request handler."""

    repository: ModuleRepository
    example_file: Path


def create_app_state(workspace: Path) -> AppState:
    """Create repository-backed application state for the given workspace."""

    data_dir = workspace / "data"
    repository = ModuleRepository(data_dir / "modules.sqlite3")
    example_file = workspace / "callerschool-pattern"
    if example_file.exists():
        repository.create_many(parse_callerschool_file(example_file))
    return AppState(repository=repository, example_file=example_file)


class ModuleRequestHandler(BaseHTTPRequestHandler):  # pylint: disable=invalid-name
    """Serve the catalog and viewer pages plus mutation endpoints."""

    app_state: AppState

    def do_HEAD(self) -> None:
        """Return a lightweight health response for known routes."""

        parsed = urlparse(self.path)
        if parsed.path not in {"/", "/viewer"}:
            self._respond(
                HTTPStatus.NOT_FOUND,
                "",
                content_type="text/plain; charset=utf-8",
            )
            return
        self._respond(HTTPStatus.OK, "")

    def do_GET(self) -> None:
        """Render the catalog or single-module viewer page."""

        parsed = urlparse(self.path)
        if parsed.path not in {"/", "/viewer"}:
            self._respond(
                HTTPStatus.NOT_FOUND,
                "Nicht gefunden.",
                content_type="text/plain; charset=utf-8",
            )
            return

        query = parse_qs(parsed.query)
        filters = self._filters_from_query(query)
        sources = self.app_state.repository.list_sources()
        modules = self.app_state.repository.list_modules(
            level=filters.level,
            start_position=filters.start,
            source_name=filters.source,
            query=filters.query,
        )
        page = (
            self._render_viewer(parsed.path, query, filters, modules, sources)
            if parsed.path == "/viewer"
            else self._render_catalog(query, filters, modules, sources)
        )
        self._respond(HTTPStatus.OK, page)

    def do_POST(self) -> None:
        """Handle create, update, delete and import actions."""

        parsed = urlparse(self.path)
        form = self._read_form_data()

        if parsed.path == "/modules":
            self._create_module(form)
            return
        if parsed.path == "/import/examples":
            self._import_examples()
            return
        if self._dispatch_update(parsed.path, form):
            return
        if self._dispatch_delete(parsed.path):
            return

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
        sources: tuple[str, ...],
    ) -> str:
        """Build the catalog page response."""

        edit_id = query.get("edit", [""])[0]
        editing = self.app_state.repository.get_module(int(edit_id)) if edit_id.isdigit() else None
        page = CatalogPageData(
            modules=modules,
            counts=self.app_state.repository.count_by_level(),
            sources=sources,
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
        sources: tuple[str, ...],
    ) -> str:
        """Build the single-module viewer response."""

        selected_module, selected_index = pick_selected_module(
            modules,
            query.get("id", [""])[0],
        )
        page = ViewerPageData(
            modules=modules,
            sources=sources,
            filters=filters,
            selected_module=selected_module,
            selected_index=selected_index,
            message=query.get("message", [""])[0],
            message_type=query.get("type", ["success"])[0],
        )
        return render_viewer_page(page)

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

    def _module_input_from_form(self, form: dict[str, str]) -> ModuleInput:
        """Convert posted form values into a repository input object."""

        return ModuleInput(
            title=form.get("title", ""),
            level=form.get("level", "MS"),
            start_position=form.get("start_position", "Static Square"),
            raw_text=form.get("raw_text", ""),
            source_name=form.get("source_name", ""),
        )

    def _read_form_data(self) -> dict[str, str]:
        """Read URL-encoded form data from the current request."""

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length).decode("utf-8")
        return {key: values[0] for key, values in parse_qs(payload).items()}

    def _redirect(self, path: str, *, message: str, message_type: str) -> None:
        """Send a redirect with a status banner encoded in the URL."""

        separator = "&" if "?" in path else "?"
        query = build_query({"message": message, "type": message_type})
        location = f"{path}{separator}{query}"
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

    def log_message(self, message_format: str, *args: object) -> None:
        """Silence the default request logging."""

        del message_format, args

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
