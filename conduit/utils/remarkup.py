"""Remarkup helpers for Phorge file attachment injection.

Pure helpers that convert between Phorge file identifiers (numeric
``F1234`` monograms and ``PHID-FILE-...`` PHIDs) and the ``{F<id>}``
remarkup syntax that Phorge renders inline. No I/O, no HTTP, no MCP
awareness — safe to import from any layer.
"""

import re
from typing import Any, Callable, Dict, List, Optional, Sequence


# Matches a Phorge file remarkup reference. The trailing character class
# anchors the numeric id so that ``{F1234}``, ``{F1234, size=full}`` and
# ``{F1234 size=full}`` all parse to id 1234 — and crucially, ``{F12345}``
# does NOT match as id 1234.
_FILE_REF_PATTERN = re.compile(r"\{F(\d+)[,\s\}]")

_MONOGRAM_PATTERN = re.compile(r"^F(\d+)$")

# Regions where Phorge does NOT parse remarkup tokens. A literal ``{F1234}``
# inside any of these renders as text rather than embedding an attachment,
# so reference detection must skip these regions.
#
# Order matters: multi-char fence syntaxes are listed first so a triple
# backtick block isn't mis-matched as two adjacent single-backtick spans.
_CODE_SPAN_PATTERN = re.compile(
    r"```.*?```"            # fenced code: ```...```
    r"|~~~.*?~~~"           # fenced code: ~~~...~~~
    r"|%%%.*?%%%"           # Phorge monospace literal: %%%...%%%
    r"|`[^`\n]+`",          # inline code: `...` (single line)
    re.DOTALL,
)


def parse_file_id_from_monogram(monogram: str) -> Optional[int]:
    """Parse ``"F1234"`` into ``1234``. Return ``None`` for any other shape."""
    match = _MONOGRAM_PATTERN.match(monogram)
    if match is None:
        return None
    return int(match.group(1))


def _strip_code_regions(text: str) -> str:
    """Blank out code-span regions so remarkup token detection only looks
    at text that Phorge will actually parse for tokens."""
    return _CODE_SPAN_PATTERN.sub("", text)


def has_file_reference(text: str, file_id: int) -> bool:
    """Return ``True`` if an *active* ``{F<file_id>}`` reference appears in
    ``text``. Mentions inside inline-code spans, fenced code blocks, or
    Phorge monospace literals are ignored because Phorge renders them as
    text rather than as attachment embeds.
    """
    stripped = _strip_code_regions(text)
    return any(
        int(found) == file_id for found in _FILE_REF_PATTERN.findall(stripped)
    )


def append_file_references(
    text: str, file_ids: Sequence[int]
) -> str:
    """Append ``{F<id>}`` for each id not already referenced in ``text``.

    Idempotent — calling repeatedly with the same ids produces the same
    output. Inserts a blank line before the refs when ``text`` is
    non-empty so the references render as a separate block.
    """
    new_ids = [fid for fid in file_ids if not has_file_reference(text, fid)]
    if not new_ids:
        return text
    refs = "\n".join(f"{{F{fid}}}" for fid in new_ids)
    if not text:
        return refs
    separator = "\n\n" if not text.endswith("\n") else "\n"
    return f"{text}{separator}{refs}"


def resolve_file_identifiers(
    identifiers: Sequence[str],
    fetch_phid_info: Callable[[str], Dict[str, Any]],
) -> List[int]:
    """Resolve each identifier to its numeric file id.

    ``"F1234"`` is parsed inline (no API call). A ``"PHID-FILE-..."`` is
    resolved via ``fetch_phid_info`` and its ``"id"`` field is returned.
    Any other shape raises :class:`ValueError`.
    """
    resolved: List[int] = []
    for identifier in identifiers:
        monogram_id = parse_file_id_from_monogram(identifier)
        if monogram_id is not None:
            resolved.append(monogram_id)
            continue
        if identifier.startswith("PHID-FILE-"):
            info = fetch_phid_info(identifier)
            file_id = info.get("id")
            if file_id is None:
                raise ValueError(
                    f"file info for {identifier} missing 'id' field"
                )
            resolved.append(int(file_id))
            continue
        raise ValueError(
            f"invalid file identifier {identifier!r}: "
            "expected 'F<n>' or 'PHID-FILE-...'"
        )
    return resolved
