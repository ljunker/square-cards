# Square Cards

[![Pylint](https://github.com/ljunker/square-cards/actions/workflows/pylint.yml/badge.svg)](https://github.com/ljunker/square-cards/actions/workflows/pylint.yml)
[![Coverage](https://github.com/ljunker/square-cards/actions/workflows/coverage.yml/badge.svg)](https://github.com/ljunker/square-cards/actions/workflows/coverage.yml)

Kleine Web-Anwendung zur Pflege von Square-Dance-Modulen in einer SQLite-Datenbank.

## Funktionen

- Speichert Module mit `Level`, `Startposition`, Rohtext, Quelle und Zeitstempeln.
- Erzeugt pro Modul einen SHA-256-Hash aus dem normalisierten Call-Text, um Duplikate zu erkennen.
- Importiert die zwei vorhandenen Beispiele aus `callerschool-pattern`.
- Bietet eine Web-Oberfläche zum Anlegen, Bearbeiten, Löschen, Filtern und Anzeigen der Module.

## Starten

```bash
.venv/bin/python app.py
```

Danach ist die Anwendung unter `http://127.0.0.1:8000` erreichbar.

Die SQLite-Datenbank wird unter `data/modules.sqlite3` angelegt.

## Docker

Image bauen:

```bash
docker build -t square-cards .
```

Container starten:

```bash
docker run --rm -p 8000:8000 -v "$(pwd)/data:/app/data" square-cards
```

Die Anwendung ist dann unter `http://127.0.0.1:8000` erreichbar. Das Image nutzt
einen Multi-Stage-Build und startet die App im Container auf `0.0.0.0:8000`.

Mit Docker Compose:

```bash
docker compose up --build
```

Mit erzwungenem Rebuild und Aufräumen verwaister Container:

```bash
docker compose up --build --force-recreate --remove-orphans
```

Die Compose-Datei bindet `./data` nach `/app/data`, damit die SQLite-Datenbank
persistiert bleibt.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
```
