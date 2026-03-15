from __future__ import annotations

import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlparse

from .importer import parse_callerschool_file
from .repository import (
    LEVELS,
    START_POSITIONS,
    DuplicateModuleError,
    ModuleInput,
    ModuleRecord,
    ModuleRepository,
)


def create_app_state(workspace: Path) -> SimpleNamespace:
    data_dir = workspace / "data"
    repository = ModuleRepository(data_dir / "modules.sqlite3")
    example_file = workspace / "callerschool-pattern"
    if example_file.exists():
        repository.create_many(parse_callerschool_file(example_file))
    return SimpleNamespace(repository=repository, example_file=example_file)


def styles() -> str:
    return """
    :root {
      color-scheme: light;
      --bg: #f4efe6;
      --panel: rgba(255, 252, 246, 0.92);
      --panel-strong: #fffaf2;
      --ink: #1f2a23;
      --muted: #5f665f;
      --line: rgba(31, 42, 35, 0.12);
      --accent: #1f6b52;
      --accent-soft: rgba(31, 107, 82, 0.12);
      --highlight: #bb4d2c;
      --shadow: 0 22px 70px rgba(52, 35, 17, 0.12);
      --radius: 22px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(255, 200, 130, 0.35), transparent 28%),
        radial-gradient(circle at bottom right, rgba(31, 107, 82, 0.16), transparent 24%),
        linear-gradient(135deg, #f8f2e7 0%, #efe5d7 55%, #e3dbc9 100%);
      min-height: 100vh;
    }
    body.viewer-page {
      min-height: 100dvh;
      height: 100dvh;
      overflow: hidden;
    }
    .shell {
      width: min(1240px, calc(100% - 32px));
      margin: 28px auto 40px;
    }
    .viewer-shell {
      width: min(1240px, calc(100% - 20px));
      min-height: 100dvh;
      height: 100dvh;
      margin: 0 auto;
      padding: 10px 0;
      display: grid;
      grid-template-rows: auto auto 1fr;
      gap: 10px;
      overflow: hidden;
    }
    .hero {
      display: grid;
      gap: 18px;
      grid-template-columns: 1.25fr 0.95fr;
      align-items: stretch;
      margin-bottom: 24px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }
    .hero-copy {
      padding: 28px;
    }
    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--highlight);
      font-size: 0.75rem;
      margin-bottom: 12px;
      font-weight: 700;
    }
    h1 {
      margin: 0 0 12px;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 0.94;
      letter-spacing: -0.04em;
      max-width: 12ch;
    }
    .hero-copy p {
      margin: 0;
      color: var(--muted);
      font-size: 1.02rem;
      line-height: 1.55;
      max-width: 64ch;
    }
    .hero-side {
      padding: 24px;
      display: grid;
      gap: 16px;
      align-content: center;
      background:
        linear-gradient(160deg, rgba(31, 107, 82, 0.95), rgba(22, 70, 54, 0.95)),
        linear-gradient(160deg, rgba(255,255,255,0.12), rgba(255,255,255,0));
      color: #f8f4ec;
    }
    .hero-side h2 {
      margin: 0;
      font-size: 1.2rem;
      letter-spacing: -0.02em;
    }
    .hero-side p {
      margin: 0;
      color: rgba(248, 244, 236, 0.86);
      line-height: 1.5;
    }
    .stats {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .stat-pill {
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.16);
      border-radius: 999px;
      padding: 10px 14px;
      display: inline-flex;
      gap: 8px;
      align-items: center;
    }
    .stat-pill span {
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .banner {
      margin-bottom: 18px;
      border-radius: 16px;
      padding: 14px 16px;
      font-weight: 600;
    }
    .banner.success {
      background: rgba(31, 107, 82, 0.12);
      color: #174736;
      border: 1px solid rgba(31, 107, 82, 0.18);
    }
    .banner.error {
      background: rgba(187, 77, 44, 0.12);
      color: #7b2d15;
      border: 1px solid rgba(187, 77, 44, 0.18);
    }
    .controls {
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: 22px;
      margin-bottom: 24px;
    }
    .form-panel, .filter-panel, .viewer-toolbar, .viewer-stage {
      padding: 22px;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      margin-bottom: 18px;
    }
    .panel-header h2 {
      margin: 0 0 4px;
      font-size: 1.3rem;
    }
    .panel-header p {
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }
    form {
      margin: 0;
    }
    .grid {
      display: grid;
      gap: 14px;
    }
    .grid.two {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .grid.three {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    label {
      display: grid;
      gap: 8px;
      font-weight: 600;
      font-size: 0.95rem;
    }
    input, select, textarea, button {
      font: inherit;
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid rgba(31, 42, 35, 0.16);
      border-radius: 14px;
      padding: 12px 14px;
      background: var(--panel-strong);
      color: var(--ink);
    }
    textarea {
      min-height: 240px;
      resize: vertical;
      line-height: 1.45;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-top: 16px;
    }
    button, .button-link, .ghost-link {
      border: none;
      border-radius: 999px;
      padding: 12px 18px;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: transform 140ms ease, box-shadow 140ms ease, background 140ms ease;
    }
    button:hover, .button-link:hover, .ghost-link:hover {
      transform: translateY(-1px);
    }
    button, .button-link {
      background: var(--accent);
      color: #f8f4ec;
      box-shadow: 0 14px 30px rgba(31, 107, 82, 0.22);
    }
    .ghost-link {
      background: transparent;
      color: var(--ink);
      border: 1px solid var(--line);
    }
    .danger {
      background: rgba(187, 77, 44, 0.12);
      color: #7b2d15;
      box-shadow: none;
    }
    .filters {
      display: grid;
      gap: 12px;
    }
    .filters .actions {
      margin-top: 8px;
    }
    .catalog {
      display: grid;
      gap: 18px;
      grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
    }
    .module-card {
      padding: 20px;
      display: grid;
      gap: 16px;
      position: relative;
      overflow: hidden;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.76), rgba(255,248,238,0.92)),
        radial-gradient(circle at top right, rgba(31, 107, 82, 0.08), transparent 38%);
    }
    .module-card::after {
      content: "";
      position: absolute;
      inset: auto -30px -46px auto;
      width: 120px;
      height: 120px;
      border-radius: 50%;
      background: rgba(255, 186, 119, 0.14);
      pointer-events: none;
    }
    .module-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
    }
    .module-title {
      margin: 0;
      font-size: 1.15rem;
      line-height: 1.15;
      letter-spacing: -0.02em;
    }
    .badge-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 10px;
      border-radius: 999px;
      font-size: 0.76rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
      background: rgba(31, 107, 82, 0.08);
      color: var(--accent);
    }
    .badge.start {
      background: rgba(187, 77, 44, 0.1);
      color: #9a3f20;
    }
    .module-meta {
      color: var(--muted);
      font-size: 0.92rem;
      display: grid;
      gap: 5px;
    }
    .hash {
      font-family: "SFMono-Regular", ui-monospace, monospace;
      font-size: 0.83rem;
      word-break: break-all;
      background: rgba(31, 42, 35, 0.05);
      border-radius: 14px;
      padding: 10px 12px;
    }
    .call-list {
      margin: 0;
      padding-left: 22px;
      display: grid;
      gap: 8px;
      line-height: 1.45;
    }
    details {
      border-top: 1px solid var(--line);
      padding-top: 14px;
    }
    summary {
      cursor: pointer;
      font-weight: 700;
    }
    .module-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
    }
    .module-actions form {
      display: inline;
    }
    .viewer-layout {
      display: grid;
      gap: 20px;
      max-width: 1180px;
      margin: 0 auto;
      height: 100%;
      min-height: 0;
    }
    .viewer-toolbar.slim {
      padding: 10px 14px;
    }
    .viewer-filter-form {
      display: grid;
      gap: 8px;
    }
    .viewer-filter-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: minmax(0, 160px) minmax(0, 180px) minmax(0, 220px) minmax(220px, 1fr) auto;
      align-items: end;
    }
    .viewer-filter-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: flex-end;
    }
    .viewer-filter-meta {
      color: var(--muted);
      font-size: 0.82rem;
      padding-left: 2px;
    }
    .viewer-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      margin-bottom: 16px;
    }
    .viewer-header h2 {
      margin: 0 0 6px;
      font-size: clamp(1.8rem, 3vw, 2.6rem);
      line-height: 1;
      letter-spacing: -0.04em;
    }
    .viewer-body {
      display: grid;
      gap: 16px;
      grid-template-columns: minmax(110px, 130px) minmax(0, 1fr) minmax(110px, 130px);
      align-items: stretch;
      height: 100%;
      min-height: 0;
    }
    .viewer-card {
      padding: 28px;
      max-width: 780px;
      width: 100%;
      margin: 0 auto;
      display: flex;
      align-items: center;
      height: 100%;
      min-height: 0;
      overflow: hidden;
    }
    .viewer-position {
      font-size: 0.9rem;
      color: var(--muted);
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .nav-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .nav-row .button-link,
    .nav-row .ghost-link {
      min-width: 120px;
    }
    .viewer-nav {
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .viewer-nav .button-link,
    .viewer-nav .ghost-link,
    .nav-placeholder {
      width: 100%;
      min-height: 64px;
    }
    .nav-placeholder {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: rgba(31, 42, 35, 0.38);
      background: rgba(255,255,255,0.35);
      font-weight: 700;
    }
    .viewer-empty {
      padding: 48px 28px;
      text-align: center;
      color: var(--muted);
    }
    .viewer-module-list {
      margin: 0;
      padding-left: 42px;
      width: 100%;
      display: grid;
      gap: 16px;
      font-size: 2rem;
      line-height: 1.28;
      letter-spacing: -0.01em;
      overflow: hidden;
    }
    .empty-state {
      grid-column: 1 / -1;
      padding: 42px 28px;
      border: 1px dashed rgba(31, 42, 35, 0.2);
      border-radius: var(--radius);
      text-align: center;
      color: var(--muted);
      background: rgba(255, 250, 242, 0.7);
    }
    @media (max-width: 980px) {
      .hero, .controls {
        grid-template-columns: 1fr;
      }
      .viewer-filter-grid {
        grid-template-columns: 1fr 1fr;
      }
      .viewer-filter-actions {
        justify-content: flex-start;
        grid-column: 1 / -1;
      }
      .viewer-body {
        grid-template-columns: 94px minmax(0, 1fr) 94px;
      }
    }
    @media (max-width: 700px) {
      .shell {
        width: min(100% - 18px, 1240px);
      }
      .viewer-shell {
        width: min(100% - 12px, 1240px);
        padding: 6px 0;
        gap: 8px;
      }
      .grid.two, .grid.three, .viewer-filter-grid {
        grid-template-columns: 1fr;
      }
      .hero-copy, .hero-side, .form-panel, .filter-panel, .module-card, .viewer-toolbar, .viewer-stage, .viewer-card {
        padding: 14px;
      }
      .viewer-header, .module-top {
        flex-direction: column;
      }
      .viewer-module-list {
        padding-left: 28px;
        gap: 10px;
      }
      .viewer-nav .button-link,
      .viewer-nav .ghost-link,
      .nav-placeholder {
        min-height: 52px;
        min-width: 0;
        padding: 10px 8px;
        font-size: 0.9rem;
      }
    }
    """


def render_banner(message: str, message_type: str) -> str:
    if not message:
        return ""
    return f'<div class="banner {html.escape(message_type)}">{html.escape(message)}</div>'


def render_stats(counts: dict[str, int]) -> str:
    return "\n".join(
        f'<div class="stat-pill"><span>{html.escape(level)}</span><strong>{count}</strong></div>'
        for level, count in counts.items()
    )


def build_query(filters: dict[str, str], **extra: str) -> str:
    params = {key: value for key, value in filters.items() if value}
    params.update({key: value for key, value in extra.items() if value})
    return urlencode(params)


def viewer_link(filters: dict[str, str], module_id: int | None = None) -> str:
    query = build_query(filters, id=str(module_id) if module_id else "")
    return f"/viewer?{query}" if query else "/viewer"


def pick_selected_module(
    modules: list[ModuleRecord],
    requested_id: str,
) -> tuple[ModuleRecord | None, int]:
    if not modules:
        return None, -1
    if requested_id.isdigit():
        requested = int(requested_id)
        for index, module in enumerate(modules):
            if module.id == requested:
                return module, index
    return modules[0], 0


def render_page(
    *,
    modules: list[ModuleRecord],
    counts: dict[str, int],
    sources: tuple[str, ...],
    filters: dict[str, str],
    editing: ModuleRecord | None,
    message: str,
    message_type: str,
) -> str:
    page_title = "Modul bearbeiten" if editing else "Neues Modul anlegen"
    submit_label = "Modul speichern" if editing else "Modul anlegen"
    submit_action = f"/modules/{editing.id}/update" if editing else "/modules"
    editor_title = editing.title if editing else filters.get("draft_title", "")
    editor_level = editing.level if editing else "MS"
    editor_start = editing.start_position if editing else "Static Square"
    editor_text = editing.raw_text if editing else filters.get("draft_text", "")
    editor_source = editing.source_name if editing else filters.get("draft_source", "")

    current_filters = {
        "level": filters.get("level", ""),
        "start": filters.get("start", ""),
        "source": filters.get("source", ""),
        "q": filters.get("q", ""),
    }
    cards_markup = "\n".join(render_module_card(module, current_filters) for module in modules) or (
        '<div class="empty-state">Keine Module gefunden. Lege ein neues Modul an '
        "oder importiere die Beispiele.</div>"
    )

    stats_markup = render_stats(counts)

    level_options = render_options(LEVELS, editor_level)
    start_options = render_options(START_POSITIONS, editor_start)
    filter_level_options = render_options(("",) + LEVELS, filters.get("level", ""), empty_label="Alle Level")
    filter_start_options = render_options(
        ("",) + START_POSITIONS,
        filters.get("start", ""),
        empty_label="Alle Starts",
    )
    filter_source_options = render_options(("",) + sources, filters.get("source", ""), empty_label="Alle Quellen")

    banner_markup = (
        render_banner(message, message_type)
    )
    reset_link = "/"
    form_cancel = (
        '<a class="ghost-link" href="/">Bearbeitung abbrechen</a>' if editing else ""
    )
    viewer_open_link = viewer_link(current_filters)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Square Cards Modulverwaltung</title>
  <style>
    {styles()}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="panel hero-copy">
        <div class="eyebrow">Caller School Module Catalog</div>
        <h1>Square-Dance-Module mit SQLite verwalten.</h1>
        <p>Module werden aus ihrem normalisierten Call-Text gehasht. Dadurch erkennst du Duplikate zuverlässig, pflegst Level und Startposition sauber in SQLite und filterst die Sammlung in einer kompakten Web-Oberfläche.</p>
      </div>
      <aside class="panel hero-side">
        <h2>Bestand</h2>
        <p>Die zwei vorhandenen Beispiele aus <code>callerschool-pattern</code> werden automatisch importiert. Weitere Einträge kannst du direkt im Browser anlegen oder bearbeiten.</p>
        <div class="stats">{stats_markup}</div>
      </aside>
    </section>
    {banner_markup}
    <section class="controls">
      <div class="panel form-panel" id="editor">
        <div class="panel-header">
          <div>
            <h2>{html.escape(page_title)}</h2>
            <p>Hash, Normalisierung und Duplicate-Prüfung passieren serverseitig beim Speichern.</p>
          </div>
          {form_cancel}
        </div>
        <form action="{html.escape(submit_action)}" method="post">
          <div class="grid">
            <label>
              Titel
              <input name="title" value="{html.escape(editor_title)}" placeholder="z. B. Heads Box The Gnat">
            </label>
          </div>
          <div class="grid two">
            <label>
              Level
              <select name="level">{level_options}</select>
            </label>
            <label>
              Start
              <select name="start_position">{start_options}</select>
            </label>
          </div>
          <div class="grid">
            <label>
              Quelle
              <input name="source_name" value="{html.escape(editor_source)}" placeholder="z. B. callerschool-pattern">
            </label>
            <label>
              Modultext
              <textarea name="raw_text" placeholder="Eine Call-Zeile pro Zeile" required>{html.escape(editor_text)}</textarea>
            </label>
          </div>
          <div class="actions">
            <button type="submit">{html.escape(submit_label)}</button>
          </div>
        </form>
      </div>
      <div class="panel filter-panel">
        <div class="panel-header">
          <div>
            <h2>Anzeige &amp; Import</h2>
            <p>Filtere nach Level, Startposition oder Freitext. Die Suche läuft über Titel, Quelle, Hash und Modultext.</p>
          </div>
        </div>
        <form action="/" method="get" class="filters">
          <div class="grid two">
            <label>
              Level
              <select name="level">{filter_level_options}</select>
            </label>
            <label>
              Start
              <select name="start">{filter_start_options}</select>
            </label>
          </div>
          <label>
            Quelle
            <select name="source">{filter_source_options}</select>
          </label>
          <label>
            Suche
            <input name="q" value="{html.escape(filters.get('q', ''))}" placeholder="Titel, Call, Hash, Quelle">
          </label>
          <div class="actions">
            <button type="submit">Filter anwenden</button>
            <a class="ghost-link" href="{reset_link}">Zurücksetzen</a>
            <a class="button-link" href="{viewer_open_link}">Einzelansicht</a>
          </div>
        </form>
        <form action="/import/examples" method="post">
          <div class="actions">
            <button type="submit">Beispiele nachimportieren</button>
          </div>
        </form>
      </div>
    </section>
    <section class="catalog">
      {cards_markup}
    </section>
  </div>
</body>
</html>
"""


def render_viewer_page(
    *,
    modules: list[ModuleRecord],
    counts: dict[str, int],
    sources: tuple[str, ...],
    filters: dict[str, str],
    selected_module: ModuleRecord | None,
    selected_index: int,
    message: str,
    message_type: str,
) -> str:
    filter_level_options = render_options(("",) + LEVELS, filters.get("level", ""), empty_label="Alle Level")
    filter_start_options = render_options(
        ("",) + START_POSITIONS,
        filters.get("start", ""),
        empty_label="Alle Starts",
    )
    filter_source_options = render_options(("",) + sources, filters.get("source", ""), empty_label="Alle Quellen")
    banner_markup = render_banner(message, message_type)
    catalog_link = f"/?{build_query(filters)}" if build_query(filters) else "/"
    result_count = len(modules)

    if selected_module is None:
        viewer_body = """
        <div class="panel viewer-stage viewer-empty">
          Keine Module für die aktuellen Filter gefunden.
        </div>
        """
    else:
        previous_link = '<span class="nav-placeholder">Vorheriges</span>'
        next_link = '<span class="nav-placeholder">Nächstes</span>'
        if selected_index > 0:
            previous_link = f'<a class="ghost-link" href="{viewer_link(filters, modules[selected_index - 1].id)}">Vorheriges</a>'
        if selected_index < len(modules) - 1:
            next_link = f'<a class="button-link" href="{viewer_link(filters, modules[selected_index + 1].id)}">Nächstes</a>'
        viewer_body = f"""
        <div class="viewer-body">
          <div class="viewer-nav">
            {previous_link}
          </div>
          <article class="panel viewer-stage viewer-card" id="module-{selected_module.id}">
            <ol class="viewer-module-list">
              {''.join(f"<li>{html.escape(call)}</li>" for call in selected_module.calls)}
            </ol>
          </article>
          <div class="viewer-nav">
            {next_link}
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Square Cards Einzelansicht</title>
  <style>
    {styles()}
  </style>
</head>
<body class="viewer-page">
  <div class="viewer-shell">
    {banner_markup}
    <section class="panel viewer-toolbar slim">
      <form action="/viewer" method="get" class="viewer-filter-form">
        <div class="viewer-filter-grid">
          <label>
            Level
            <select name="level">{filter_level_options}</select>
          </label>
          <label>
            Start
            <select name="start">{filter_start_options}</select>
          </label>
          <label>
            Quelle
            <select name="source">{filter_source_options}</select>
          </label>
          <label>
            Suche
            <input name="q" value="{html.escape(filters.get('q', ''))}" placeholder="Titel, Call, Hash, Quelle">
          </label>
          <div class="viewer-filter-actions">
            <button type="submit">Anwenden</button>
            <a class="ghost-link" href="/viewer">Reset</a>
            <a class="ghost-link" href="{catalog_link}">Verwaltung</a>
          </div>
        </div>
        <div class="viewer-filter-meta">
          {result_count} Modul(e) in der aktuellen Auswahl
        </div>
      </form>
    </section>
    <section class="viewer-layout">
      {viewer_body}
    </section>
  </div>
  <script>
    (() => {{
      const steps = [
        {{ size: 2.1, gap: 16, line: 1.28 }},
        {{ size: 1.9, gap: 15, line: 1.26 }},
        {{ size: 1.75, gap: 14, line: 1.24 }},
        {{ size: 1.6, gap: 13, line: 1.22 }},
        {{ size: 1.48, gap: 12, line: 1.2 }},
        {{ size: 1.36, gap: 11, line: 1.18 }},
        {{ size: 1.24, gap: 10, line: 1.16 }},
        {{ size: 1.14, gap: 9, line: 1.14 }},
        {{ size: 1.04, gap: 8, line: 1.12 }},
        {{ size: 0.96, gap: 7, line: 1.1 }}
      ];

      function fitViewerModule() {{
        const card = document.querySelector('.viewer-card');
        const list = document.querySelector('.viewer-module-list');
        if (!card || !list) {{
          return;
        }}

        for (const step of steps) {{
          list.style.fontSize = `${{step.size}}rem`;
          list.style.gap = `${{step.gap}}px`;
          list.style.lineHeight = String(step.line);
          if (list.scrollHeight <= card.clientHeight - 4) {{
            return;
          }}
        }}
      }}

      window.addEventListener('load', fitViewerModule);
      window.addEventListener('resize', fitViewerModule);
    }})();
  </script>
</body>
</html>
"""


def render_module_card(module: ModuleRecord, filters: dict[str, str]) -> str:
    calls_markup = "\n".join(f"<li>{html.escape(call)}</li>" for call in module.calls[:10])
    extra_line = ""
    if len(module.calls) > 10:
        extra_line = f'<li>… {len(module.calls) - 10} weitere Calls</li>'
    source_line = (
        f"<div>Quelle: <strong>{html.escape(module.source_name)}</strong></div>"
        if module.source_name
        else ""
    )
    return f"""
    <article class="panel module-card" id="module-{module.id}">
      <div class="module-top">
        <div>
          <h3 class="module-title">{html.escape(module.title)}</h3>
        </div>
        <div class="badge-row">
          <span class="badge">{html.escape(module.level)}</span>
          <span class="badge start">{html.escape(module.start_position)}</span>
        </div>
      </div>
      <div class="module-meta">
        {source_line}
        <div>{len(module.calls)} Calls</div>
        <div>Aktualisiert: {html.escape(module.updated_at)}</div>
      </div>
      <div class="hash">{html.escape(module.module_hash)}</div>
      <ol class="call-list">
        {calls_markup}
        {extra_line}
      </ol>
      <details>
        <summary>Komplettes Modul anzeigen</summary>
        <ol class="call-list">
          {''.join(f"<li>{html.escape(call)}</li>" for call in module.calls)}
        </ol>
      </details>
      <div class="module-actions">
        <a class="ghost-link" href="{viewer_link(filters, module.id)}">Ansehen</a>
        <a class="button-link" href="/?edit={module.id}#editor">Bearbeiten</a>
        <form action="/modules/{module.id}/delete" method="post">
          <button type="submit" class="danger">Löschen</button>
        </form>
      </div>
    </article>
    """


def render_options(
    values: tuple[str, ...],
    current_value: str,
    *,
    empty_label: str | None = None,
) -> str:
    options = []
    for value in values:
        if not value and empty_label is not None:
            label = empty_label
        else:
            label = value
        selected = " selected" if value == current_value else ""
        options.append(f'<option value="{html.escape(value)}"{selected}>{html.escape(label)}</option>')
    return "".join(options)


class ModuleRequestHandler(BaseHTTPRequestHandler):
    app_state: SimpleNamespace

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/", "/viewer"}:
            self._respond(HTTPStatus.NOT_FOUND, "", content_type="text/plain; charset=utf-8")
            return
        self._respond(HTTPStatus.OK, "")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/", "/viewer"}:
            self._respond(HTTPStatus.NOT_FOUND, "Nicht gefunden.", content_type="text/plain; charset=utf-8")
            return

        query = parse_qs(parsed.query)
        level = query.get("level", [""])[0]
        start_position = query.get("start", [""])[0]
        source_name = query.get("source", [""])[0]
        search = query.get("q", [""])[0]
        edit_id_raw = query.get("edit", [""])[0]
        message = query.get("message", [""])[0]
        message_type = query.get("type", ["success"])[0]
        sources = self.app_state.repository.list_sources()
        modules = self.app_state.repository.list_modules(
            level=level,
            start_position=start_position,
            source_name=source_name,
            query=search,
        )
        filters = {"level": level, "start": start_position, "source": source_name, "q": search}
        if parsed.path == "/viewer":
            selected_module, selected_index = pick_selected_module(modules, query.get("id", [""])[0])
            page = render_viewer_page(
                modules=modules,
                counts=self.app_state.repository.count_by_level(),
                sources=sources,
                filters=filters,
                selected_module=selected_module,
                selected_index=selected_index,
                message=message,
                message_type=message_type,
            )
        else:
            editing = None
            if edit_id_raw.isdigit():
                editing = self.app_state.repository.get_module(int(edit_id_raw))
            page = render_page(
                modules=modules,
                counts=self.app_state.repository.count_by_level(),
                sources=sources,
                filters=filters,
                editing=editing,
                message=message,
                message_type=message_type,
            )
        self._respond(HTTPStatus.OK, page)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        form = self._read_form_data()

        if parsed.path == "/modules":
            self._create_module(form)
            return
        if parsed.path == "/import/examples":
            self._import_examples()
            return
        if parsed.path.endswith("/update"):
            module_id = parsed.path.removeprefix("/modules/").removesuffix("/update")
            if module_id.isdigit():
                self._update_module(int(module_id), form)
                return
        if parsed.path.endswith("/delete"):
            module_id = parsed.path.removeprefix("/modules/").removesuffix("/delete")
            if module_id.isdigit():
                self.app_state.repository.delete_module(int(module_id))
                self._redirect("/", message="Modul gelöscht.", message_type="success")
                return

        self._respond(HTTPStatus.NOT_FOUND, "Nicht gefunden.", content_type="text/plain; charset=utf-8")

    def _create_module(self, form: dict[str, str]) -> None:
        try:
            record = self.app_state.repository.create_module(self._module_input_from_form(form))
        except DuplicateModuleError as exc:
            self._redirect(
                f"/?edit={exc.existing_id}#editor",
                message=f"Dieses Modul existiert bereits als Datensatz {exc.existing_id}.",
                message_type="error",
            )
            return
        except ValueError as exc:
            self._redirect("/", message=str(exc), message_type="error")
            return

        self._redirect(
            f"/?edit={record.id}#module-{record.id}",
            message="Modul gespeichert.",
            message_type="success",
        )

    def _update_module(self, module_id: int, form: dict[str, str]) -> None:
        try:
            record = self.app_state.repository.update_module(module_id, self._module_input_from_form(form))
        except DuplicateModuleError as exc:
            self._redirect(
                f"/?edit={exc.existing_id}#editor",
                message=f"Das aktualisierte Modul entspricht bereits Datensatz {exc.existing_id}.",
                message_type="error",
            )
            return
        except ValueError as exc:
            self._redirect(f"/?edit={module_id}#editor", message=str(exc), message_type="error")
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
        if not self.app_state.example_file.exists():
            self._redirect("/", message="Beispieldatei nicht gefunden.", message_type="error")
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
        return ModuleInput(
            title=form.get("title", ""),
            level=form.get("level", "MS"),
            start_position=form.get("start_position", "Static Square"),
            raw_text=form.get("raw_text", ""),
            source_name=form.get("source_name", ""),
        )

    def _read_form_data(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        return {key: values[0] for key, values in parse_qs(payload).items()}

    def _redirect(self, path: str, *, message: str, message_type: str) -> None:
        separator = "&" if "?" in path else "?"
        location = f"{path}{separator}{urlencode({'message': message, 'type': message_type})}"
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
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def run_server(host: str = "127.0.0.1", port: int = 8000, workspace: Path | None = None) -> None:
    base_path = workspace or Path.cwd()
    app_state = create_app_state(base_path)

    class BoundHandler(ModuleRequestHandler):
        pass

    BoundHandler.app_state = app_state

    server = ThreadingHTTPServer((host, port), BoundHandler)
    print(f"Square Cards läuft auf http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
