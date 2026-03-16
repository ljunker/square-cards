"""Import helpers for CallerSchool-style module files."""

from __future__ import annotations

from pathlib import Path

from .repository import ModuleInput, extract_call_lines

LEVEL_MAP = {
    "mainstream": "MS",
    "plus": "Plus",
    "a1": "A1",
    "a2": "A2",
}


def parse_callerschool_file(path: Path) -> list[ModuleInput]:
    """Parse a CallerSchool export file into repository inputs."""

    text = path.read_text(encoding="utf-8")
    blocks = [block.strip() for block in text.split("\f") if block.strip()]
    modules: list[ModuleInput] = []

    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines()]
        header = next((line for line in lines if line.strip()), "")
        call_lines = extract_call_lines(block)
        if not call_lines:
            continue

        lower_header = header.lower()
        level = next((mapped for key, mapped in LEVEL_MAP.items() if key in lower_header), "MS")
        title = call_lines[0]
        modules.append(
            ModuleInput(
                title=title,
                level=level,
                start_position="Static Square",
                raw_text="\n".join(call_lines),
                source_name=path.name,
            )
        )

    return modules


def parse_choreodb_text(
    text: str,
    *,
    level: str,
    start_position: str,
    source_name: str,
) -> list[ModuleInput]:
    """Parse a choreodb-style export into repository inputs.

    The format uses ``@`` as record separators, metadata lines prefixed with
    ``#`` and comma-separated calls for each record.
    """

    modules: list[ModuleInput] = []
    normalized_text = text.replace("\r\n", "\n")
    blocks = [block.strip() for block in normalized_text.split("@") if block.strip()]

    for block in blocks:
        call_lines = _parse_choreodb_calls(block)
        if not call_lines:
            continue
        modules.append(
            ModuleInput(
                title=call_lines[0],
                level=level,
                start_position=start_position,
                raw_text="\n".join(call_lines),
                source_name=source_name,
            )
        )

    return modules


def _parse_choreodb_calls(block: str) -> list[str]:
    """Extract call lines from one choreodb record block."""

    sequence_lines = [
        line.strip()
        for line in block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    sequence = " ".join(sequence_lines)
    return [part.strip() for part in sequence.split(",") if part.strip()]
