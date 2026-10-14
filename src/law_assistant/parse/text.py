"""Text helpers shared by the parsers."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable

BLOCK_TAGS = frozenset({"p", "div", "tr", "td", "th", "table", "li", "ul", "ol", "br"})
_SPACES = re.compile(r"\s+")  # \s also matches the non-breaking space the sources use


def clean(text: str) -> str:
    """Collapse every run of whitespace (including non-breaking spaces) to one space and trim."""
    return _SPACES.sub(" ", text).strip()


def local(element: ET.Element) -> str:
    """The tag name without its XML namespace."""
    return element.tag.rsplit("}", 1)[-1]


def text_of(
    element: ET.Element,
    *,
    skip: Callable[[ET.Element], bool] = lambda e: False,
    block_tags: frozenset[str] = BLOCK_TAGS,
) -> str:
    """All the text under `element`, cleaned. Children for which `skip` is true are left out (tail kept)."""
    parts: list[str] = []

    def walk(node: ET.Element) -> None:
        parts.append(node.text or "")
        for child in node:
            if not skip(child):
                block = local(child) in block_tags
                parts.append(" " if block else "")  # paragraphs, cells and rows never run into each other
                walk(child)
                parts.append(" " if block else "")
            parts.append(child.tail or "")

    walk(element)
    return clean("".join(parts))
