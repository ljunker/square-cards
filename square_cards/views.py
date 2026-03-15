"""HTML rendering helpers for the Square Cards web UI."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlencode

from .assets import APP_STYLES, VIEWER_FIT_SCRIPT
from .repository import LEVELS, START_POSITIONS, ModuleRecord


@dataclass(slots=True)
class ViewFilters:
    """Filter values shared between catalog and viewer pages."""

    level: str = ""
    start: str = ""
    source: str = ""
    query: str = ""

    def as_mapping(self) -> dict[str, str]:
        """Return filters in query-string form."""

        return {
            "level": self.level,
            "start": self.start,
            "source": self.source,
            "q": self.query,
        }


@dataclass(slots=True)
class CatalogPageData:
    """Data required to render the catalog and edit page."""

    modules: list[ModuleRecord]
    counts: dict[str, int]
    sources: tuple[str, ...]
    filters: ViewFilters
    editing: ModuleRecord | None
    message: str = ""
    message_type: str = "success"


@dataclass(slots=True)
class ViewerPageData:
    """Data required to render the single-module viewer page."""

    modules: list[ModuleRecord]
    sources: tuple[str, ...]
    filters: ViewFilters
    selected_module: ModuleRecord | None
    selected_index: int
    message: str = ""
    message_type: str = "success"


def build_query(filters: Mapping[str, str] | ViewFilters, **extra: str) -> str:
    """Build a query string while omitting empty values."""

    base = _filter_mapping(filters)
    params = {key: value for key, value in base.items() if value}
    params.update({key: value for key, value in extra.items() if value})

    return urlencode(params)


def viewer_link(filters: Mapping[str, str] | ViewFilters, module_id: int | None = None) -> str:
    """Build a viewer URL that preserves the current filter context."""

    query = build_query(filters, id=str(module_id) if module_id else "")
    return f"/viewer?{query}" if query else "/viewer"


def pick_selected_module(
    modules: list[ModuleRecord], requested_id: str
) -> tuple[ModuleRecord | None, int]:
    """Pick the requested module or fall back to the first filtered result."""

    if not modules:
        return None, -1
    if requested_id.isdigit():
        requested = int(requested_id)
        for index, module in enumerate(modules):
            if module.id == requested:
                return module, index
    return modules[0], 0


def render_catalog_page(page: CatalogPageData) -> str:
    """Render the catalog page with edit form, filters and module cards."""

    editor = _build_editor_state(page.editing)

    cards_markup = "\n".join(
        render_module_card(module, page.filters) for module in page.modules
    ) or _empty_catalog_markup()

    filter_options = {
        "level": render_options(
            ("",) + LEVELS,
            page.filters.level,
            empty_label="Alle Level",
        ),
        "start": render_options(
            ("",) + START_POSITIONS,
            page.filters.start,
            empty_label="Alle Starts",
        ),
        "source": render_options(
            ("",) + page.sources,
            page.filters.source,
            empty_label="Alle Quellen",
        ),
    }
    viewer_open_link = viewer_link(page.filters)

    return "\n".join(
        [
            "<!DOCTYPE html>",
            "<html lang=\"de\">",
            _render_head("Square Cards Modulverwaltung"),
            "<body>",
            '<div class="shell">',
            _render_catalog_hero(page.counts),
            render_banner(page.message, page.message_type),
            '<section class="controls">',
            _render_editor_panel(editor),
            _render_catalog_filter_panel(
                filter_options=filter_options,
                query_value=page.filters.query,
                viewer_open_link=viewer_open_link,
            ),
            "</section>",
            '<section class="catalog">',
            cards_markup,
            "</section>",
            "</div>",
            "</body>",
            "</html>",
        ]
    )


def render_viewer_page(page: ViewerPageData) -> str:
    """Render the full-screen single-module viewer page."""

    filter_options = {
        "level": render_options(
            ("",) + LEVELS,
            page.filters.level,
            empty_label="Alle Level",
        ),
        "start": render_options(
            ("",) + START_POSITIONS,
            page.filters.start,
            empty_label="Alle Starts",
        ),
        "source": render_options(
            ("",) + page.sources,
            page.filters.source,
            empty_label="Alle Quellen",
        ),
    }
    catalog_link = _catalog_link(page.filters)

    return "\n".join(
        [
            "<!DOCTYPE html>",
            "<html lang=\"de\">",
            _render_head("Square Cards Einzelansicht"),
            '<body class="viewer-page">',
            '<div class="viewer-shell">',
            render_banner(page.message, page.message_type),
            _render_viewer_toolbar(
                filters=page.filters,
                filter_options=filter_options,
                result_count=len(page.modules),
                catalog_link=catalog_link,
            ),
            '<section class="viewer-layout">',
            _render_viewer_body(page),
            "</section>",
            "</div>",
            f"<script>{VIEWER_FIT_SCRIPT}</script>",
            "</body>",
            "</html>",
        ]
    )


def render_banner(message: str, message_type: str) -> str:
    """Render a feedback banner or nothing for empty messages."""

    if not message:
        return ""
    return (
        f'<div class="banner {html.escape(message_type)}">'
        f"{html.escape(message)}</div>"
    )


def render_module_card(module: ModuleRecord, filters: ViewFilters) -> str:
    """Render a module card for the catalog grid."""

    calls_markup = "\n".join(
        f"<li>{html.escape(call)}</li>" for call in module.calls[:10]
    )
    full_calls_markup = "".join(
        f"<li>{html.escape(call)}</li>" for call in module.calls
    )
    extra_line = ""
    if len(module.calls) > 10:
        extra_line = f'<li>… {len(module.calls) - 10} weitere Calls</li>'
    source_line = (
        f"<div>Quelle: <strong>{html.escape(module.source_name)}</strong></div>"
        if module.source_name
        else ""
    )
    return "\n".join(
        [
            f'<article class="panel module-card" id="module-{module.id}">',
            '<div class="module-top">',
            "<div>",
            f'<h3 class="module-title">{html.escape(module.title)}</h3>',
            "</div>",
            '<div class="badge-row">',
            f'<span class="badge">{html.escape(module.level)}</span>',
            f'<span class="badge start">{html.escape(module.start_position)}</span>',
            "</div>",
            "</div>",
            '<div class="module-meta">',
            source_line,
            f"<div>{len(module.calls)} Calls</div>",
            f"<div>Aktualisiert: {html.escape(module.updated_at)}</div>",
            "</div>",
            f'<div class="hash">{html.escape(module.module_hash)}</div>',
            '<ol class="call-list">',
            calls_markup,
            extra_line,
            "</ol>",
            "<details>",
            "<summary>Komplettes Modul anzeigen</summary>",
            '<ol class="call-list">',
            full_calls_markup,
            "</ol>",
            "</details>",
            '<div class="module-actions">',
            f'<a class="ghost-link" href="{viewer_link(filters, module.id)}">Ansehen</a>',
            f'<a class="button-link" href="/?edit={module.id}#editor">Bearbeiten</a>',
            f'<form action="/modules/{module.id}/delete" method="post">',
            '<button type="submit" class="danger">Löschen</button>',
            "</form>",
            "</div>",
            "</article>",
        ]
    )


def render_options(
    values: tuple[str, ...],
    current_value: str,
    *,
    empty_label: str | None = None,
) -> str:
    """Render select options for a tuple of values."""

    options: list[str] = []
    for value in values:
        label = empty_label if not value and empty_label is not None else value
        selected = " selected" if value == current_value else ""
        options.append(
            f'<option value="{html.escape(value)}"{selected}>'
            f"{html.escape(label)}</option>"
        )
    return "".join(options)


def _render_head(title: str) -> str:
    """Render the HTML head shared by all pages."""

    return "\n".join(
        [
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{html.escape(title)}</title>",
            "  <style>",
            APP_STYLES,
            "  </style>",
            "</head>",
        ]
    )


def _render_catalog_hero(counts: dict[str, int]) -> str:
    """Render the top hero section for the catalog page."""

    stats_markup = render_stats(counts)
    return "\n".join(
        [
            '<section class="hero">',
            '<div class="panel hero-copy">',
            '<div class="eyebrow">Caller School Module Catalog</div>',
            "<h1>Square-Dance-Module mit SQLite verwalten.</h1>",
            (
                "<p>Module werden aus ihrem normalisierten Call-Text gehasht. "
                "Dadurch erkennst du Duplikate zuverlässig, pflegst Level und "
                "Startposition sauber in SQLite und filterst die Sammlung in "
                "einer kompakten Web-Oberfläche.</p>"
            ),
            "</div>",
            '<aside class="panel hero-side">',
            "<h2>Bestand</h2>",
            (
                "<p>Die vorhandenen Beispiele aus "
                "<code>callerschool-pattern</code> werden automatisch importiert. "
                "Weitere Einträge kannst du direkt im Browser anlegen oder "
                "bearbeiten.</p>"
            ),
            f'<div class="stats">{stats_markup}</div>',
            "</aside>",
            "</section>",
        ]
    )


def _render_editor_panel(editor: Mapping[str, str]) -> str:
    """Render the create/edit form panel."""

    level_options = render_options(LEVELS, editor["level"])
    start_options = render_options(START_POSITIONS, editor["start"])
    return "\n".join(
        [
            '<div class="panel form-panel" id="editor">',
            '<div class="panel-header">',
            "<div>",
            f"<h2>{html.escape(editor['page_title'])}</h2>",
            (
                "<p>Hash, Normalisierung und Duplicate-Prüfung passieren "
                "serverseitig beim Speichern.</p>"
            ),
            "</div>",
            editor["form_cancel"],
            "</div>",
            f'<form action="{html.escape(editor["submit_action"])}" method="post">',
            '<div class="grid">',
            "<label>",
            "Titel",
            (
                f'<input name="title" value="{html.escape(editor["title"])}" '
                'placeholder="z. B. Heads Box The Gnat">'
            ),
            "</label>",
            "</div>",
            '<div class="grid two">',
            "<label>",
            "Level",
            f'<select name="level">{level_options}</select>',
            "</label>",
            "<label>",
            "Start",
            f'<select name="start_position">{start_options}</select>',
            "</label>",
            "</div>",
            '<div class="grid">',
            "<label>",
            "Quelle",
            (
                f'<input name="source_name" value="{html.escape(editor["source"])}" '
                'placeholder="z. B. callerschool-pattern">'
            ),
            "</label>",
            "<label>",
            "Modultext",
            (
                '<textarea name="raw_text" placeholder="Eine Call-Zeile pro Zeile" '
                f'required>{html.escape(editor["raw_text"])}</textarea>'
            ),
            "</label>",
            "</div>",
            '<div class="actions">',
            f"<button type=\"submit\">{html.escape(editor['submit_label'])}</button>",
            "</div>",
            "</form>",
            "</div>",
        ]
    )


def _render_catalog_filter_panel(
    *,
    filter_options: Mapping[str, str],
    query_value: str,
    viewer_open_link: str,
) -> str:
    """Render the catalog filter and import controls."""

    return "\n".join(
        [
            '<div class="panel filter-panel">',
            '<div class="panel-header">',
            "<div>",
            "<h2>Anzeige &amp; Import</h2>",
            (
                "<p>Filtere nach Level, Startposition, Quelle oder Freitext. "
                "Die Suche läuft über Titel, Quelle, Hash und Modultext.</p>"
            ),
            "</div>",
            "</div>",
            '<form action="/" method="get" class="filters">',
            '<div class="grid two">',
            "<label>",
            "Level",
            f'<select name="level">{filter_options["level"]}</select>',
            "</label>",
            "<label>",
            "Start",
            f'<select name="start">{filter_options["start"]}</select>',
            "</label>",
            "</div>",
            "<label>",
            "Quelle",
            f'<select name="source">{filter_options["source"]}</select>',
            "</label>",
            "<label>",
            "Suche",
            (
                f'<input name="q" value="{html.escape(query_value)}" '
                'placeholder="Titel, Call, Hash, Quelle">'
            ),
            "</label>",
            '<div class="actions">',
            '<button type="submit">Filter anwenden</button>',
            '<a class="ghost-link" href="/">Zurücksetzen</a>',
            f'<a class="button-link" href="{viewer_open_link}">Einzelansicht</a>',
            "</div>",
            "</form>",
            '<form action="/import/examples" method="post">',
            '<div class="actions">',
            '<button type="submit">Beispiele nachimportieren</button>',
            "</div>",
            "</form>",
            "</div>",
        ]
    )


def _render_viewer_toolbar(
    *,
    filters: ViewFilters,
    filter_options: Mapping[str, str],
    result_count: int,
    catalog_link: str,
) -> str:
    """Render the compact toolbar above the single-module viewer."""

    return "\n".join(
        [
            '<section class="panel viewer-toolbar slim">',
            '<form action="/viewer" method="get" class="viewer-filter-form">',
            '<div class="viewer-filter-grid">',
            "<label>",
            "Level",
            f'<select name="level">{filter_options["level"]}</select>',
            "</label>",
            "<label>",
            "Start",
            f'<select name="start">{filter_options["start"]}</select>',
            "</label>",
            "<label>",
            "Quelle",
            f'<select name="source">{filter_options["source"]}</select>',
            "</label>",
            "<label>",
            "Suche",
            (
                f'<input name="q" value="{html.escape(filters.query)}" '
                'placeholder="Titel, Call, Hash, Quelle">'
            ),
            "</label>",
            '<div class="viewer-filter-actions">',
            '<button type="submit">Anwenden</button>',
            '<a class="ghost-link" href="/viewer">Reset</a>',
            f'<a class="ghost-link" href="{catalog_link}">Verwaltung</a>',
            "</div>",
            "</div>",
            (
                f'<div class="viewer-filter-meta">{result_count} Modul(e) '
                "in der aktuellen Auswahl</div>"
            ),
            "</form>",
            "</section>",
        ]
    )


def _render_viewer_body(page: ViewerPageData) -> str:
    """Render the body of the single-module viewer page."""

    if page.selected_module is None:
        return (
            '<div class="panel viewer-stage viewer-empty">'
            "Keine Module für die aktuellen Filter gefunden."
            "</div>"
        )

    previous_link = _viewer_nav_label("Vorheriges")
    next_link = _viewer_nav_label("Nächstes")

    if page.selected_index > 0:
        previous_module = page.modules[page.selected_index - 1]
        previous_link = (
            f'<a class="ghost-link" href="{viewer_link(page.filters, previous_module.id)}">'
            "Vorheriges</a>"
        )
    if page.selected_index < len(page.modules) - 1:
        next_module = page.modules[page.selected_index + 1]
        next_link = (
            f'<a class="button-link" href="{viewer_link(page.filters, next_module.id)}">'
            "Nächstes</a>"
        )

    call_items = "".join(
        f"<li>{html.escape(call)}</li>" for call in page.selected_module.calls
    )
    return "\n".join(
        [
            '<div class="viewer-body">',
            f'<div class="viewer-nav">{previous_link}</div>',
            (
                f'<article class="panel viewer-stage viewer-card" '
                f'id="module-{page.selected_module.id}">'
            ),
            f'<ol class="viewer-module-list">{call_items}</ol>',
            "</article>",
            f'<div class="viewer-nav">{next_link}</div>',
            "</div>",
        ]
    )


def render_stats(counts: dict[str, int]) -> str:
    """Render the count badges shown in the catalog hero."""

    return "\n".join(
        (
            f'<div class="stat-pill"><span>{html.escape(level)}</span>'
            f"<strong>{count}</strong></div>"
        )
        for level, count in counts.items()
    )


def _viewer_nav_label(label: str) -> str:
    """Render a disabled navigation placeholder."""

    return f'<span class="nav-placeholder">{html.escape(label)}</span>'


def _catalog_link(filters: ViewFilters) -> str:
    """Build a catalog link that preserves the current filter context."""

    query = build_query(filters)
    return f"/?{query}" if query else "/"


def _build_editor_state(editing: ModuleRecord | None) -> dict[str, str]:
    """Build the form state used by the catalog editor panel."""

    if editing is None:
        return {
            "page_title": "Neues Modul anlegen",
            "submit_label": "Modul anlegen",
            "submit_action": "/modules",
            "title": "",
            "level": "MS",
            "start": "Static Square",
            "raw_text": "",
            "source": "",
            "form_cancel": "",
        }
    return {
        "page_title": "Modul bearbeiten",
        "submit_label": "Modul speichern",
        "submit_action": f"/modules/{editing.id}/update",
        "title": editing.title,
        "level": editing.level,
        "start": editing.start_position,
        "raw_text": editing.raw_text,
        "source": editing.source_name,
        "form_cancel": '<a class="ghost-link" href="/">Bearbeitung abbrechen</a>',
    }


def _empty_catalog_markup() -> str:
    """Render the catalog empty state."""

    return (
        '<div class="empty-state">Keine Module gefunden. '
        "Lege ein neues Modul an oder importiere die Beispiele.</div>"
    )


def _filter_mapping(filters: Mapping[str, str] | ViewFilters) -> Mapping[str, str]:
    """Return a mapping for either raw filter dicts or typed filter objects."""

    if isinstance(filters, ViewFilters):
        return filters.as_mapping()
    return filters
