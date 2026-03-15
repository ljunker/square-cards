# Square Cards

[![Pylint](https://github.com/ljunker/square-cards/actions/workflows/pylint.yml/badge.svg)](https://github.com/ljunker/square-cards/actions/workflows/pylint.yml)

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

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
```
