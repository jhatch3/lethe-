"""Shared helpers for streaming agent output.

The audit agents stream their reasoning prose first, then a `---` divider,
then the structured JSON. This module:

  * splits chunks at the divider,
  * buffers prose at clause boundaries (so the dashboard terminal doesn't
    get spammed with one-character SSE events),
  * extracts the JSON object from the trailing portion.
"""

from __future__ import annotations

import json
import re
from typing import Awaitable, Callable, Optional, Tuple


DIVIDER = "---"
# Punctuation we treat as natural emit points for live streaming.
_BOUNDARY_RE = re.compile(r"[.!?\n]")


class StreamCollector:
    """Accepts streamed token chunks; emits prose lines via `on_message`.

    Anything before the divider is treated as visible prose. After the
    divider it's accumulated and parsed as JSON in `finalize()`.
    """

    def __init__(self, on_message: Optional[Callable[[str], Awaitable[None]]] = None) -> None:
        self._on_message = on_message
        self._before_divider: list[str] = []   # prose accumulator (parts before any divider)
        self._after_divider: list[str] = []    # json accumulator
        self._divider_seen = False
        self._line_buf = ""                    # buffer for clause-boundary emit
        self._all: list[str] = []              # full raw, for fallback parsing

    async def feed(self, chunk: str) -> None:
        if not chunk:
            return
        self._all.append(chunk)
        if self._divider_seen:
            self._after_divider.append(chunk)
            return

        # Look for the divider INSIDE this chunk (could span chunks too —
        # we handle the cross-chunk case by buffering small tails).
        combined = self._line_buf + chunk
        idx = combined.find(DIVIDER)
        if idx >= 0:
            prose_tail = combined[:idx].rstrip()
            self._before_divider.append(prose_tail)
            if prose_tail and self._on_message:
                # Flush any remaining prose as one final message.
                last = prose_tail.split("\n")[-1].strip()
                if last:
                    await self._on_message(last)
            self._line_buf = ""
            after = combined[idx + len(DIVIDER):]
            self._after_divider.append(after)
            self._divider_seen = True
            return

        # No divider yet — accumulate prose, emit when we hit a clause boundary
        # or buffer gets big.
        self._line_buf = combined
        # Find the latest natural boundary in the buffer:
        boundaries = list(_BOUNDARY_RE.finditer(self._line_buf))
        if boundaries:
            last = boundaries[-1].end()
            line = self._line_buf[:last].strip()
            self._line_buf = self._line_buf[last:]
            if line and self._on_message:
                # Strip leading whitespace + collapse internal newlines for a clean line
                cleaned = re.sub(r"\s+", " ", line).strip()
                if cleaned:
                    await self._on_message(cleaned)
                    self._before_divider.append(line)
        elif len(self._line_buf) >= 120:
            # Soft-flush long unpunctuated runs so the terminal stays alive
            line = self._line_buf
            self._line_buf = ""
            cleaned = re.sub(r"\s+", " ", line).strip()
            if cleaned and self._on_message:
                await self._on_message(cleaned)
                self._before_divider.append(line)

    async def finalize(self) -> Tuple[str, str]:
        """Flush any trailing prose; return (prose, json_text)."""
        if not self._divider_seen:
            # No divider — best-effort split: try to find a JSON object inside the
            # raw text and treat everything before it as prose.
            raw = "".join(self._all)
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                self._before_divider.append(raw[: m.start()])
                self._after_divider.append(m.group(0))
                self._divider_seen = True
            else:
                # Flush whatever's still buffered as a final message
                tail = self._line_buf.strip()
                if tail and self._on_message:
                    await self._on_message(tail)
                self._before_divider.append(self._line_buf)
                self._line_buf = ""
        else:
            tail = self._line_buf.strip()
            if tail and self._on_message:
                await self._on_message(tail)
            self._line_buf = ""

        prose = "".join(self._before_divider).strip()
        json_text = "".join(self._after_divider).strip()
        return prose, json_text


def parse_json_block(text: str) -> dict:
    """Best-effort extract a single {...} JSON object."""
    if not text:
        return {}
    text = text.strip()
    # Strip Markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
