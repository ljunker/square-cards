from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

LEVELS = ("MS", "Plus", "A1", "A2")
START_POSITIONS = ("Static Square", "Zero Box")
SPACE_RE = re.compile(r"\s+")
DATE_PREFIX_RE = re.compile(
    r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}\b",
    re.IGNORECASE,
)
SD_VERSION_RE = re.compile(r"\bSd\d+(?:\.\d+)*(?::db\d+(?:\.\d+)*)?\b", re.IGNORECASE)
LEVEL_NAME_RE = re.compile(r"^(?:Mainstream|MS|Plus|A1|A2)$", re.IGNORECASE)


class DuplicateModuleError(ValueError):
    def __init__(self, existing_id: int) -> None:
        super().__init__(f"Module already exists as record {existing_id}")
        self.existing_id = existing_id


@dataclass(slots=True)
class ModuleInput:
    title: str
    level: str
    start_position: str
    raw_text: str
    source_name: str = ""


@dataclass(slots=True)
class ModuleRecord:
    id: int
    title: str
    level: str
    start_position: str
    raw_text: str
    normalized_text: str
    module_hash: str
    source_name: str
    created_at: str
    updated_at: str

    @property
    def calls(self) -> list[str]:
        return [line for line in self.raw_text.splitlines() if line.strip()]


def normalize_module_text(raw_text: str) -> str:
    return "\n".join(line.lower() for line in extract_call_lines(raw_text))


def build_module_hash(raw_text: str) -> tuple[str, str]:
    normalized = normalize_module_text(raw_text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return normalized, digest


def extract_call_lines(raw_text: str) -> list[str]:
    call_lines: list[str] = []
    for line in raw_text.splitlines():
        compact = SPACE_RE.sub(" ", line.strip())
        if not compact:
            continue
        without_date = DATE_PREFIX_RE.sub("", compact).strip(" -")
        without_version = SD_VERSION_RE.sub("", without_date).strip(" -")
        if not without_version or LEVEL_NAME_RE.fullmatch(without_version):
            continue
        call_lines.append(without_version)
    return call_lines


class ModuleRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _managed_connection(self) -> sqlite3.Connection:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self._managed_connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    level TEXT NOT NULL,
                    start_position TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    module_hash TEXT NOT NULL UNIQUE,
                    source_name TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def list_modules(
        self,
        *,
        level: str = "",
        start_position: str = "",
        source_name: str = "",
        query: str = "",
    ) -> list[ModuleRecord]:
        clauses: list[str] = []
        params: list[str] = []
        if level:
            clauses.append("level = ?")
            params.append(level)
        if start_position:
            clauses.append("start_position = ?")
            params.append(start_position)
        if source_name:
            clauses.append("source_name = ?")
            params.append(source_name)
        if query:
            clauses.append(
                "(title LIKE ? OR raw_text LIKE ? OR module_hash LIKE ? OR source_name LIKE ?)"
            )
            wildcard = f"%{query}%"
            params.extend([wildcard, wildcard, wildcard, wildcard])

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._managed_connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, title, level, start_position, raw_text, normalized_text,
                       module_hash, source_name, created_at, updated_at
                FROM modules
                {where_clause}
                ORDER BY updated_at DESC, id DESC
                """,
                params,
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_module(self, module_id: int) -> ModuleRecord | None:
        with self._managed_connection() as connection:
            row = connection.execute(
                """
                SELECT id, title, level, start_position, raw_text, normalized_text,
                       module_hash, source_name, created_at, updated_at
                FROM modules
                WHERE id = ?
                """,
                (module_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def create_module(self, module_input: ModuleInput) -> ModuleRecord:
        validated = self._validate_input(module_input)
        normalized, module_hash = build_module_hash(validated.raw_text)
        with self._managed_connection() as connection:
            existing = connection.execute(
                "SELECT id FROM modules WHERE module_hash = ?",
                (module_hash,),
            ).fetchone()
            if existing:
                raise DuplicateModuleError(int(existing["id"]))

            cursor = connection.execute(
                """
                INSERT INTO modules (
                    title, level, start_position, raw_text, normalized_text,
                    module_hash, source_name
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    validated.title,
                    validated.level,
                    validated.start_position,
                    validated.raw_text,
                    normalized,
                    module_hash,
                    validated.source_name,
                ),
            )
            module_id = int(cursor.lastrowid)
        record = self.get_module(module_id)
        if record is None:
            raise RuntimeError("Inserted module could not be reloaded")
        return record

    def update_module(self, module_id: int, module_input: ModuleInput) -> ModuleRecord:
        validated = self._validate_input(module_input)
        normalized, module_hash = build_module_hash(validated.raw_text)
        with self._managed_connection() as connection:
            existing = connection.execute(
                "SELECT id FROM modules WHERE module_hash = ?",
                (module_hash,),
            ).fetchone()
            if existing and int(existing["id"]) != module_id:
                raise DuplicateModuleError(int(existing["id"]))

            cursor = connection.execute(
                """
                UPDATE modules
                SET title = ?,
                    level = ?,
                    start_position = ?,
                    raw_text = ?,
                    normalized_text = ?,
                    module_hash = ?,
                    source_name = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    validated.title,
                    validated.level,
                    validated.start_position,
                    validated.raw_text,
                    normalized,
                    module_hash,
                    validated.source_name,
                    module_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Module {module_id} not found")
        record = self.get_module(module_id)
        if record is None:
            raise RuntimeError("Updated module could not be reloaded")
        return record

    def delete_module(self, module_id: int) -> None:
        with self._managed_connection() as connection:
            connection.execute("DELETE FROM modules WHERE id = ?", (module_id,))

    def count_by_level(self) -> dict[str, int]:
        with self._managed_connection() as connection:
            rows = connection.execute(
                """
                SELECT level, COUNT(*) AS module_count
                FROM modules
                GROUP BY level
                """
            ).fetchall()
        counts = {level: 0 for level in LEVELS}
        counts.update({row["level"]: int(row["module_count"]) for row in rows})
        return counts

    def list_sources(self) -> tuple[str, ...]:
        with self._managed_connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT source_name
                FROM modules
                WHERE source_name <> ''
                ORDER BY source_name COLLATE NOCASE
                """
            ).fetchall()
        return tuple(str(row["source_name"]) for row in rows)

    def all_hashes(self) -> set[str]:
        with self._managed_connection() as connection:
            rows = connection.execute("SELECT module_hash FROM modules").fetchall()
        return {str(row["module_hash"]) for row in rows}

    def create_many(self, entries: Iterable[ModuleInput]) -> tuple[int, int]:
        added = 0
        skipped = 0
        for entry in entries:
            try:
                self.create_module(entry)
            except DuplicateModuleError:
                skipped += 1
            else:
                added += 1
        return added, skipped

    def _validate_input(self, module_input: ModuleInput) -> ModuleInput:
        cleaned_lines = extract_call_lines(module_input.raw_text)
        raw_text = "\n".join(cleaned_lines)
        title = module_input.title.strip() or self._title_from_text(raw_text)
        source_name = module_input.source_name.strip()
        if not raw_text:
            raise ValueError("Bitte Modultext eingeben.")
        if module_input.level not in LEVELS:
            raise ValueError("Ungültiges Level.")
        if module_input.start_position not in START_POSITIONS:
            raise ValueError("Ungültige Startposition.")
        return ModuleInput(
            title=title,
            level=module_input.level,
            start_position=module_input.start_position,
            raw_text=raw_text,
            source_name=source_name,
        )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ModuleRecord:
        return ModuleRecord(
            id=int(row["id"]),
            title=str(row["title"]),
            level=str(row["level"]),
            start_position=str(row["start_position"]),
            raw_text=str(row["raw_text"]),
            normalized_text=str(row["normalized_text"]),
            module_hash=str(row["module_hash"]),
            source_name=str(row["source_name"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _title_from_text(raw_text: str) -> str:
        for line in extract_call_lines(raw_text):
            if line.strip():
                return SPACE_RE.sub(" ", line.strip())
        return "Unbenanntes Modul"
